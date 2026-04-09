"""
OneQueue Pre-Flight Checklist - Automatic Launch Validation
Runs BEFORE any task processing starts
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

logger = logging.getLogger("onequeue.preflight")


class PreflightCheck:
    """Single pre-flight check item"""

    def __init__(self, name: str, critical: bool = True):
        self.name = name
        self.critical = critical
        self.passed = False
        self.message = ""
        self.fix_hint = ""


class PreflightChecklist:
    """
    Automatic pre-flight checklist that runs before OneQueue starts.

    CRITICAL checks (must pass):
    - Database accessible
    - At least one backend available
    - Configuration valid

    NON-CRITICAL checks (warning only):
    - GPU available (optional)
    - Ollama models present
    - Disk space available
    """

    def __init__(self):
        self.checks: List[PreflightCheck] = []
        self.results: Dict[str, PreflightCheck] = {}

    async def run_all_checks(self) -> Tuple[bool, List[str]]:
        """
        Run all pre-flight checks.

        Returns:
            (all_passed: bool, errors: List[str])
        """
        logger.info("=" * 60)
        logger.info("ONEQUEUE PRE-FLIGHT CHECKLIST")
        logger.info("=" * 60)

        errors = []
        warnings = []

        # 1. CRITICAL: Database check (with table creation if needed)
        check = PreflightCheck("Database Connection", critical=True)
        try:
            from app.utils import engine
            from sqlmodel import SQLModel, Session, select
            from app.models import Task, Run, Settings

            # Create tables if they don't exist
            SQLModel.metadata.create_all(engine)

            # Now try a simple query
            with Session(engine) as session:
                session.exec(select(Task).limit(1)).first()

            check.passed = True
            check.message = "Database accessible (tables created)"
            logger.info(f"✓ {check.name}: {check.message}")

        except Exception as e:
            check.passed = False
            check.message = f"Database error: {e}"
            check.fix_hint = "Check DATABASE_URL or ensure write permissions"
            logger.error(f"✗ {check.name}: {check.message}")
            errors.append(f"{check.name}: {check.message}")

        self.results["database"] = check

        # 2. CRITICAL: Backend availability
        check = PreflightCheck("Backend Availability", critical=True)
        try:
            from app.services.backend_health import get_backend_checker

            checker = get_backend_checker()
            health = await checker.check_all(use_cache=False)

            if health["any_available"]:
                check.passed = True
                check.message = health["recommended_action"]
                logger.info(f"✓ {check.name}: {check.message}")
            else:
                check.passed = False
                check.message = "No backends available (Ollama or NVIDIA API)"
                check.fix_hint = (
                    "Start Ollama: ollama serve\nOR set NVIDIA_API_KEY in .env"
                )
                logger.error(f"✗ {check.name}: {check.message}")
                errors.append(f"{check.name}: {check.message}")

        except Exception as e:
            check.passed = False
            check.message = f"Backend check failed: {e}"
            logger.error(f"✗ {check.name}: {check.message}")
            errors.append(f"{check.name}: {check.message}")

        self.results["backend"] = check

        # 3. CRITICAL: Configuration validation
        check = PreflightCheck("Configuration", critical=True)
        try:
            from app.config import settings

            # Check critical settings
            issues = []

            if settings.POLLING_INTERVAL_SECONDS < 0.1:
                issues.append("POLLING_INTERVAL_SECONDS too low")

            if settings.POLLING_INTERVAL_SECONDS > 60:
                issues.append("POLLING_INTERVAL_SECONDS too high")

            if issues:
                check.passed = False
                check.message = f"Config issues: {', '.join(issues)}"
                logger.warning(f"⚠ {check.name}: {check.message}")
                warnings.append(f"{check.name}: {check.message}")
            else:
                check.passed = True
                check.message = "Configuration valid"
                logger.info(f"✓ {check.name}: {check.message}")

        except Exception as e:
            check.passed = False
            check.message = f"Configuration error: {e}"
            check.fix_hint = "Check .env file and app/config.py"
            logger.error(f"✗ {check.name}: {check.message}")
            errors.append(f"{check.name}: {check.message}")

        self.results["config"] = check

        # 4. NON-CRITICAL: Disk space
        check = PreflightCheck("Disk Space", critical=False)
        try:
            import shutil
            import platform

            disk_path = "C:\\" if platform.system().lower() == "windows" else "/"
            usage = shutil.disk_usage(disk_path)
            free_gb = usage.free / (1024**3)
            total_gb = usage.total / (1024**3)
            used_percent = (usage.used / usage.total) * 100

            if free_gb < 5:
                check.passed = False
                check.message = (
                    f"Low disk space: {free_gb:.1f}GB free ({used_percent:.1f}% used)"
                )
                logger.warning(f"⚠ {check.name}: {check.message}")
                warnings.append(f"{check.name}: {check.message}")
            else:
                check.passed = True
                check.message = f"{free_gb:.1f}GB free ({used_percent:.1f}% used)"
                logger.info(f"✓ {check.name}: {check.message}")

        except Exception as e:
            check.passed = True  # Non-critical
            check.message = f"Could not check disk: {e}"
            logger.warning(f"⚠ {check.name}: {check.message}")

        self.results["disk"] = check

        # 5. NON-CRITICAL: RAM availability
        check = PreflightCheck("RAM Available", critical=False)
        try:
            import psutil

            ram = psutil.virtual_memory()
            available_gb = ram.available / (1024**3)
            used_percent = ram.percent

            if available_gb < 2:
                check.passed = False
                check.message = (
                    f"Low RAM: {available_gb:.1f}GB available ({used_percent}% used)"
                )
                logger.warning(f"⚠ {check.name}: {check.message}")
                warnings.append(f"{check.name}: {check.message}")
            else:
                check.passed = True
                check.message = f"{available_gb:.1f}GB available ({used_percent}% used)"
                logger.info(f"✓ {check.name}: {check.message}")

        except Exception as e:
            check.passed = True
            check.message = f"Could not check RAM: {e}"
            logger.warning(f"⚠ {check.name}: {check.message}")

        self.results["ram"] = check

        # Summary
        logger.info("=" * 60)

        critical_passed = all(c.passed for c in self.results.values() if c.critical)

        if critical_passed:
            logger.info("✓ PREFLIGHT PASSED - All critical checks passed")
            if warnings:
                logger.warning(f"⚠ {len(warnings)} warnings (non-critical)")
                for w in warnings:
                    logger.warning(f"  - {w}")
        else:
            logger.error("✗ PREFLIGHT FAILED - Critical checks failed:")
            for e in errors:
                logger.error(f"  - {e}")
            logger.error(
                "\nOneQueue will NOT start until critical issues are resolved."
            )
            logger.error("Please fix the errors above and restart.")

        logger.info("=" * 60)

        return critical_passed, errors

    def print_report(self):
        """Print detailed pre-flight report"""
        print("\n" + "=" * 60)
        print("ONEQUEUE PRE-FLIGHT REPORT")
        print("=" * 60)
        print(f"Timestamp: {datetime.utcnow().isoformat()}\n")

        for name, check in self.results.items():
            status = "✓ PASS" if check.passed else "✗ FAIL"
            critical = "CRITICAL" if check.critical else "OPTIONAL"
            print(f"[{status}] [{critical}] {check.name}")
            print(f"  Message: {check.message}")
            if check.fix_hint and not check.passed:
                print(f"  Fix: {check.fix_hint}")
            print()

        print("=" * 60)


async def run_preflight_checklist() -> bool:
    """
    Run pre-flight checklist before OneQueue starts.

    Usage:
        # In app/main.py startup
        from app.services.preflight import run_preflight_checklist

        if not await run_preflight_checklist():
            sys.exit(1)

    Returns:
        True if all critical checks passed, False otherwise
    """
    checklist = PreflightChecklist()
    passed, errors = await checklist.run_all_checks()

    if not passed:
        # Log to file
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        error_log = (
            log_dir
            / f"preflight_failure_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.log"
        )
        with open(error_log, "w") as f:
            f.write("ONEQUEUE PRE-FLIGHT FAILURE\n")
            f.write(f"Timestamp: {datetime.utcnow().isoformat()}\n\n")
            f.write("ERRORS:\n")
            for error in errors:
                f.write(f"  - {error}\n")
            f.write("\nFULL REPORT:\n")
            for name, check in checklist.results.items():
                f.write(f"{name}: {check.message}\n")
                if check.fix_hint:
                    f.write(f"  Fix: {check.fix_hint}\n")

        logger.error(f"Pre-flight failure logged to: {error_log}")

    return passed
