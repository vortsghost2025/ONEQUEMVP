import psutil
import platform
from app.models import Settings, ThresholdCheckResult
from sqlmodel import Session, select
from app.utils import engine


def _get_disk_path() -> str:
    """Get appropriate disk path for current OS.

    Returns:
        str: Disk path ('/' for Unix-like, 'C:\\' for Windows)
    """
    system = platform.system().lower()
    if system == "windows":
        return "C:\\"
    return "/"


def _get_current_settings(session: Session) -> Settings:
    """Retrieve the singleton Settings row, creating a default one if missing."""
    s = session.get(Settings, 1)
    if not s:
        s = Settings()
        session.add(s)
        session.commit()
        session.refresh(s)
    return s


def check_thresholds() -> ThresholdCheckResult:
    """Check system resources against the thresholds stored in Settings.

    Returns a ``ThresholdCheckResult`` where ``should_pause`` is ``True``
    if *any* of the monitored resources exceed their configured limits
    and ``auto_pause`` is enabled. The ``reason`` field contains a human
    readable explanation of which metric triggered the pause.
    """
    # Gather system metrics
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory().percent
    disk_path = _get_disk_path()
    disk = psutil.disk_usage(disk_path).percent

    # Load thresholds from DB (no side‑effects)
    with Session(engine) as session:
        settings = _get_current_settings(session)
        if not settings.auto_pause:
            return ThresholdCheckResult(should_pause=False)

        if cpu > settings.max_cpu_percent:
            return ThresholdCheckResult(
                should_pause=True, reason=f"CPU {cpu}% > {settings.max_cpu_percent}%"
            )
        if ram > settings.max_ram_percent:
            return ThresholdCheckResult(
                should_pause=True, reason=f"RAM {ram}% > {settings.max_ram_percent}%"
            )
        if disk > settings.max_disk_percent:
            return ThresholdCheckResult(
                should_pause=True, reason=f"Disk {disk}% > {settings.max_disk_percent}%"
            )
        return ThresholdCheckResult(should_pause=False)
