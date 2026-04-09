"""
Safe File I/O Utilities - Atomic writes and UTF-8 safety
Prevents state corruption from power loss, encoding errors
"""

import json
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Any, Optional, Dict
import logging

logger = logging.getLogger("onequeue.safe_io")


def atomic_write_json(filepath: str | Path, data: Any, backup: bool = True) -> bool:
    """
    Write JSON atomically to prevent corruption from power failure.

    Process:
    1. Write to temporary file
    2. Sync to disk
    3. Atomic rename (replaces original)

    Args:
        filepath: Target file path
        data: Data to write (will be JSON serialized)
        backup: Create .backup of existing file before overwrite

    Returns:
        True on success, False on failure
    """
    filepath = Path(filepath)

    try:
        # Ensure parent directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Backup existing file if requested
        if backup and filepath.exists():
            backup_path = filepath.with_suffix(filepath.suffix + ".backup")
            shutil.copy2(filepath, backup_path)
            logger.debug(f"Created backup: {backup_path}")

        # Write to temp file first
        fd, tmp_path = tempfile.mkstemp(
            dir=filepath.parent, prefix=".tmp_", suffix=filepath.suffix
        )

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk

            # Atomic rename (POSIX guarantee, Windows best-effort)
            os.replace(tmp_path, filepath)
            logger.debug(f"Atomic write successful: {filepath}")
            return True

        except Exception as e:
            # Clean up temp file on failure
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    except Exception as e:
        logger.error(f"Atomic write failed for {filepath}: {e}")
        return False


def safe_read_json(
    filepath: str | Path, default: Optional[Any] = None, repair: bool = True
) -> Optional[Any]:
    """
    Read JSON safely with UTF-8 encoding and corruption handling.

    Args:
        filepath: File to read
        default: Return value if file missing/corrupted
        repair: Attempt to restore from .backup if corrupted

    Returns:
        Parsed JSON data or default value
    """
    filepath = Path(filepath)

    if not filepath.exists():
        logger.debug(f"File not found: {filepath}, returning default")
        return default

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    except json.JSONDecodeError as e:
        logger.error(f"Corrupted JSON in {filepath}: {e}")

        # Attempt repair from backup
        if repair:
            backup_path = filepath.with_suffix(filepath.suffix + ".backup")
            if backup_path.exists():
                logger.warning(f"Attempting restore from backup: {backup_path}")
                try:
                    with open(backup_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    # Restore backup to main file
                    atomic_write_json(filepath, data, backup=False)
                    logger.info(f"Successfully restored from backup: {filepath}")
                    return data
                except Exception as restore_error:
                    logger.error(f"Backup restore failed: {restore_error}")

        return default

    except UnicodeDecodeError as e:
        logger.error(f"Encoding error in {filepath}: {e}")
        return default

    except Exception as e:
        logger.error(f"Unexpected error reading {filepath}: {e}")
        return default


def safe_write_text(
    filepath: str | Path, content: str, encoding: str = "utf-8"
) -> bool:
    """
    Write text file atomically with encoding safety.

    Args:
        filepath: Target file path
        content: Text content to write
        encoding: Text encoding (default UTF-8)

    Returns:
        True on success, False on failure
    """
    filepath = Path(filepath)

    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(
            dir=filepath.parent, prefix=".tmp_", suffix=filepath.suffix
        )

        try:
            with os.fdopen(fd, "w", encoding=encoding) as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())

            os.replace(tmp_path, filepath)
            return True

        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    except Exception as e:
        logger.error(f"Text write failed for {filepath}: {e}")
        return False


def safe_read_text(
    filepath: str | Path, default: str = "", encoding: str = "utf-8"
) -> str:
    """
    Read text file safely with encoding fallback.

    Args:
        filepath: File to read
        default: Return value if file missing/error
        encoding: Expected encoding

    Returns:
        File content or default value
    """
    filepath = Path(filepath)

    if not filepath.exists():
        return default

    try:
        with open(filepath, "r", encoding=encoding) as f:
            return f.read()
    except UnicodeDecodeError:
        # Try alternative encodings
        for alt_encoding in ["utf-8-sig", "latin-1", "cp1252"]:
            try:
                with open(filepath, "r", encoding=alt_encoding) as f:
                    logger.warning(
                        f"Read {filepath} with fallback encoding: {alt_encoding}"
                    )
                    return f.read()
            except:
                continue
        logger.error(f"All encoding attempts failed for {filepath}")
        return default
    except Exception as e:
        logger.error(f"Error reading {filepath}: {e}")
        return default


def rotate_file(
    filepath: str | Path, max_size_mb: float = 10.0, keep_backups: int = 5
) -> bool:
    """
    Rotate log/data files when they exceed size threshold.

    Args:
        filepath: File to rotate
        max_size_mb: Maximum size in MB before rotation
        keep_backups: Number of backup files to keep

    Returns:
        True if rotation occurred, False otherwise
    """
    filepath = Path(filepath)

    if not filepath.exists():
        return False

    size_mb = filepath.stat().st_size / (1024 * 1024)

    if size_mb < max_size_mb:
        return False

    logger.info(f"Rotating {filepath} ({size_mb:.2f} MB > {max_size_mb} MB)")

    # Rotate existing backups
    for i in range(keep_backups - 1, 0, -1):
        old_backup = filepath.with_suffix(f".{i}{filepath.suffix}")
        new_backup = filepath.with_suffix(f".{i + 1}{filepath.suffix}")
        if old_backup.exists():
            old_backup.rename(new_backup)

    # Rotate current file to .1
    backup_path = filepath.with_suffix(f".1{filepath.suffix}")
    shutil.move(str(filepath), str(backup_path))

    logger.info(f"Rotated to {backup_path}")
    return True


# Convenience functions for common OneQueue operations


def save_task_state(task_id: int, state: Dict) -> bool:
    """Save task state atomically."""
    from app.config import settings

    state_file = Path(settings.DATA_DIR) / "tasks" / f"task_{task_id}.json"
    return atomic_write_json(state_file, state)


def load_task_state(task_id: int) -> Optional[Dict]:
    """Load task state safely."""
    from app.config import settings

    state_file = Path(settings.DATA_DIR) / "tasks" / f"task_{task_id}.json"
    return safe_read_json(state_file)


def save_router_config(config: Dict) -> bool:
    """Save router configuration atomically."""
    return atomic_write_json("router.json", config)


def load_router_config() -> Optional[Dict]:
    """Load router configuration safely."""
    return safe_read_json("router.json", default={})
