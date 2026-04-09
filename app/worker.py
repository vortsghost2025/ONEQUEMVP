import asyncio
import logging
from datetime import datetime
import psutil

from sqlmodel import Session, select, desc

from app.config import settings
from app.main import engine
from app.models import Task, Run, Settings
from app.services.monitor import check_thresholds
from app.services.ollama import OllamaClient, OllamaError
from app.services.nvidia_api import NvidiaAPI

logger = logging.getLogger("onequeue.worker")


async def worker_loop() -> None:
    """Background worker that processes pending tasks.

    The loop respects manual pause (Settings.queue_paused) and auto‑pause
    based on system thresholds. It processes tasks in priority order,
    supports cooperative cancellation, enforces per‑task timeouts, logs a
    ``Run`` record with resource usage, and handles retry logic.
    """
    poll_interval = settings.POLLING_INTERVAL_SECONDS
    client = OllamaClient()

    # Consecutive breach counters for sustained load detection
    ram_breach_count = 0
    cpu_breach_count = 0
    disk_breach_count = 0

    while True:
        # Open a new DB session for each iteration
        with Session(engine) as session:
            # Load the singleton Settings row (create if missing)
            s = session.get(Settings, 1)
            if not s:
                s = Settings()
                session.add(s)
                session.commit()
                session.refresh(s)

        # Manual pause check
        if s.queue_paused:
            logger.debug("Queue manually paused")
            await asyncio.sleep(poll_interval)
            continue

        # Threshold auto‑pause check with sustained load detection
        th = check_thresholds()
        breach_duration = s.breach_duration_seconds

        # Track consecutive breaches for each resource
        if th.should_pause:
            if "RAM" in (th.reason or ""):
                ram_breach_count += 1
                cpu_breach_count = 0
                disk_breach_count = 0
            elif "CPU" in (th.reason or ""):
                cpu_breach_count += 1
                ram_breach_count = 0
                disk_breach_count = 0
            elif "Disk" in (th.reason or ""):
                disk_breach_count += 1
                ram_breach_count = 0
                cpu_breach_count = 0

            # Only pause if breach sustained for consecutive checks
            max_breach = max(ram_breach_count, cpu_breach_count, disk_breach_count)
            if max_breach >= breach_duration:
                logger.warning(
                    f"Sustained threshold block: {th.reason} for {max_breach} consecutive seconds"
                )
                await asyncio.sleep(poll_interval)
                continue
            else:
                logger.debug(
                    f"Threshold spike detected: {th.reason} (count: {max_breach}/{breach_duration})"
                )
        else:
            # Reset all counters when within thresholds
            ram_breach_count = 0
            cpu_breach_count = 0
            disk_breach_count = 0

        # Fetch the next pending task (order by priority DESC, then created_at ASC)
        stmt = (
            select(Task)
            .where(Task.status == "pending")
            .order_by(Task.priority.desc())
            .order_by(Task.created_at)
        )
        task = session.exec(stmt).first()
        if not task:
            await asyncio.sleep(poll_interval)
            continue

        # Cooperative cancellation before starting work
        if task.cancel_requested:
            task.status = "cancelled"
            task.finished_at = datetime.utcnow()
            session.add(task)
            session.commit()
            logger.info(f"Task {task.id} cancelled before execution")
            continue

        # Mark task as RUNNING
        task.status = "running"
        task.started_at = datetime.utcnow()
        session.add(task)
        session.commit()
        session.refresh(task)  # Ensure task.id is populated
        logger.info(f"Started task {task.id} (attempt {task.attempt_count})")

        # Execute the model call with timeout enforcement
        success = False
        error_text = None
        output = None
        start = datetime.utcnow()
        try:
            async with asyncio.timeout(task.timeout_seconds):
                if "/" in task.model:
                    nvidia_client = NvidiaAPI()
                    result = await nvidia_client.generate(
                        model=task.model,
                        prompt=task.prompt,
                        max_tokens=task.timeout_seconds,
                    )
                    output = result["choices"][0]["message"]["content"]
                else:
                    output = await client.generate(
                        task.prompt, task.model, task.timeout_seconds
                    )
                success = True
        except asyncio.TimeoutError:
            error_text = "Task timed out"
        except OllamaError as exc:
            error_text = str(exc)
        except Exception as exc:
            error_text = str(exc)
        end = datetime.utcnow()
        duration_ms = int((end - start).total_seconds() * 1000)

        # Record Run information (resource usage captured after execution)
        assert task.id is not None
        run = Run(
            task_id=task.id,
            attempt_number=task.attempt_count,
            cpu_percent=psutil.cpu_percent(),
            ram_percent=psutil.virtual_memory().percent,
            disk_percent=psutil.disk_usage("C:\\").percent,
            duration_ms=duration_ms,
            success=success,
            error_text=error_text,
        )
        session.add(run)

        # Update task based on execution outcome
        if success:
            task.status = "completed"
            task.finished_at = end
            task.output_text = output
            task.error_text = None
            logger.info(f"Task {task.id} completed successfully")
        else:
            task.error_text = error_text
            total_allowed_attempts = 1 + task.max_retries
            if task.attempt_count >= total_allowed_attempts:
                task.status = "failed"
                task.finished_at = end
                logger.error(
                    f"Task {task.id} failed permanently after {task.attempt_count} attempts: {error_text}"
                )
            else:
                task.status = "pending"
                task.attempt_count += 1
                logger.warning(
                    f"Task {task.id} failed on attempt {task.attempt_count - 1}. Will retry as attempt {task.attempt_count}."
                )

            if task.status == "pending":
                task.started_at = None
                task.finished_at = None

        session.add(task)
        session.commit()

        # Small sleep before next iteration to avoid a tight loop when no work
        await asyncio.sleep(poll_interval)
