"""
visualize.py — 웜퍼스 세계와 에이전트 이동 경로·지식 상태 시각화 (matplotlib)
"""
from __future__ import annotations
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Rectangle, Circle, RegularPolygon

for _f in ("Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR"):
    if any(_f == f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = _f
        break
plt.rcParams["axes.unicode_minus"] = False

C_VISITED, C_SAFE, C_PIT, C_WUMP, C_UNK = "#CFE8E4", "#E7F5D9", "#F6D3D3", "#F9E1C4", "#FFFFFF"


def draw_world(ax, world, agent=None, title=None):
    n = world.size
    for x in range(1, n + 1):
        for y in range(1, n + 1):
            c = (x, y)
            fill = C_UNK
            if agent is not None:
                if c in agent.visited: fill = C_VISITED
                elif c in agent.safe: fill = C_SAFE
                elif c in agent.known_pit: fill = C_PIT
                elif c == agent.known_wumpus: fill = C_WUMP
            ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, facecolor=fill, edgecolor="#1F2147", lw=1.5))
            ax.text(x - 0.44, y - 0.44, f"{x},{y}", fontsize=7, color="#5B6070", va="bottom")
            if c in world.pits:
                ax.add_patch(Circle((x + 0.18, y + 0.18), 0.2, color="#2B2B2B"))
                ax.text(x + 0.18, y + 0.18, "P", color="white", ha="center", va="center", fontsize=9, weight="bold")
            if c == world.wumpus:
                col = "#C0392B" if world.wumpus_alive else "#9AA0B2"
                ax.text(x - 0.18, y + 0.18, "W", color=col, ha="center", va="center", fontsize=15, weight="bold")
            if c == world.gold:
                ax.add_patch(RegularPolygon((x + 0.2, y - 0.2), 5, radius=0.14, color="#E08A17"))
    ax.set_xlim(0.5, n + 0.5); ax.set_ylim(0.5, n + 0.5)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    if title: ax.set_title(title, fontsize=11)


def draw_path(ax, trajectory):
    pts = [t[0] for t in trajectory]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    ax.plot(xs, ys, "-", color="#2A9D8F", lw=3, alpha=0.75, zorder=5)
    for i in range(1, len(pts)):
        if pts[i] != pts[i - 1]:
            ax.annotate("", xy=pts[i], xytext=pts[i - 1],
                        arrowprops=dict(arrowstyle="->", color="#1F2147", lw=1.6), zorder=6)
    ax.plot(*pts[0], "o", color="#1F2147", ms=9, zorder=7)
    for i, (pos, d, a) in enumerate(trajectory):
        if a == "Shoot":
            ax.text(pos[0], pos[1] - 0.3, "Shoot!", ha="center", fontsize=8, color="#C0392B", zorder=8)
        if a == "Grab":
            ax.text(pos[0], pos[1] + 0.32, "Grab", ha="center", fontsize=8, color="#E08A17", weight="bold", zorder=8)


def legend(ax):
    from matplotlib.patches import Patch
    items = [Patch(facecolor=C_VISITED, edgecolor="#1F2147", label="방문한 칸"),
             Patch(facecolor=C_SAFE, edgecolor="#1F2147", label="안전(추론)·미방문"),
             Patch(facecolor=C_PIT, edgecolor="#1F2147", label="구덩이 확정(추론)"),
             Patch(facecolor=C_WUMP, edgecolor="#1F2147", label="웜퍼스 확정(추론)"),
             Patch(facecolor=C_UNK, edgecolor="#1F2147", label="미확인")]
    ax.legend(handles=items, loc="upper left", bbox_to_anchor=(1.02, 1.0), fontsize=9, frameon=False)


def save_episode(world, agent, path, title=None):
    fig, ax = plt.subplots(figsize=(6.4, 4.6), dpi=150)
    draw_world(ax, world, agent, title)
    draw_path(ax, world.trajectory)
    legend(ax)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path
