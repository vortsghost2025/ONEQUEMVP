"""
Graceful Shutdown Handler - Clean exit on signals
Prevents data loss, orphaned tasks, state corruption
"""

import signal
import sys
import atexit
import logging
import asyncio
from typing import Callable, List, Optional
from datetime import datetime
from pathlib import Path
import json

logger = logging.getLogger("onequeue.graceful_shutdown")


class GracefulShutdown:
    """
    Handles graceful shutdown on SIGINT (Ctrl+C) and SIGTERM.

    Ensures:
    - Running tasks are saved
    - Database connections closed
    - Background workers stopped
    - State persisted
    - Audit log written
    """

    def __init__(self):
        self.shutdown_handlers: List[Callable] = []
        self.is_shutting_down = False
        self.shutdown_timeout = 10.0  # Max seconds for cleanup

        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Register atexit for normal exits
        atexit.register(self._atexit_handler)

        logger.info("Graceful shutdown handler registered")

    def register_handler(self, handler: Callable, name: str = "unnamed"):
        """
        Register a cleanup handler to be called on shutdown.

        Args:
            handler: Async or sync function to call
            name: Handler name for logging
        """
        self.shutdown_handlers.append({"handler": handler, "name": name})
        logger.debug(f"Registered shutdown handler: {name}")

    def _signal_handler(self, signum, frame):
        """Handle SIGINT/SIGTERM signals."""
        signal_name = signal.Signals(signum).name
        logger.warning(f"Received signal {signal_name} ({signum})")

        if self.is_shutting_down:
            logger.error("Force exit (cleanup already in progress)")
            sys.exit(1)

        self.initiate_shutdown()
        sys.exit(0)

    def _atexit_handler(self):
        """Handle normal program exit."""
        if not self.is_shutting_down:
            logger.info("Normal exit detected")
            self.initiate_shutdown()

    def initiate_shutdown(self):
        """
        Execute all registered cleanup handlers.

        Runs handlers with timeout protection.
        """
        if self.is_shutting_down:
            return

        self.is_shutting_down = True

        logger.info("=" * 60)
        logger.info("GRACEFUL SHUTDOWN INITIATED")
        logger.info(f"Timestamp: {datetime.utcnow().isoformat()}")
        logger.info("=" * 60)

        # Log shutdown event
        self._log_shutdown_event()

        # Execute cleanup handlers
        for handler_info in self.shutdown_handlers:
            handler_name = handler_info["name"]
            handler = handler_info["handler"]

            try:
                logger.info(f"Running cleanup handler: {handler_name}")

                # Handle both sync and async handlers
                if asyncio.iscoroutinefunction(handler):
                    # Run async handler with timeout
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If loop is running, schedule task
                        asyncio.create_task(handler())
                    else:
                        # If loop not running, run directly
                        loop.run_until_complete(
                            asyncio.wait_for(handler(), timeout=self.shutdown_timeout)
                        )
                else:
                    # Run sync handler
                    handler()

                logger.info(f"Cleanup handler completed: {handler_name}")

            except asyncio.TimeoutError:
                logger.error(f"Cleanup handler timeout: {handler_name}")
            except Exception as e:
                logger.error(f"Cleanup handler error ({handler_name}): {e}")

        # Save final state
        self._save_final_state()

        logger.info("=" * 60)
        logger.info("GRACEFUL SHUTDOWN COMPLETE")
        logger.info("=" * 60)

    def _log_shutdown_event(self):
        """Log shutdown event for audit trail."""
        try:
            audit_dir = Path("logs")
            audit_dir.mkdir(exist_ok=True)

            audit_file = audit_dir / "shutdown_events.log"

            event = {
                "timestamp": datetime.utcnow().isoformat(),
                "event": "graceful_shutdown",
                "handlers_registered": len(self.shutdown_handlers),
                "handler_names": [h["name"] for h in self.shutdown_handlers],
            }

            with open(audit_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")

        except Exception as e:
            logger.error(f"Failed to log shutdown event: {e}")

    def _save_final_state(self):
        """Save final system state."""
        try:
            state_dir = Path("data")
            state_dir.mkdir(exist_ok=True)

            state_file = state_dir / "shutdown_state.json"

            state = {
                "shutdown_timestamp": datetime.utcnow().isoformat(),
                "clean_exit": True,
                "version": "0.2.1",  # Match FastAPI version
            }

            # Atomic write
            from app.utils.safe_io import atomic_write_json

            atomic_write_json(state_file, state, backup=False)

            logger.info(f"Final state saved to {state_file}")

        except Exception as e:
            logger.error(f"Failed to save final state: {e}")


# Global instance
_shutdown_handler: Optional[GracefulShutdown] = None


def get_shutdown_handler() -> GracefulShutdown:
    """Get or create global shutdown handler."""
    global _shutdown_handler
    if _shutdown_handler is None:
        _shutdown_handler = GracefulShutdown()
    return _shutdown_handler


def register_shutdown_handler(handler: Callable, name: str = "unnamed"):
    """
    Convenience function to register cleanup handler.

    Args:
        handler: Function to call on shutdown
        name: Handler name for logging
    """
    shutdown_manager = get_shutdown_handler()
    shutdown_manager.register_handler(handler, name)


# Integration with FastAPI
def integrate_with_fastapi(app):
    """
    Integrate graceful shutdown with FastAPI application.

    Args:
        app: FastAPI application instance

    Usage:
        from app.services.graceful_shutdown import integrate_with_fastapi
        integrate_with_fastapi(app)
    """
    from app.utils import logger as app_logger

    shutdown_handler = get_shutdown_handler()

    # Register FastAPI-specific cleanup
    async def cleanup_database():
        """Close database connections."""
        try:
            from app.utils import engine

            engine.dispose()
            app_logger.info("Database connections closed")
        except Exception as e:
            app_logger.error(f"Database cleanup error: {e}")

    async def cleanup_background_tasks():
        """Cancel background tasks."""
        try:
            # Cancel any running background tasks
            tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

            if tasks:
                app_logger.info(f"Cancelling {len(tasks)} background tasks")
                for task in tasks:
                    task.cancel()

                # Wait for tasks to be cancelled
                await asyncio.gather(*tasks, return_exceptions=True)
                app_logger.info("Background tasks cancelled")

        except Exception as e:
            app_logger.error(f"Background task cleanup error: {e}")

    async def save_worker_state():
        """Save worker state before shutdown."""
        try:
            from app.utils.safe_io import atomic_write_json
            from pathlib import Path

            worker_state = {
                "shutdown_timestamp": datetime.utcnow().isoformat(),
                "active_tasks": 0,  # Could be enhanced to track actual tasks
                "status": "shutdown_clean",
            }

            state_file = Path("data/worker_state.json")
            atomic_write_json(state_file, worker_state)
            app_logger.info("Worker state saved")

        except Exception as e:
            app_logger.error(f"Worker state save error: {e}")

    # Register cleanup handlers in reverse order (LIFO)
    shutdown_handler.register_handler(save_worker_state, "save_worker_state")
    shutdown_handler.register_handler(
        cleanup_background_tasks, "cleanup_background_tasks"
    )
    shutdown_handler.register_handler(cleanup_database, "cleanup_database")

    app_logger.info("Graceful shutdown integrated with FastAPI")


# Convenience exports
__all__ = [
    "GracefulShutdown",
    "get_shutdown_handler",
    "register_shutdown_handler",
    "integrate_with_fastapi",
]
