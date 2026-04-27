"""Tests for the SoundFont resolution helper.

These never hit the network: they either point ``MUSICKY_SOUNDFONT`` at
a real on-disk file, or monkey-patch ``urllib.request.urlopen`` so the
download path is exercised without leaving the test process.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import pytest

from musicky import default_soundfont
from musicky.sf import DEFAULT_SOUNDFONT_URL, cache_dir


def test_env_var_takes_priority(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sf_path = tmp_path / "my.sf2"
    sf_path.write_bytes(b"not really a soundfont")
    monkeypatch.setenv("MUSICKY_SOUNDFONT", str(sf_path))
    assert default_soundfont() == sf_path


def test_missing_env_var_path_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MUSICKY_SOUNDFONT", str(tmp_path / "nope.sf2"))
    with pytest.raises(RuntimeError, match="MUSICKY_SOUNDFONT"):
        default_soundfont()


def test_cached_file_is_reused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """If the cache file already exists, no download is attempted."""
    monkeypatch.delenv("MUSICKY_SOUNDFONT", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    cached = cache_dir() / "default.sf3"
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(b"pretend SoundFont")

    # Patch urlopen to make sure it never gets called.
    def fail(*_a: Any, **_k: Any) -> None:
        raise AssertionError("urlopen should not be called when cache hits")

    monkeypatch.setattr("musicky.sf.urllib.request.urlopen", fail)
    assert default_soundfont() == cached


def test_download_writes_to_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """First-run path: urlopen returns bytes, file lands in the cache."""
    monkeypatch.delenv("MUSICKY_SOUNDFONT", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))

    payload = b"x" * 1024  # one chunk worth of fake SoundFont data

    class FakeResponse:
        def __init__(self) -> None:
            self.headers = {"Content-Length": str(len(payload))}
            self._stream = BytesIO(payload)

        def read(self, n: int) -> bytes:
            return self._stream.read(n)

        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *_a: object) -> None:
            return None

    def fake_urlopen(url: str, **_kwargs: Any) -> FakeResponse:
        assert url == DEFAULT_SOUNDFONT_URL
        return FakeResponse()

    monkeypatch.setattr("musicky.sf.urllib.request.urlopen", fake_urlopen)

    result = default_soundfont()
    assert result.exists()
    assert result.read_bytes() == payload

    # Idempotent: a second call must hit the cache without touching the
    # network. We swap urlopen for a function that always raises.
    def boom(*_a: Any, **_k: Any) -> None:
        raise AssertionError("second call should hit cache")

    monkeypatch.setattr("musicky.sf.urllib.request.urlopen", boom)
    again = default_soundfont()
    assert again == result


def test_network_failure_cleans_up_partial_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A URLError during download should leave no half-written file behind."""
    import urllib.error

    monkeypatch.delenv("MUSICKY_SOUNDFONT", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))

    def boom(*_a: Any, **_k: Any) -> None:
        raise urllib.error.URLError("no network")

    monkeypatch.setattr("musicky.sf.urllib.request.urlopen", boom)

    with pytest.raises(RuntimeError, match="Could not download"):
        default_soundfont()

    assert not (cache_dir() / "default.sf3").exists()
