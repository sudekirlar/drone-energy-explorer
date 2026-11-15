"""Colour checks under simulated colour-vision deficiencies, for every palette in src/theme.py.

Each colour is passed through the Machado, Oliveira & Fernandes (2009) matrices for
protanopia, deuteranopia and tritanopia (severity 1.0), converted to CIELAB, and compared with
the CIE76 colour difference (Delta E). Two colours that should be told apart must stay at least
MIN_DELTA_E apart for normal vision and for each deficiency.

MIN_DELTA_E = 10 is our working rule, not a standard: about 2.3 is just noticeable for large
patches side by side, and thin bands and small points need much more.

Complete colour blindness (achromatopsia) leaves only lightness, so it is tested on CIELAB L*
with the same threshold: the phases (and Ground), the two parts of each phase, and every ordered
palette must stay apart in grey. Two things are left to other cues on purpose. Translucent bands
lose most of their lightness differences, so the Sankey's bands lead to labelled nodes and the
timeline has a full-colour strip and a key. The K-means colours (Okabe & Ito) are not ordered by
lightness, so the parallel coordinates also show each flight's group on its own axis.

Translucent colours are tested as they appear on the page, blended with Streamlit's light and
dark background.
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
import pytest

from src import theme
from src.charts import sankey, timeline
from src.data import schema

MIN_DELTA_E = 10.0
BACKGROUNDS = {"light": "#ffffff", "dark": "#0e1117"}  # Streamlit's page colour in each theme

VISION = {
    "normal": np.eye(3),
    "protanopia": np.array(
        [
            [0.152286, 1.052583, -0.204868],
            [0.114503, 0.786281, 0.099216],
            [-0.003882, -0.048116, 1.051998],
        ]
    ),
    "deuteranopia": np.array(
        [
            [0.367322, 0.860646, -0.227968],
            [0.280085, 0.672501, 0.047413],
            [-0.011820, 0.042940, 0.968881],
        ]
    ),
    "tritanopia": np.array(
        [
            [1.255528, -0.076749, -0.178779],
            [-0.078411, 0.930809, 0.147602],
            [0.004733, 0.691367, 0.303900],
        ]
    ),
}


def _rgb(hex_colour: str) -> np.ndarray:
    h = hex_colour.lstrip("#")
    return np.array([int(h[i : i + 2], 16) for i in (0, 2, 4)], dtype=float)


def _linear(rgb: np.ndarray) -> np.ndarray:
    c = rgb / 255
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _lab(linear_rgb: np.ndarray) -> np.ndarray:
    xyz = np.array(
        [[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]
    ) @ np.clip(linear_rgb, 0, 1)
    xyz = xyz / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def _blend(hex_colour: str, alpha: float, background: str) -> np.ndarray:
    """The colour a translucent band shows on the page."""
    return alpha * _rgb(hex_colour) + (1 - alpha) * _rgb(background)


def _delta_e(a: np.ndarray, b: np.ndarray, vision: str) -> float:
    m = VISION[vision]
    return float(np.linalg.norm(_lab(m @ _linear(a)) - _lab(m @ _linear(b))))


def _lightness(hex_colour: str) -> float:
    return float(_lab(_linear(_rgb(hex_colour)))[0])


def _closest(colours: dict[str, np.ndarray]) -> tuple[float, str]:
    """The smallest difference over every pair and every type of vision, and where it is."""
    return min(
        (_delta_e(colours[a], colours[b], v), f"{a} / {b} ({v})")
        for a, b in itertools.combinations(colours, 2)
        for v in VISION
    )


MAIN_PHASES = [p for p in schema.PHASES if p != "Ground"]
SIBLINGS = [
    tuple(s for s, parent in schema.SUB_PHASE_PARENT.items() if parent == p) for p in MAIN_PHASES
]
SIBLINGS = [pair for pair in SIBLINGS if len(pair) == 2]


def test_main_phase_colours_stay_apart() -> None:
    colours = {p: _rgb(theme.PALETTES["phase"][p]) for p in MAIN_PHASES}
    value, where = _closest(colours)
    assert value >= MIN_DELTA_E, f"{where}: {value:.1f}"


@pytest.mark.parametrize("pair", SIBLINGS, ids=lambda p: "/".join(p))
def test_the_two_parts_of_a_phase_stay_apart(pair: tuple[str, str]) -> None:
    colours = {s: _rgb(theme.PALETTES["sub_phase"][s]) for s in pair}
    value, where = _closest(colours)
    assert value >= MIN_DELTA_E, f"{where}: {value:.1f}"


@pytest.mark.parametrize("background", BACKGROUNDS)
def test_sankey_main_bands_stay_apart_on_the_page(background: str) -> None:
    colours = {
        p: _blend(theme.PALETTES["phase"][p], sankey.LINK_ALPHA_MAIN, BACKGROUNDS[background])
        for p in MAIN_PHASES
    }
    value, where = _closest(colours)
    assert value >= MIN_DELTA_E, f"{where} on the {background} theme: {value:.1f}"


@pytest.mark.parametrize("background", BACKGROUNDS)
@pytest.mark.parametrize("pair", SIBLINGS, ids=lambda p: "/".join(p))
def test_sankey_sub_phase_bands_stay_apart_on_the_page(
    pair: tuple[str, str], background: str
) -> None:
    colours = {
        s: _blend(theme.PALETTES["sub_phase"][s], sankey.LINK_ALPHA_SUB, BACKGROUNDS[background])
        for s in pair
    }
    value, where = _closest(colours)
    assert value >= MIN_DELTA_E, f"{where} on the {background} theme: {value:.1f}"


def test_payload_colours_stay_apart_and_get_darker_with_weight() -> None:
    payloads = [p for p in sorted(theme.PALETTES["payload"]) if p in (0, 250, 500)]
    colours = {f"{p} g": _rgb(theme.PALETTES["payload"][p]) for p in payloads}
    value, where = _closest(colours)
    assert value >= MIN_DELTA_E, f"{where}: {value:.1f}"
    # Ordered by lightness, so the order survives even without colour vision.
    lightness = [_lightness(theme.PALETTES["payload"][p]) for p in payloads]
    assert lightness == sorted(lightness, reverse=True)


def test_viridis_gets_lighter_step_by_step() -> None:
    lightness = [_lightness(c) for c in theme.PALETTES["viridis"]]
    assert all(b - a >= MIN_DELTA_E for a, b in itertools.pairwise(lightness))


def test_diverging_scale_is_lightest_at_zero() -> None:
    """Without colour vision, the distance from zero must still show as darkness."""
    lightness = [_lightness(c) for c in _scale_colours(theme.PALETTES["diverging"])]
    centre = len(lightness) // 2
    # Lighter step by step towards zero from both ends (the three colours around zero are all
    # near white, so the grey at zero may be a point darker than its neighbours).
    assert lightness[:centre] == sorted(lightness[:centre])
    assert lightness[centre + 1 :] == sorted(lightness[centre + 1 :], reverse=True)
    assert max(lightness) - lightness[centre] < 2
    assert min(lightness[centre] - lightness[0], lightness[centre] - lightness[-1]) >= MIN_DELTA_E


def _scale_colours(scale: list) -> list[str]:
    return [c[1] if isinstance(c, list | tuple) else c for c in scale]


@pytest.mark.parametrize("k", range(2, 7))
def test_k_means_group_colours_stay_apart(k: int) -> None:
    """The K-means slider goes up to 6 groups, coloured with the first k categorical colours."""
    colours = {c: _rgb(c) for c in theme.PALETTES["categorical"][:k]}
    value, where = _closest(colours)
    assert value >= MIN_DELTA_E, f"{where}: {value:.1f}"


def test_timeline_shows_the_phases_at_full_strength() -> None:
    """The faint bands behind the timeline are too pale to tell phases apart for every reader,
    so the phases are also drawn in full colour in a strip above the panels."""
    pale = {
        p: _blend(theme.PALETTES["phase"][p], timeline.BAND_OPACITY, "#ffffff") for p in MAIN_PHASES
    }
    assert _closest(pale)[0] < MIN_DELTA_E  # why the strip exists
    phases = ["Ground", "Take-off", "Cruise", "Manoeuvre", "Cruise", "Landing", "Ground"]
    telemetry = pd.DataFrame(
        {
            "flight": 1,
            "t_s": np.arange(len(phases), dtype=float),
            "power_w": 400.0,
            "ground_speed_mps": 5.0,
            "airspeed_mps": 5.0,
            "alt_rel_m": 20.0,
            "voltage_v": 23.0,
            "phase": phases,
            "sub_phase": "Straight leg",
        }
    )
    fig = timeline.build_timeline(telemetry, 1, show_phases=True)
    strip = [s for s in fig.layout.shapes if s.yref == "paper" and s.type == "rect"]
    assert {s.fillcolor for s in strip} == {theme.PALETTES["phase"][p] for p in set(phases)}
    assert all(s.opacity is None or s.opacity == 1 for s in strip)


# ---- complete colour blindness (achromatopsia): only lightness is left ----------------------


def _closest_in_grey(colours: dict[str, str]) -> tuple[float, str]:
    return min(
        (abs(_lightness(colours[a]) - _lightness(colours[b])), f"{a} / {b}")
        for a, b in itertools.combinations(colours, 2)
    )


def test_phases_stay_apart_in_grey() -> None:
    """Map, cube, timeline strip, flight heatmap and Sankey nodes, including Ground."""
    value, where = _closest_in_grey(dict(theme.PALETTES["phase"]))
    assert value >= MIN_DELTA_E, f"{where}: {value:.1f}"


@pytest.mark.parametrize("pair", SIBLINGS, ids=lambda p: "/".join(p))
def test_the_two_parts_of_a_phase_stay_apart_in_grey(pair: tuple[str, str]) -> None:
    value, where = _closest_in_grey({s: theme.PALETTES["sub_phase"][s] for s in pair})
    assert value >= MIN_DELTA_E, f"{where}: {value:.1f}"


def test_payload_colours_stay_apart_in_grey() -> None:
    value, where = _closest_in_grey({f"{p} g": theme.PALETTES["payload"][p] for p in (0, 250, 500)})
    assert value >= MIN_DELTA_E, f"{where}: {value:.1f}"
