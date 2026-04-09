"""
Startup Notifier - Alerts when critical services are down
Notifies both users (via status endpoint) and agents (via system messages)
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger("onequeue.startup_notifier")


class StartupStatus:
    """Global startup status tracker"""

    def __init__(self):
        self.start_time = datetime.utcnow()
        self.is_ready = False
        self.critical_failures: List[Dict] = []
        self.warnings: List[Dict] = []
        self.fix_instructions: List[str] = []

    def add_critical_failure(self, check_name: str, message: str, fix_hint: str = ""):
        """Add a critical failure that blocks startup"""
        self.critical_failures.append(
            {
                "check": check_name,
                "message": message,
                "fix_hint": fix_hint,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        if fix_hint:
            self.fix_instructions.append(fix_hint)
        self.is_ready = False
        logger.error(f"❌ CRITICAL: {check_name} - {message}")

    def add_warning(self, check_name: str, message: str, fix_hint: str = ""):
        """Add a warning that doesn't block startup"""
        self.warnings.append(
            {
                "check": check_name,
                "message": message,
                "fix_hint": fix_hint,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        logger.warning(f"⚠️ WARNING: {check_name} - {message}")

    def mark_ready(self):
        """Mark system as ready to serve"""
        self.is_ready = True
        logger.info("✅ System ready to serve requests")

    def get_status(self) -> Dict:
        """Get current status for API endpoint"""
        return {
            "ready": self.is_ready,
            "start_time": self.start_time.isoformat(),
            "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
            "critical_failures": self.critical_failures,
            "warnings": self.warnings,
            "fix_instructions": self.fix_instructions if not self.is_ready else [],
            "can_accept_tasks": self.is_ready and len(self.critical_failures) == 0,
        }

    def get_agent_message(self) -> str:
        """Get a message for agents explaining system status"""
        if self.is_ready:
            return "System ready. All services operational."

        if self.critical_failures:
            issues = "; ".join([f["check"] for f in self.critical_failures])
            fixes = "\n".join([f"- {fix}" for fix in self.fix_instructions])
            return (
                f"⚠️ SYSTEM ISSUE: {issues}. "
                f"Tasks may fail until resolved. "
                f"Fix instructions:\n{fixes}"
            )

        if self.warnings:
            issues = "; ".join([f["check"] for f in self.warnings])
            return f"⚠️ Warnings: {issues}. System operational but degraded."

        return "System status unknown."


# Global instance
startup_status = StartupStatus()


def get_startup_status() -> StartupStatus:
    """Get the global startup status tracker"""
    return startup_status
