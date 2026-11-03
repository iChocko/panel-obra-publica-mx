"""Shared visual system for the README figures (executive style).

Light chart cards that read well on GitHub's light and dark themes,
plus dark hero banners and dark maps.
"""
from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch

# ---------- palette ----------
NAVY = "#0A1A2F"
NAVY_2 = "#10284A"
NAVY_3 = "#1B3A63"
INK = "#0F172A"
TEXT = "#1E293B"
MUTED = "#64748B"
SOFT = "#94A3B8"
GRID = "#E6EAF0"
CARD = "#FFFFFF"
PAPER = "#F7F9FC"

AMBER = "#F5A524"
TEAL = "#14B8A6"
CORAL = "#EF5B5B"
BLUE = "#3B82F6"
INDIGO = "#6366F1"
SLATE = "#CBD5E1"

SEQ_WARM = ["#2A1B3D", "#5B2A5E", "#93355F", "#C9474F", "#EE6A3A", "#F9A03F", "#FCD581", "#FFF6D5"]

FONT = "Inter"
FONT_DISPLAY = "Inter Display"


def setup() -> None:
    names = {f.name for f in font_manager.fontManager.ttflist}
    family = FONT if FONT in names else "DejaVu Sans"
    mpl.rcParams.update({
        "font.family": family,
        "font.size": 11,
        "axes.edgecolor": GRID,
        "axes.labelcolor": MUTED,
        "axes.titleweight": "semibold",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": GRID,
        "grid.linewidth": 0.9,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "legend.frameon": False,
        "figure.dpi": 100,
        "savefig.dpi": 200,
        "svg.fonttype": "none",
    })


def display_font() -> str:
    names = {f.name for f in font_manager.fontManager.ttflist}
    return FONT_DISPLAY if FONT_DISPLAY in names else mpl.rcParams["font.family"][0]


def card(figsize=(12, 6.2), top=None, bottom=0.14, left=0.07, right=0.97, bg=CARD, top_in=1.75):
    """Figure laid out as a rounded card with room for title, subtitle and source."""
    fig = plt.figure(figsize=figsize, facecolor="none")
    if top is None:
        top = 1 - top_in / figsize[1]
    fig.patches.append(FancyBboxPatch((0.004, 0.006), 0.992, 0.988, boxstyle="round,pad=0,rounding_size=0.018",
                                      transform=fig.transFigure, facecolor=bg, edgecolor="#DCE3EC",
                                      linewidth=1.2, zorder=-10))
    ax = fig.add_axes([left, bottom, right - left, top - bottom])
    ax.set_facecolor("none")
    return fig, ax


def heading(fig, title: str, subtitle: str | None = None, kicker: str | None = None,
            color=INK, sub_color=MUTED, kicker_color=AMBER, x=0.035):
    """Title block positioned in inches from the top so it never clips."""
    df = display_font()
    h = fig.get_figheight()
    y = lambda inch: 1 - inch / h  # noqa: E731
    if kicker:
        fig.text(x, y(0.36), kicker.upper(), fontsize=10, fontweight="bold", color=kicker_color,
                 family=df, va="top")
    fig.text(x, y(0.60), title, fontsize=21, fontweight="semibold", color=color, family=df, va="top")
    if subtitle:
        fig.text(x, y(1.08), subtitle, fontsize=12, color=sub_color, va="top")


def top_at(fig, inches: float) -> float:
    """Figure fraction that sits `inches` below the top edge."""
    return 1 - inches / fig.get_figheight()


def source(fig, text: str, color=SOFT, x=0.035, y=0.035):
    fig.text(x, y, text, fontsize=9, color=color, va="bottom")


def save(fig, path):
    fig.savefig(path, facecolor=fig.get_facecolor(), transparent=True, bbox_inches=None, pad_inches=0)
    plt.close(fig)
