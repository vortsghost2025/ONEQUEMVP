"""
System Status API - For users and agents to check system health
"""

from fastapi import APIRouter
from app.services.startup_notifier import get_startup_status

router = APIRouter()


@router.get("/status")
def get_system_status():
    """
    Get current system status.

    Returns:
    - ready: bool - Whether system can accept tasks
    - critical_failures: List - Critical issues blocking operation
    - warnings: List - Non-blocking warnings
    - fix_instructions: List - Steps to resolve issues
    - can_accept_tasks: bool - Whether to submit new tasks
    """
    status = get_startup_status()
    return status.get_status()


@router.get("/status/agent")
def get_agent_status():
    """
    Get status message for agents.
    Simple text message explaining if agent should proceed with tasks.
    """
    status = get_startup_status()
    return {
        "message": status.get_agent_message(),
        "can_proceed": status.is_ready,
        "ready": status.is_ready,
    }
