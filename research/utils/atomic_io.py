"""Atomic JSON write utilities for FQL state files.

Prevents data corruption from interrupted writes by writing to a temp file
first, then atomically replacing the target. os.replace() is atomic on POSIX.
"""

import json
import os
import shutil
from pathlib import Path


def atomic_write_json(path, data, indent=2):
    """Write JSON data atomically using temp-file + rename.

    Parameters
    ----------
    path : str or Path
        Target file path.
    data : dict or list
        JSON-serializable data.
    indent : int
        JSON indentation level.
    """
    path = Path(path)
    tmp_path = path.with_suffix(".json.tmp")
    try:
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=indent, default=str)
        os.replace(str(tmp_path), str(path))
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def backup_rotate(path, keep=5):
    """Create a rolling backup of a file before overwriting.

    Keeps the last `keep` backup copies as path.bak.1.json through path.bak.N.json.
    Backup 1 is always the most recent.

    Parameters
    ----------
    path : str or Path
        File to back up.
    keep : int
        Number of backups to retain.
    """
    path = Path(path)
    if not path.exists():
        return

    # Rotate existing backups (N -> N+1, delete oldest)
    for i in range(keep, 0, -1):
        old = path.with_name(f"{path.stem}.bak.{i}{path.suffix}")
        if i == keep:
            old.unlink(missing_ok=True)
        elif old.exists():
            new = path.with_name(f"{path.stem}.bak.{i + 1}{path.suffix}")
            old.rename(new)

    # Copy current to bak.1
    bak1 = path.with_name(f"{path.stem}.bak.1{path.suffix}")
    shutil.copy2(str(path), str(bak1))
