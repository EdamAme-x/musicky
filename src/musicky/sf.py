"""SoundFont resolution: where to find a usable .sf2/.sf3 file.

Order of resolution used by `default_soundfont()`:
  1. ``MUSICKY_SOUNDFONT`` environment variable, if set and pointing to
     an existing file.
  2. Cached download at ``~/.cache/musicky/default.sf3`` (or whatever
     ``XDG_CACHE_HOME`` points to). If present, return it.
  3. Otherwise download a small free SoundFont (MuseScore's MS Basic,
     ~33MB) from a public mirror, save it to the cache, and return.

Network failures or missing libfluidsynth always raise with an error
message that tells the user how to fix the problem manually (set
``MUSICKY_SOUNDFONT`` or ``apt install libfluidsynth3``).

The downloader uses only the standard library so musicky itself does
not pick up an HTTP client as a runtime dependency.
"""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

__all__ = [
    "DEFAULT_SOUNDFONT_URL",
    "cache_dir",
    "default_soundfont",
]

# MuseScore's "MS Basic" — General MIDI compliant, ~33 MB, CC-BY licensed.
# Hosted on the official MuseScore GitHub repository so the URL is
# expected to stay stable for the lifetime of MuseScore 4.
DEFAULT_SOUNDFONT_URL = (
    "https://github.com/musescore/MuseScore/raw/master/share/sound/MS%20Basic.sf3"
)

# File name used for the cached download. The extension reflects the
# actual file format; sf3 is just a compressed sf2 and pyfluidsynth
# accepts either.
_DEFAULT_FILENAME = "default.sf3"


def cache_dir() -> Path:
    """Return the directory used to cache downloaded SoundFonts.

    Honors ``XDG_CACHE_HOME`` so Linux users with custom XDG layouts
    keep musicky's cache where they expect.
    """
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "musicky"


def default_soundfont() -> Path:
    """Resolve the SoundFont path, downloading on first use.

    Raises ``RuntimeError`` with an actionable message if no SoundFont
    can be obtained (network down, host unreachable, etc.).
    """
    env = os.environ.get("MUSICKY_SOUNDFONT")
    if env:
        path = Path(env).expanduser()
        if not path.exists():
            raise RuntimeError(
                f"MUSICKY_SOUNDFONT points to {path}, but no file is there. "
                "Set the variable to an existing .sf2/.sf3 file, or unset "
                "it to use the auto-downloaded default.",
            )
        return path

    target = cache_dir() / _DEFAULT_FILENAME
    if target.exists():
        return target

    # Need to download. Tell the user what is happening — the first run
    # otherwise looks like the program just hangs.
    target.parent.mkdir(parents=True, exist_ok=True)
    sys.stderr.write(
        f"musicky: downloading default SoundFont (~33 MB) to {target}\n"
        f"  source: {DEFAULT_SOUNDFONT_URL}\n"
        "  this only happens once. set MUSICKY_SOUNDFONT to skip.\n",
    )
    sys.stderr.flush()

    try:
        _download_with_progress(DEFAULT_SOUNDFONT_URL, target)
    except urllib.error.URLError as exc:
        # Clean up partial files so the next run retries from scratch.
        target.unlink(missing_ok=True)
        raise RuntimeError(
            "Could not download the default SoundFont. "
            "Either connect to the internet and retry, or download a "
            "SoundFont manually and point MUSICKY_SOUNDFONT at it. "
            f"Underlying error: {exc}",
        ) from exc
    return target


def _download_with_progress(url: str, target: Path) -> None:
    """Stream `url` to `target`, printing a simple percentage to stderr."""
    with urllib.request.urlopen(url, timeout=30) as response:
        total_str = response.headers.get("Content-Length")
        total = int(total_str) if total_str else 0
        chunk_size = 64 * 1024
        downloaded = 0
        last_percent = -1
        with target.open("wb") as fh:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                fh.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    percent = int(downloaded * 100 / total)
                    if percent != last_percent and percent % 5 == 0:
                        sys.stderr.write(f"  {percent}% ({downloaded // 1024} KB)\n")
                        sys.stderr.flush()
                        last_percent = percent
    sys.stderr.write("  done.\n")
    sys.stderr.flush()
