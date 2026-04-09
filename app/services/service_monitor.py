"""
Service Monitoring & Alerting System
Automatic notifications when services go down
"""

import asyncio
import logging
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("onequeue.service_monitor")


class ServiceStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


@dataclass
class ServiceAlert:
    """Alert when service status changes"""

    service_name: str
    previous_status: ServiceStatus
    current_status: ServiceStatus
    timestamp: datetime
    message: str
    notify_agent: bool = True
    notify_user: bool = True
    metadata: Dict = field(default_factory=dict)


class ServiceMonitor:
    """
    Monitors all OneQueue services and sends alerts on status changes.

    Monitors:
    - Ollama backend
    - NVIDIA API
    - Database
    - GPU (optional)
    - Queue worker

    Alert Channels:
    - Agent notification (logger + in-app)
    - User notification (UI badge + optional webhook)
    - Alert history file
    """

    def __init__(self):
        self.services: Dict[str, ServiceStatus] = {}
        self.alert_history: List[ServiceAlert] = []
        self.alert_callbacks: List[Callable] = []
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False

        # Alert thresholds
        self.offline_threshold = 3  # Consecutive failures before OFFLINE alert
        self.recovery_threshold = 1  # Successes before HEALTHY alert

        # Failure counters
        self._failure_counts: Dict[str, int] = {}
        self._success_counts: Dict[str, int] = {}

        # Alert cooldown (don't spam same alert)
        self.alert_cooldown = timedelta(minutes=5)
        self._last_alert_time: Dict[str, datetime] = {}

    async def check_ollama(self) -> ServiceStatus:
        """Check Ollama service"""
        try:
            import httpx
            from app.config import settings

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=2.0
                )

                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])

                    if len(models) == 0:
                        return ServiceStatus.DEGRADED

                    return ServiceStatus.HEALTHY
                else:
                    return ServiceStatus.OFFLINE

        except Exception:
            return ServiceStatus.OFFLINE

    async def check_nvidia(self) -> ServiceStatus:
        """Check NVIDIA API"""
        try:
            from app.config import settings

            if not settings.NVIDIA_API_KEY:
                return ServiceStatus.OFFLINE

            if not settings.NVIDIA_API_KEY.startswith("nvapi-"):
                return ServiceStatus.OFFLINE

            # Quick validation - try to list models
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://integrate.api.nvidia.com/v1/models",
                    headers={"Authorization": f"Bearer {settings.NVIDIA_API_KEY}"},
                    timeout=5.0,
                )

                if response.status_code == 200:
                    return ServiceStatus.HEALTHY
                elif response.status_code == 401:
                    return ServiceStatus.OFFLINE
                else:
                    return ServiceStatus.DEGRADED

        except Exception:
            return ServiceStatus.OFFLINE

    async def check_database(self) -> ServiceStatus:
        """Check database connection"""
        try:
            from app.utils import engine
            from sqlmodel import Session, select
            from app.models import Task

            with Session(engine) as session:
                session.exec(select(Task).limit(1)).first()

            return ServiceStatus.HEALTHY

        except Exception:
            return ServiceStatus.OFFLINE

    async def check_all_services(self) -> Dict[str, ServiceStatus]:
        """Check all services"""
        results = {
            "ollama": await self.check_ollama(),
            "nvidia": await self.check_nvidia(),
            "database": await self.check_database(),
        }

        # Detect status changes and send alerts
        for service_name, current_status in results.items():
            previous_status = self.services.get(service_name, ServiceStatus.UNKNOWN)

            # Update failure/success counters
            if current_status != ServiceStatus.HEALTHY:
                self._failure_counts[service_name] = (
                    self._failure_counts.get(service_name, 0) + 1
                )
                self._success_counts[service_name] = 0
            else:
                self._success_counts[service_name] = (
                    self._success_counts.get(service_name, 0) + 1
                )
                self._failure_counts[service_name] = 0

            # Check for OFFLINE transition
            if (
                self._failure_counts.get(service_name, 0) >= self.offline_threshold
                and previous_status != ServiceStatus.OFFLINE
            ):
                await self._send_alert(
                    ServiceAlert(
                        service_name=service_name,
                        previous_status=previous_status,
                        current_status=ServiceStatus.OFFLINE,
                        timestamp=datetime.utcnow(),
                        message=f"{service_name.upper()} is OFFLINE",
                        notify_agent=True,
                        notify_user=True,
                        metadata={"failures": self._failure_counts[service_name]},
                    )
                )

            # Check for HEALTHY transition
            elif (
                self._success_counts.get(service_name, 0) >= self.recovery_threshold
                and previous_status != ServiceStatus.HEALTHY
            ):
                await self._send_alert(
                    ServiceAlert(
                        service_name=service_name,
                        previous_status=previous_status,
                        current_status=ServiceStatus.HEALTHY,
                        timestamp=datetime.utcnow(),
                        message=f"{service_name.upper()} is HEALTHY again",
                        notify_agent=True,
                        notify_user=True,
                        metadata={"recoveries": self._success_counts[service_name]},
                    )
                )

            self.services[service_name] = current_status

        return results

    async def _send_alert(self, alert: ServiceAlert):
        """Send alert through all channels"""

        # Cooldown check
        alert_key = f"{alert.service_name}_{alert.current_status.value}"
        last_alert = self._last_alert_time.get(alert_key)

        if last_alert and (datetime.utcnow() - last_alert) < self.alert_cooldown:
            logger.debug(f"Alert cooldown active for {alert_key}")
            return

        # Update last alert time
        self._last_alert_time[alert_key] = datetime.utcnow()

        # Store in history
        self.alert_history.append(alert)

        # Agent notification (logger)
        if alert.notify_agent:
            if alert.current_status == ServiceStatus.OFFLINE:
                logger.error(f"🚨 SERVICE ALERT: {alert.message}")
            elif alert.current_status == ServiceStatus.HEALTHY:
                logger.info(f"✓ SERVICE RECOVERY: {alert.message}")
            else:
                logger.warning(f"⚠ SERVICE WARNING: {alert.message}")

        # User notification (write to file for UI to pick up)
        if alert.notify_user:
            await self._write_user_alert(alert)

        # Callbacks
        for callback in self.alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

    async def _write_user_alert(self, alert: ServiceAlert):
        """Write alert to file for UI to display"""
        alerts_dir = Path("data/alerts")
        alerts_dir.mkdir(parents=True, exist_ok=True)

        alert_file = alerts_dir / "current_alerts.json"

        # Read existing alerts
        existing_alerts = []
        if alert_file.exists():
            try:
                with open(alert_file, "r") as f:
                    existing_alerts = json.load(f)
            except:
                pass

        # Add new alert
        alert_dict = {
            "service": alert.service_name,
            "status": alert.current_status.value,
            "message": alert.message,
            "timestamp": alert.timestamp.isoformat(),
            "metadata": alert.metadata,
        }

        # Remove old alerts for same service
        existing_alerts = [
            a for a in existing_alerts if a["service"] != alert.service_name
        ]

        # Add new alert if not healthy
        if alert.current_status != ServiceStatus.HEALTHY:
            existing_alerts.append(alert_dict)

        # Write back
        with open(alert_file, "w") as f:
            json.dump(existing_alerts, f, indent=2)

    def add_alert_callback(self, callback: Callable):
        """Add custom alert callback"""
        self.alert_callbacks.append(callback)

    async def start_monitoring(self, interval_seconds: int = 30):
        """Start continuous monitoring"""
        self._running = True

        async def monitor_loop():
            while self._running:
                try:
                    await self.check_all_services()
                    await asyncio.sleep(interval_seconds)
                except Exception as e:
                    logger.error(f"Monitor loop error: {e}")
                    await asyncio.sleep(5)

        self._monitoring_task = asyncio.create_task(monitor_loop())
        logger.info(f"Service monitoring started (interval: {interval_seconds}s)")

    def stop_monitoring(self):
        """Stop monitoring"""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            logger.info("Service monitoring stopped")

    def get_current_status(self) -> Dict[str, str]:
        """Get current service status"""
        return {name: status.value for name, status in self.services.items()}

    def get_alerts(self, since: Optional[datetime] = None) -> List[Dict]:
        """Get recent alerts"""
        if since:
            return [
                {
                    "service": a.service_name,
                    "previous": a.previous_status.value,
                    "current": a.current_status.value,
                    "message": a.message,
                    "timestamp": a.timestamp.isoformat(),
                }
                for a in self.alert_history
                if a.timestamp >= since
            ]
        else:
            return [
                {
                    "service": a.service_name,
                    "previous": a.previous_status.value,
                    "current": a.current_status.value,
                    "message": a.message,
                    "timestamp": a.timestamp.isoformat(),
                }
                for a in self.alert_history[-50:]  # Last 50 alerts
            ]


# Singleton
_service_monitor: Optional[ServiceMonitor] = None


def get_service_monitor() -> ServiceMonitor:
    """Get or create service monitor singleton"""
    global _service_monitor
    if _service_monitor is None:
        _service_monitor = ServiceMonitor()
    return _service_monitor


async def start_service_monitoring(interval_seconds: int = 30):
    """Start service monitoring"""
    monitor = get_service_monitor()
    await monitor.start_monitoring(interval_seconds)


def stop_service_monitoring():
    """Stop service monitoring"""
    monitor = get_service_monitor()
    monitor.stop_monitoring()
