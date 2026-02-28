"""
Repository ingestion: clone into a temporary directory on the host.

Uses subprocess + tempfile (no Docker). cleanup_volume removes the directory with shutil.rmtree.
"""

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def ingest_repository(repo_url: str) -> dict:
    """
    Clones a validated repository into a temporary local directory on the host.

    Runs `git clone [repo_url]` into a new temp directory. Returns the absolute
    local path so the worker can read files directly.

    Returns:
        dict with:
            - container_id: absolute path to the cloned repo (used as handle for cleanup)
            - local_path: same absolute path
    """
    try:
        clone_dir = tempfile.mkdtemp(prefix="scan_repo_")
        abs_path = Path(clone_dir).resolve()
    except OSError as e:
        logger.error("Failed to create temp directory: %s", e)
        raise RuntimeError(f"Failed to create temp directory: {e}") from e

    logger.info("Cloning %s into %s", repo_url, abs_path)

    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, "."],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(abs_path),
        )
    except FileNotFoundError:
        shutil.rmtree(abs_path, ignore_errors=True)
        raise RuntimeError("git is not installed or not on PATH") from None
    except subprocess.TimeoutExpired:
        shutil.rmtree(abs_path, ignore_errors=True)
        raise RuntimeError("git clone timed out after 300s") from None
    except Exception as e:
        shutil.rmtree(abs_path, ignore_errors=True)
        logger.exception("Unexpected error during git clone")
        raise RuntimeError(f"Failed to clone repository: {e}") from e

    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        shutil.rmtree(abs_path, ignore_errors=True)
        logger.error("Clone failed: %s", err)
        raise RuntimeError(f"Failed to clone repository: {err}")

    logger.info("Clone successful: %s", abs_path)
    path_str = str(abs_path)
    return {
        "container_id": path_str,
        "local_path": path_str,
    }


def cleanup_volume(volume_name_or_path: str) -> None:
    """
    Removes the cloned repository directory.

    volume_name_or_path is the absolute path returned by ingest_repository
    (previously called container_id). Uses shutil.rmtree to delete the directory.
    """
    path = Path(volume_name_or_path)
    if not path.is_dir():
        logger.warning("Cleanup path is not a directory or does not exist: %s", volume_name_or_path)
        return
    try:
        shutil.rmtree(path, ignore_errors=False)
        logger.info("Successfully cleaned up directory: %s", path)
    except OSError as e:
        logger.error("Failed to clean up directory %s: %s", path, e)
