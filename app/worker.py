import asyncio
import logging
import platform
from datetime import datetime
import psutil

from sqlmodel import Session, select

from app.config import settings
from app.utils import engine
from app.models import Task, Run, Settings, TaskStatus
from app.services.monitor import check_thresholds
from app.services.ollama import OllamaClient, OllamaError
from app.services.nvidia_api import NvidiaAPI
from app.services.smart_router import SmartRouter

logger = logging.getLogger("onequeue.worker")

# ====================== HELPERS ======================


def _get_disk_path() -> str:
    """Return correct disk path for current operating system."""
    if platform.system().lower() == "windows":
        return "C:\\"
    return "/"


def _is_nvidia_model(model_id: str, router: SmartRouter) -> bool:
    """
    Check if model should use NVIDIA API.
    Uses centralized SmartRouter logic for single source of truth.
    """
    return router._is_nvidia_model(model_id)


# ====================== MAIN WORKER ======================


async def worker_loop() -> None:
    """
    Background worker that processes pending tasks.

    - Respects manual pause and auto-pause on sustained high resource usage
    - Processes tasks by priority (highest first), then by age (oldest first)
    - Supports cooperative cancellation
    - Enforces per-task timeouts
    - Records peak resource usage (before/after execution)
    - Handles retry logic with attempt counting
    """
    poll_interval = settings.POLLING_INTERVAL_SECONDS
    ollama_client = OllamaClient()
    nvidia_client = NvidiaAPI()
    smart_router = SmartRouter()

    # Breach counters for sustained load detection
    ram_breach_count = 0
    cpu_breach_count = 0
    disk_breach_count = 0

    while True:
        with Session(engine) as session:
            # ====================== LOAD SETTINGS ======================
            settings_obj = session.get(Settings, 1)
            if not settings_obj:
                settings_obj = Settings()
                session.add(settings_obj)
                session.commit()
                session.refresh(settings_obj)

            # ====================== MANUAL PAUSE ======================
            if settings_obj.queue_paused:
                logger.debug("Queue is manually paused")
                await asyncio.sleep(poll_interval)
                continue

            # ====================== AUTO-PAUSE ON SUSTAINED HIGH LOAD ======================
            thresholds = check_thresholds()
            if thresholds.should_pause:
                # Track consecutive breaches
                if "RAM" in (thresholds.reason or ""):
                    ram_breach_count += 1
                    cpu_breach_count = 0
                    disk_breach_count = 0
                elif "CPU" in (thresholds.reason or ""):
                    cpu_breach_count += 1
                    ram_breach_count = 0
                    disk_breach_count = 0
                elif "Disk" in (thresholds.reason or ""):
                    disk_breach_count += 1
                    ram_breach_count = 0
                    cpu_breach_count = 0

                # Only pause if breach sustained for configured duration
                max_breach = max(ram_breach_count, cpu_breach_count, disk_breach_count)
                if max_breach >= settings_obj.breach_duration_seconds:
                    logger.warning(
                        f"Sustained high load: {thresholds.reason} "
                        f"({max_breach}/{settings_obj.breach_duration_seconds}s). Pausing queue."
                    )
                    await asyncio.sleep(poll_interval)
                    continue
            else:
                # Reset counters when healthy
                ram_breach_count = 0
                cpu_breach_count = 0
                disk_breach_count = 0

            # ====================== FETCH NEXT TASK ======================
            # Priority: highest first, then oldest first
            task = session.exec(
                select(Task)
                .where(Task.status == TaskStatus.PENDING)
                .order_by(Task.priority.desc())
                .order_by(Task.created_at.asc())
            ).first()

            if not task:
                await asyncio.sleep(poll_interval)
                continue

            # ====================== HANDLE CANCELLATION ======================
            if task.cancel_requested:
                task.status = TaskStatus.CANCELLED
                task.finished_at = datetime.utcnow()
                session.add(task)
                session.commit()
                logger.info(f"Task {task.id} cancelled before execution")
                continue

            # ====================== MARK AS RUNNING ======================
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow()
            session.add(task)
            session.commit()
            session.refresh(task)
            logger.info(f"Started task {task.id} (attempt {task.attempt_count})")

            # ====================== EXECUTE TASK ======================
            success = False
            error_text = None
            output = None
            start_time = datetime.utcnow()

            # Capture resource usage BEFORE execution
            disk_path = _get_disk_path()
            cpu_before = psutil.cpu_percent()
            ram_before = psutil.virtual_memory().percent
            disk_before = psutil.disk_usage(disk_path).percent

            try:
                async with asyncio.timeout(task.timeout_seconds):
                    # Route to correct backend using SmartRouter
                    if _is_nvidia_model(task.model, smart_router):
                        logger.info(f"Routing to NVIDIA API: {task.model}")
                        response = await nvidia_client.generate(
                            model=task.model, prompt=task.prompt, max_tokens=2048
                        )
                        output = (
                            response.get("choices", [{}])[0]
                            .get("message", {})
                            .get("content", "")
                        )
                    else:
                        logger.info(f"Routing to Ollama: {task.model}")
                        output = await ollama_client.generate(
                            task.prompt, task.model, task.timeout_seconds
                        )
                    success = True

            except asyncio.TimeoutError:
                error_text = "Task timed out"
                logger.warning(
                    f"Task {task.id} timed out after {task.timeout_seconds}s"
                )

            except OllamaError as e:
                error_text = str(e)
                logger.error(f"Ollama error on task {task.id}: {e}")

            except Exception as e:
                error_text = str(e)
                logger.error(f"Unexpected error on task {task.id}: {e}")

            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            # Capture resource usage AFTER execution
            cpu_after = psutil.cpu_percent()
            ram_after = psutil.virtual_memory().percent
            disk_after = psutil.disk_usage(disk_path).percent

            # ====================== RECORD RUN METRICS ======================
            run = Run(
                task_id=task.id,
                attempt_number=task.attempt_count,
                cpu_percent=max(cpu_before, cpu_after),  # Peak usage
                ram_percent=max(ram_before, ram_after),
                disk_percent=max(disk_before, disk_after),
                duration_ms=duration_ms,
                success=success,
                error_text=error_text,
            )
            session.add(run)

            # ====================== UPDATE TASK STATUS ======================
            if success:
                task.status = TaskStatus.COMPLETED
                task.finished_at = end_time
                task.output_text = output
                logger.info(f"Task {task.id} completed successfully")

            else:
                task.error_text = error_text

                # Check if max retries exceeded
                if task.attempt_count >= task.max_retries:
                    task.status = TaskStatus.FAILED
                    task.finished_at = end_time
                    logger.error(
                        f"Task {task.id} failed permanently after "
                        f"{task.attempt_count} attempts: {error_text}"
                    )
                else:
                    # Retry: set back to pending
                    task.status = TaskStatus.PENDING
                    task.attempt_count += 1
                    logger.warning(
                        f"Task {task.id} failed on attempt {task.attempt_count - 1}. "
                        f"Will retry as attempt {task.attempt_count}."
                    )

            # If task is pending (retry), clear timestamps
            if task.status == TaskStatus.PENDING:
                task.started_at = None
                task.finished_at = None

            session.add(task)
            session.commit()

            # Small delay to prevent tight loop when no work
            await asyncio.sleep(poll_interval)
