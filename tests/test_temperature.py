import pytest

from eightctl_web.service import _adjust_level, _format_level  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize(
    ("raw", "display"),
    [
        (-100, "-10"),
        (-35, "-4"),
        (-34, "-3"),
        (-25, "-3"),
        (-24, "-2"),
        (-5, "-1"),
        (-4, "0"),
        (0, "0"),
        (4, "0"),
        (5, "1"),
        (24, "2"),
        (25, "3"),
        (100, "10"),
    ],
)
def test_format_level_rounds_to_nearest_app_level(raw: int, display: str) -> None:
    assert _format_level(raw) == display


@pytest.mark.parametrize(
    ("raw", "delta", "expected"),
    [(-24, 10, -10), (-24, -10, -30), (-26, 10, -20), (99, 10, 100), (-99, -10, -100)],
)
def test_adjust_level_moves_one_visible_step(raw: int, delta: int, expected: int) -> None:
    assert _adjust_level(raw, delta) == expected
