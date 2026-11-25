"""
chart_style.py — 발표용 그래프 공통 스타일 (탐험 GIF와 같은 어두운 화면)

  폰트: 나눔고딕코딩 하나 (Colab: !apt-get -qq install fonts-nanum)
  색  : 배경 #14161b, 글씨 크림색, 강조 주황·빨강·초록·파랑
  제목: 그래프 가운데, 단어마다 색을 다르게 줄 수 있음 (색이 곧 범례)
"""
from __future__ import annotations
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

BG, GRID, ZONE = "#14161b", "#2b2f39", "#1f222a"
CREAM, AMBER, RED, GREEN, BLUE = "#f3eee3", "#ffb000", "#ff5d73", "#7ee081", "#5ab4ff"

_NANUM = "/usr/share/fonts/truetype/nanum/"


def mono(size, bold=False):
    path = _NANUM + ("NanumGothicCodingBold.ttf" if bold else "NanumGothicCoding.ttf")
    return FontProperties(fname=path, size=size) if os.path.exists(path) else FontProperties(size=size)


def new_chart(figsize=(10, 5.6)):
    fig, ax = plt.subplots(figsize=figsize, dpi=150, facecolor=BG)
    ax.set_facecolor(BG)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(labelcolor=CREAM, length=0, pad=6)
    return fig, ax


def finish_ticks(ax, size=10):
    for lab in ax.get_xticklabels() + ax.get_yticklabels():
        lab.set_fontproperties(mono(size))
        lab.set_color(CREAM)


def centered_title(fig, ax, parts, y=.92, size=22):
    """parts = [("TT", RED), (" VS ", CREAM), ("DPLL", AMBER)] — 그래프 영역 가운데에 이어 붙인다."""
    texts = [fig.text(0, y, w, fontproperties=mono(size, True), color=c) for w, c in parts]
    fig.canvas.draw()
    inv = fig.transFigure.inverted()
    widths = []
    for t in texts:
        (x0, _), (x1, _) = inv.transform(t.get_window_extent().get_points())
        widths.append(x1 - x0)
    box = ax.get_position()
    x = (box.x0 + box.x1) / 2 - sum(widths) / 2
    for t, w in zip(texts, widths):
        t.set_x(x)
        x += w


def save(fig, path, tight=False):
    """tight=False면 모든 그래프가 같은 크기(1500x780)로 저장된다 → PPT에 나란히 넣기 좋음"""
    fig.savefig(path, facecolor=BG, bbox_inches="tight" if tight else None)
    plt.close(fig)
    return path
