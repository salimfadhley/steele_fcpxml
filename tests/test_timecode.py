"""Tests for tc(), FrameRate, and seconds_to_rational."""

from __future__ import annotations

from fractions import Fraction

import pytest

from steele_fcpxml.timecode import FrameRate, seconds_to_rational, tc

# -- tc() timecode conversion ----------------------------------------------


def test_tc_mm_ss() -> None:
    assert tc("1:30") == 90.0


def test_tc_mm_ss_fractional() -> None:
    assert tc("1:30.5") == 90.5


def test_tc_hh_mm_ss() -> None:
    assert tc("1:02:30") == 3750.0


def test_tc_seconds_only() -> None:
    assert tc("45") == 45.0


# -- FrameRate enum --------------------------------------------------------


@pytest.mark.parametrize(
    "rate,expected_frame_dur",
    [
        (FrameRate.FPS_23_976, "1001/24000s"),
        (FrameRate.FPS_24, "1/24s"),
        (FrameRate.FPS_25, "1/25s"),
        (FrameRate.FPS_29_97, "1001/30000s"),
        (FrameRate.FPS_30, "1/30s"),
        (FrameRate.FPS_50, "1/50s"),
        (FrameRate.FPS_59_94, "1001/60000s"),
        (FrameRate.FPS_60, "1/60s"),
    ],
)
def test_frame_duration_for_all_standard_rates(
    rate: FrameRate, expected_frame_dur: str
) -> None:
    assert rate.frame_duration == expected_frame_dur


@pytest.mark.parametrize(
    "ffprobe_output,expected_member",
    [
        ("25/1", FrameRate.FPS_25),
        ("30000/1001", FrameRate.FPS_29_97),
        ("24000/1001", FrameRate.FPS_23_976),
        ("30/1", FrameRate.FPS_30),
        ("24/1", FrameRate.FPS_24),
        ("50/1", FrameRate.FPS_50),
        ("60000/1001", FrameRate.FPS_59_94),
        ("60/1", FrameRate.FPS_60),
    ],
)
def test_from_ffprobe_matches_known_rates(
    ffprobe_output: str, expected_member: FrameRate
) -> None:
    assert FrameRate.from_ffprobe(ffprobe_output) == expected_member


def test_from_ffprobe_returns_none_for_unknown_rate() -> None:
    assert FrameRate.from_ffprobe("17/1") is None


# -- seconds_to_rational ---------------------------------------------------


def test_seconds_to_rational_25fps() -> None:
    assert seconds_to_rational(10.0, Fraction(25, 1)) == "250/25s"


def test_seconds_to_rational_29_97fps() -> None:
    # 10s at 30000/1001 fps: round(10 * 30000/1001) = 300 frames
    # 300 frames * 1001 / 30000 = 300300/30000s
    result = seconds_to_rational(10.0, Fraction(30000, 1001))
    assert result == "300300/30000s"
    # Verify it parses back to ~10s
    parts = result.rstrip("s").split("/")
    rational = Fraction(int(parts[0]), int(parts[1]))
    assert abs(float(rational) - 10.0) < 0.04


def test_seconds_to_rational_zero() -> None:
    assert seconds_to_rational(0.0, Fraction(25, 1)) == "0/25s"
