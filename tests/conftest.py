"""Shared pytest fixtures.

The ``mock_ffprobe`` fixture patches ``subprocess.run`` so tests need no real
video files - the writer and builder probe synthetic ffprobe output. The
autouse ``_clear_ffprobe_cache`` fixture resets the module-level probe cache
between tests so cached results never leak across cases.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from types import SimpleNamespace
from typing import Any

import pytest

from steele_fcpxml.probe import clear_cache


@pytest.fixture(autouse=True)
def _clear_ffprobe_cache() -> Iterator[None]:
    """Clear the ffprobe cache before and after each test."""
    clear_cache()
    yield
    clear_cache()


@pytest.fixture
def mock_ffprobe(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[..., None]:
    """Return a function that patches ``subprocess.run`` with fake ffprobe output.

    Call it to install the patch, optionally overriding fps/dimensions/duration::

        def test_x(tmp_path, mock_ffprobe):
            mock_ffprobe(duration=60.0)
            ...
    """

    def install(
        fps_str: str = "25/1",
        width: int = 1920,
        height: int = 1080,
        duration: float = 120.0,
    ) -> None:
        def fake_run(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
            return SimpleNamespace(stdout=f"{fps_str},{width},{height}\n{duration}\n")

        monkeypatch.setattr("subprocess.run", fake_run)

    return install
