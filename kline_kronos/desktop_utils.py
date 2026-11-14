"""Cross-platform safe desktop window & file-manager helpers (zero shell execution)."""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys


def bring_window_frontmost() -> bool:
    """Safely bring the current Tkinter process window to front on macOS without os.system."""
    if sys.platform != "darwin":
        return False
    osascript = pathlib.Path("/usr/bin/osascript")
    if not osascript.is_file():
        return False
    script = (
        'tell application "System Events" to set frontmost of the first process '
        f"whose unix id is {int(os.getpid())} to true"
    )
    res = subprocess.run(
        [str(osascript), "-e", script],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return res.returncode == 0


def reveal_in_file_manager(target: str | os.PathLike[str], select_file: bool = False) -> bool:
    """Open a directory or highlight a file in the OS native file manager using argv lists."""
    resolved = pathlib.Path(target).expanduser().resolve()
    if sys.platform == "darwin":
        cmd = ["/usr/bin/open", "-R", str(resolved)] if select_file else ["/usr/bin/open", str(resolved)]
    elif sys.platform.startswith("win"):
        cmd = ["explorer", f"/select,{resolved}"] if select_file else ["explorer", str(resolved)]
    else:
        folder = resolved.parent if select_file else resolved
        cmd = ["xdg-open", str(folder)]
    try:
        res = subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except FileNotFoundError:
        return False
