"""
viz_game.py — 탐험 과정 GIF (게임 화면 스타일)

  python viz_game.py --world worlds/world_shoot.txt          # → results/game_world_shoot.gif
  python viz_game.py --world worlds/world_fig7_2.txt --fps 1.5   # 더 느리게
  python viz_game.py --seed 7 --png 31                      # 31번째 턴만 PNG로 (슬라이드용 정지 화면)

화면 구성
  왼쪽  던전 지도: 안개(?) = 아직 모르는 칸, 모래색 = 가 본 칸, 초록 = 안전하다고 증명된 칸,
                   PIT / W = 추론으로 확정한 구덩이 / 웜퍼스, 흐린 점선 원·흐린 w = 실제 정답(에이전트는 모름)
  오른쪽 상태판: 턴 진행 막대, 지각 램프 5개, 이번 동작, 점수, KB 크기
폰트: 나눔고딕코딩(숫자·영문) + 나눔스퀘어라운드(한글) — Colab은  !apt-get -qq install fonts-nanum
"""
from __future__ import annotations
import argparse
import math
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyBboxPatch, Circle, Wedge, RegularPolygon, Rectangle

from wumpus_env import WumpusWorld
from agent import HybridWumpusAgent
from viz_plus import record_episode, setup_korean_font

ROOT = Path(__file__).resolve().parent

# ------------------------------------------------------------------ 팔레트 (던전)
BG, PANEL, FOG, FOG_Q = "#14161b", "#1f222a", "#2b2f39", "#4a505e"
FLOOR, FLOOR_INK, SAFE, PIT_C, WUMP_C = "#eadcb9", "#9b8a66", "#7fc58a", "#08090b", "#9e2236"
AMBER, CREAM, DIM, RED, GREEN = "#ffb000", "#f3eee3", "#8a909d", "#ff5d73", "#7ee081"
LAMPS = [("냄새", "stench", "#a3d13b"), ("바람", "breeze", "#5ab4ff"), ("반짝", "glitter", "#ffd23f"),
         ("부딪힘", "bump", "#c792ea"), ("비명", "scream", RED)]
ACTION_KR = {"Forward": "앞으로", "TurnLeft": "왼쪽으로 돌기", "TurnRight": "오른쪽으로 돌기",
             "Grab": "금 줍기", "Shoot": "화살 쏘기", "Climb": "동굴 탈출"}

# ------------------------------------------------------------------ 폰트
_NANUM = "/usr/share/fonts/truetype/nanum/"
_FONT_FILES = {"mono": ["NanumGothicCodingBold.ttf", "NanumGothicCoding.ttf"],
               "round": ["NanumSquareRoundB.ttf", "NanumSquareRoundR.ttf", "NanumSquareB.ttf"],
               "round_r": ["NanumSquareRoundR.ttf", "NanumSquareR.ttf"]}


def font(kind, size):
    for name in _FONT_FILES[kind]:
        if os.path.exists(_NANUM + name):
            return FontProperties(fname=_NANUM + name, size=size)
    return FontProperties(size=size)               # 없으면 setup_korean_font()가 정한 기본 글꼴


def T(ax, x, y, s, kind="round", size=10, color=CREAM, **kw):
    return ax.text(x, y, s, fontproperties=font(kind, size), color=color, **kw)


# ------------------------------------------------------------------ 지도
def draw_map(ax, world, f):
    ax.clear(); ax.set_facecolor(BG)
    n = world.size
    for x in range(1, n + 1):
        for y in range(1, n + 1):
            c = (x, y)
            if c in f["visited"]: fill, ink = FLOOR, FLOOR_INK
            elif c in f["known_pit"]: fill, ink = PIT_C, DIM
            elif c == f["known_wumpus"] and not f["wumpus_dead"]: fill, ink = WUMP_C, CREAM
            elif c in f["safe"]: fill, ink = SAFE, "#2f5d3a"
            else: fill, ink = FOG, FOG_Q
            ax.add_patch(FancyBboxPatch((x - .45, y - .45), .9, .9, boxstyle="round,pad=0,rounding_size=.09",
                                        facecolor=fill, edgecolor="none"))
            T(ax, x - .39, y - .39, f"{x},{y}", "mono", 7, ink, va="bottom")
            if fill == FOG:
                T(ax, x, y + .02, "?", "mono", 20, FOG_Q, ha="center", va="center")
            elif fill == PIT_C:
                ax.add_patch(Circle((x, y + .04), .24, facecolor="none", edgecolor=RED, lw=2))
                T(ax, x, y - .3, "PIT", "mono", 8, RED, ha="center", va="center")
            elif fill == WUMP_C:
                T(ax, x, y + .04, "W", "mono", 22, CREAM, ha="center", va="center")
            elif fill == SAFE:
                T(ax, x, y - .3, "SAFE", "mono", 7.5, "#2f5d3a", ha="center", va="center")
            # 이 칸에서 받은 지각 → 색 점
            p = f["seen"].get(c)
            if p is not None:
                dots = [col for _, key, col in LAMPS[:3] if getattr(p, key)]
                for k, col in enumerate(dots):
                    ax.add_patch(Circle((x + .34 - k * .13, y + .34), .05, color=col, zorder=4))
            # 실제 정답 (에이전트는 모름) — 아주 흐리게
            if c in world.pits and fill != PIT_C:
                ax.add_patch(Circle((x, y + .04), .24, facecolor="none", edgecolor="#6b7180", lw=1.2, ls=(0, (2, 2))))
            if c == world.wumpus:
                if f["world_wumpus_alive"] and fill != WUMP_C:
                    T(ax, x - .22, y + .2, "w", "mono", 13, "#b3485a", ha="center", va="center", alpha=.8)
                elif not f["world_wumpus_alive"]:
                    T(ax, x - .2, y + .2, "x", "mono", 13, DIM, ha="center", va="center")
            if c == world.gold and not f.get("_grabbed"):
                ax.add_patch(RegularPolygon((x + .22, y - .16), 4, radius=.11, color="#ffd23f", zorder=4))
    # 지나온 길
    pts = f["path"]
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=AMBER, lw=2, ls=(0, (1, 2.2)),
            alpha=.85, zorder=5, solid_capstyle="round", dash_capstyle="round")
    # 화살
    (axp, ayp), d = f["after"]
    dx, dy = {0: (1, 0), 1: (0, 1), 2: (-1, 0), 3: (0, -1)}[d]
    if f["action"] == "Shoot":
        ex = min(max(axp + dx * 9, .55), n + .45); ey = min(max(ayp + dy * 9, .55), n + .45)
        ax.annotate("", xy=(ex, ey), xytext=(axp + dx * .25, ayp + dy * .25),
                    arrowprops=dict(arrowstyle="-|>", color=RED, lw=3, mutation_scale=18), zorder=9)
    # 에이전트 (입 벌린 원 = 바라보는 방향)
    ang = {0: 0, 1: 90, 2: 180, 3: 270}[d]
    ax.add_patch(Wedge((axp, ayp), .21, ang + 32, ang - 32 + 360, facecolor=AMBER, edgecolor=BG, lw=2, zorder=8))
    ax.add_patch(Circle((axp - .05 * dy + .02 * dx, ayp + .05 * dx + .02 * dy), .025, color=BG, zorder=9))
    ax.set_xlim(.5, n + .5); ax.set_ylim(.5, n + .5); ax.set_aspect("equal"); ax.axis("off")


# ------------------------------------------------------------------ 상태판
def pill(ax, x, y, w, h, color, **kw):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={h / 2}",
                                facecolor=color, edgecolor="none", transform=ax.transAxes, **kw))


def draw_hud(ax, f, total, score):
    ax.clear(); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0,rounding_size=.04",
                                facecolor=PANEL, edgecolor="none", transform=ax.transAxes))
    L = .07
    # 지각 램프 — 에이전트가 이번 턴에 서 있는 칸에서 감지한 신호 5가지
    T(ax, L, .9, "지각 (이번 칸에서 감지한 신호)", "round_r", 9, DIM, transform=ax.transAxes)
    w, gap = .155, .022
    for i, (kr, key, col) in enumerate(LAMPS):
        on = getattr(f["percept"], key)
        x = L + i * (w + gap)
        pill(ax, x, .78, w, .075, col if on else FOG)
        T(ax, x + w / 2, .8175, kr, "round", 8.5, BG if on else "#5c6270", ha="center", va="center",
          transform=ax.transAxes)
    # 동작
    T(ax, L, .67, "ACTION", "mono", 9, DIM, transform=ax.transAxes)
    T(ax, L, .575, f["action"].upper(), "mono", 22, RED if f["action"] == "Shoot" else AMBER,
      va="center", transform=ax.transAxes)
    T(ax, L, .505, ACTION_KR[f["action"]], "round_r", 10, CREAM, va="center", transform=ax.transAxes)
    # 점수
    T(ax, L, .4, "SCORE", "mono", 9, DIM, transform=ax.transAxes)
    T(ax, L, .315, f"{score:+d}" if score else "0", "mono", 22, GREEN if score >= 0 else RED,
      va="center", transform=ax.transAxes)
    # 작은 정보 줄
    (x0, y0), _ = f["after"]                       # 이번 동작을 한 뒤의 위치 (지도 위 에이전트와 같음)
    info = f"위치 [{x0},{y0}]   KB {f['kb']}절   안전 칸 {len(f['safe'])}"
    T(ax, L, .17, info, "round_r", 9, DIM, transform=ax.transAxes)
    # 색 설명 (한 줄, 상태판 안)
    keys = [(FLOOR, "방문"), (SAFE, "안전"), (FOG, "모름"), (PIT_C, "구덩이"), (WUMP_C, "웜퍼스")]
    for i, (col, lab) in enumerate(keys):
        x = L + i * .172
        ax.add_patch(FancyBboxPatch((x, .045), .03, .03, boxstyle="round,pad=0,rounding_size=.006",
                                    facecolor=col, edgecolor="#3a3f4a", lw=.8, transform=ax.transAxes))
        T(ax, x + .042, .06, lab, "round_r", 7.5, DIM, va="center", transform=ax.transAxes)


# ------------------------------------------------------------------ 합치기
def _mark_grab(frames):
    g = False
    for f in frames:
        g = g or f["action"] == "Grab"
        f["_grabbed"] = g


def draw_turnbar(ax, t, total):
    """화면 맨 위: 턴 진행 막대"""
    ax.clear(); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    T(ax, 0, .5, "TURN", "mono", 11, DIM, va="center", transform=ax.transAxes)
    x0, x1 = .065, .9
    ax.plot([x0, x1], [.5, .5], color=FOG, lw=10, solid_capstyle="round", transform=ax.transAxes)
    ax.plot([x0, x0 + (x1 - x0) * t / total], [.5, .5], color=AMBER, lw=10, solid_capstyle="round",
            transform=ax.transAxes)
    T(ax, 1, .5, f"{t:>2} / {total}", "mono", 14, CREAM, ha="right", va="center", transform=ax.transAxes)


def _figure():
    fig = plt.figure(figsize=(9.6, 5.4), dpi=100, facecolor=BG)
    tax = fig.add_axes([.035, .895, .93, .07])
    gax = fig.add_axes([.03, .04, .47, .835]); hax = fig.add_axes([.53, .04, .44, .835])
    return fig, tax, gax, hax


def save_game_gif(world, frames, path, name="", sub="", fps=2, hold=2.5):
    """fps 2 = 한 턴에 0.5초. 마지막 장면은 hold초 동안 멈춰 있다."""
    _mark_grab(frames)
    total = len(frames)
    seq = list(range(total)) + [total - 1] * int(fps * hold)
    fig, tax, gax, hax = _figure()

    def update(k):
        f = frames[seq[k]]
        draw_turnbar(tax, f["t"], total)
        draw_map(gax, world, f)
        draw_hud(hax, f, total, f["score"])
    FuncAnimation(fig, update, frames=len(seq)).save(path, writer=PillowWriter(fps=fps))
    plt.close(fig)
    return path


def save_game_png(world, frames, path, turn, name="", sub=""):
    _mark_grab(frames)
    f = frames[min(max(turn, 1), len(frames)) - 1]
    fig, tax, gax, hax = _figure()
    draw_turnbar(tax, f["t"], len(frames))
    draw_map(gax, world, f)
    draw_hud(hax, f, len(frames), f["score"])
    fig.savefig(path, dpi=200, facecolor=BG); plt.close(fig)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--world"); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--engine", default="dpll", choices=["dpll", "tt"])
    ap.add_argument("--policy", default="safe", choices=["safe", "risk"])
    ap.add_argument("--fps", type=float, default=2, help="초당 턴 수 (작을수록 느림)")
    ap.add_argument("--png", type=int, help="이 턴의 정지 화면만 PNG로 저장")
    a = ap.parse_args()
    setup_korean_font(verbose=False)
    if a.world:
        world, name = WumpusWorld.from_file(a.world), Path(a.world).stem
    else:
        world, name = WumpusWorld.random(seed=a.seed), f"seed {a.seed}"
    frames = record_episode(world, HybridWumpusAgent(method=a.engine, policy=a.policy))
    sub = f"{a.engine.upper()} · {a.policy.upper()}"
    out = ROOT / "results"; out.mkdir(exist_ok=True)
    stem = name.replace(" ", "")
    if a.png:
        print("저장:", save_game_png(world, frames, out / f"game_{stem}_t{a.png}.png", a.png, name, sub))
    else:
        print("저장:", save_game_gif(world, frames, out / f"game_{stem}.gif", name, sub, a.fps))


if __name__ == "__main__":
    main()
