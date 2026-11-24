"""
viz_plus.py — 발표·보고서용 시각화 확장 (visualize.py는 그대로 두고 추가로 쓰는 모듈)

  1) 탐험 과정 애니메이션 (GIF)       : 매 턴 에이전트의 '믿음'(안전/구덩이/웜퍼스 추론)과 실제 세계를 함께
  2) 지식 변화 단계별 패널 (PNG)       : 중요한 순간 6장을 한 장에 — PPT 한 쪽에 넣기 좋음
  3) 실험 대시보드 (PNG)              : 정책·사격별 결과 비율, 평균 점수, 추론 엔진별 ASK 시간

  python viz_plus.py --world worlds/world_fig7_2.txt          # → results/anim_world_fig7_2.gif, results/steps_world_fig7_2.png
  python viz_plus.py --world worlds/world_shoot.txt --fps 4
  python viz_plus.py --seed 7                                 # 무작위 세계
  python viz_plus.py --experiments 300                        # → results/experiments.png  (1000이면 1~2분)

Colab:  한글이 □로 깨지면 먼저  !apt-get -qq install fonts-nanum  (설치 후 런타임 재시작 없이 바로 적용됨)
※ agent.py · wumpus_env.py 는 수정하지 않습니다. 에이전트를 감싸서(record_episode) 매 턴 상태를 복사해 둡니다.
"""
from __future__ import annotations
import argparse
import glob
import os
import statistics as st
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import Rectangle, Circle, RegularPolygon, Polygon, Patch

from wumpus_env import WumpusWorld, gold_reachable
from agent import HybridWumpusAgent, RandomAgent

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"

# ------------------------------------------------------------------ 한글 폰트
FONT_PATHS = ["/usr/share/fonts/truetype/nanum/NanumGothic.ttf",          # Colab / Ubuntu (fonts-nanum)
              "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
              "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
              "C:/Windows/Fonts/malgun.ttf",                               # Windows
              "/System/Library/Fonts/Supplemental/AppleGothic.ttf",        # macOS
              "/Library/Fonts/AppleGothic.ttf"]


def setup_korean_font(verbose=True):
    """설치된 한글 폰트를 matplotlib에 '직접 등록'한다.
    Colab에서 apt로 폰트를 깔아도 matplotlib 캐시가 갱신되지 않아 □로 깨지는 문제를 피한다."""
    if "google.colab" in sys.modules and not any(os.path.exists(p) for p in FONT_PATHS):
        os.system("apt-get -qq install -y fonts-nanum > /dev/null 2>&1")
    found = [p for p in FONT_PATHS + sorted(glob.glob("/usr/share/fonts/**/Nanum*.ttf", recursive=True))
             if os.path.exists(p)]
    for path in found:                                   # 굵은 글꼴(Bold)도 함께 등록
        font_manager.fontManager.addfont(path)
    if found:
        name = font_manager.FontProperties(fname=found[0]).get_name()
        plt.rcParams["font.family"] = name
        plt.rcParams["axes.unicode_minus"] = False
        return name
    if verbose:
        print("⚠️ 한글 폰트를 찾지 못했습니다. Colab이면  !apt-get -qq install fonts-nanum  후 다시 실행하세요.")
    return None


# ------------------------------------------------------------------ 색
C_VISITED, C_SAFE, C_PIT, C_WUMP, C_UNK = "#CFE8E4", "#E7F5D9", "#F6D3D3", "#F9E1C4", "#FFFFFF"
INK, QUIET, LINE = "#1F2147", "#6B7080", "#2A9D8F"
OUTCOME_COLOR = {"win": "#2A9D8F", "climb": "#B8C4CC", "death": "#D1495B", "timeout": "#F2C14E"}


# ------------------------------------------------------------------ 기록
def record_episode(world, agent):
    """에피소드를 실행하면서 매 턴의 (지각, 동작, 추론 결과, 점수)를 복사해 둔다."""
    frames, seen = [], {}
    percept = world.reset()
    path = [world.agent]
    while not world.done:
        pos, d = agent.pos, agent.dir
        action = agent(percept)
        seen.setdefault(pos, percept)
        f = dict(t=agent.t, pos=pos, dir=d, percept=percept, action=action,
                 visited=set(agent.visited), safe=set(agent.safe), known_pit=set(agent.known_pit),
                 known_wumpus=agent.known_wumpus, wumpus_dead=agent.wumpus_dead,
                 kb=len(agent.kb), plan=list(agent.plan), seen=dict(seen))
        percept, _, _ = world.step(action)
        path.append(world.agent)
        f.update(score=world.score, path=list(path), after=(world.agent, world.direction),
                 world_wumpus_alive=world.wumpus_alive)
        frames.append(f)
    return frames


# ------------------------------------------------------------------ 그리기
def _percept_words(p):
    ws = [w for w, v in (("Stench", p.stench), ("Breeze", p.breeze), ("Glitter", p.glitter),
                         ("Bump", p.bump), ("Scream", p.scream)) if v]
    return ", ".join(ws) if ws else "없음"


def draw_frame(ax, world, f, show_truth=True, compact=False):
    """한 턴의 상태를 격자에 그린다. 칸 색 = 에이전트의 '믿음', 옅은 기호 = 실제 세계(에이전트는 모름)"""
    ax.clear()
    n = world.size
    for x in range(1, n + 1):
        for y in range(1, n + 1):
            c = (x, y)
            fill = C_UNK
            if c in f["visited"]: fill = C_VISITED
            elif c in f["safe"]: fill = C_SAFE
            elif c in f["known_pit"]: fill = C_PIT
            elif c == f["known_wumpus"]: fill = C_WUMP
            ax.add_patch(Rectangle((x - .5, y - .5), 1, 1, facecolor=fill, edgecolor=INK, lw=1.3))
            if not compact:
                ax.text(x - .45, y - .45, f"{x},{y}", fontsize=6.5, color=QUIET, va="bottom")
            # 실제 세계 (정답) — 옅게
            if show_truth:
                if c in world.pits:
                    ax.add_patch(Circle((x + .2, y + .2), .17, facecolor="none", edgecolor="#555", lw=1, ls="--", alpha=.6))
                    ax.text(x + .2, y + .2, "P", color="#555", ha="center", va="center", fontsize=8, alpha=.7)
                if c == world.wumpus:
                    alive = f["world_wumpus_alive"]
                    ax.text(x - .2, y + .2, "W", color="#C0392B" if alive else "#9AA0B2", ha="center", va="center",
                            fontsize=13, weight="bold", alpha=.55)
                if c == world.gold and not f.get("_grabbed"):
                    ax.add_patch(RegularPolygon((x + .22, y - .2), 5, radius=.12, color="#E08A17", alpha=.55))
            # 이 칸에서 받은 지각 (에이전트가 아는 것)
            p = f["seen"].get(c)
            if p is not None:
                tags = [s for s, v in (("B", p.breeze), ("S", p.stench), ("G", p.glitter)) if v]
                if tags:
                    ax.text(x + .45, y - .45, " ".join(tags), fontsize=7.5, ha="right", va="bottom",
                            color="#1D4E89", weight="bold")
            if fill == C_PIT and not compact:
                ax.text(x, y - .05, "구덩이?!", ha="center", fontsize=7, color="#A33")
            if fill == C_WUMP and not compact:
                ax.text(x, y - .05, "웜퍼스!", ha="center", fontsize=7, color="#A55B00")
    # 지나온 길
    pts = f["path"]
    ax.plot([p[0] for p in pts], [p[1] for p in pts], "-", color=LINE, lw=2.5, alpha=.6, zorder=5)
    # 에이전트 (방향 삼각형)
    (ax_, ay), d = f["after"]
    dx, dy = {0: (1, 0), 1: (0, 1), 2: (-1, 0), 3: (0, -1)}[d]
    tri = [(ax_ + .2 * dx, ay + .2 * dy), (ax_ - .12 * dx - .11 * dy, ay - .12 * dy + .11 * dx),
           (ax_ - .12 * dx + .11 * dy, ay - .12 * dy - .11 * dx)]
    ax.add_patch(Polygon(tri, closed=True, color=INK, zorder=8))
    if f["action"] == "Shoot":
        ex, ey = ax_ + dx * 3.5, ay + dy * 3.5
        ax.annotate("", xy=(min(max(ex, .5), n + .5), min(max(ey, .5), n + .5)), xytext=(ax_, ay),
                    arrowprops=dict(arrowstyle="-|>", color="#C0392B", lw=2, ls="--"), zorder=9)
    ax.set_xlim(.5, n + .5); ax.set_ylim(.5, n + .5)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)


def draw_info(ax, f, total):
    ax.clear(); ax.axis("off")
    lines = [("턴", f"{f['t']} / {total}"),
             ("위치", f"[{f['pos'][0]},{f['pos'][1]}]"),
             ("지각", _percept_words(f["percept"])),
             ("동작", f["action"]),
             ("KB 절 수", str(f["kb"])),
             ("안전·미방문 칸", str(len(f["safe"] - f["visited"]))),
             ("점수", str(f["score"])),
             ("남은 계획", " ".join(a.replace("Turn", "T").replace("Forward", "F") for a in f["plan"][:6]) or "-")]
    for i, (k, v) in enumerate(lines):
        y = .95 - i * .1
        ax.text(0, y, k, fontsize=9, color=QUIET, transform=ax.transAxes)
        ax.text(.42, y, v, fontsize=9.5, color=INK, weight="bold" if k == "동작" else "normal",
                transform=ax.transAxes)
    ax.text(0, .08, "칸 색 = 에이전트의 추론 · 점선 P / 옅은 W = 실제 세계\nB 바람  S 냄새  G 반짝임 (그 칸에서 받은 지각)",
            fontsize=7.5, color=QUIET, transform=ax.transAxes, va="bottom")


def legend_patches():
    return [Patch(facecolor=C_VISITED, edgecolor=INK, label="방문함"),
            Patch(facecolor=C_SAFE, edgecolor=INK, label="안전(추론)"),
            Patch(facecolor=C_PIT, edgecolor=INK, label="구덩이 확정"),
            Patch(facecolor=C_WUMP, edgecolor=INK, label="웜퍼스 확정"),
            Patch(facecolor=C_UNK, edgecolor=INK, label="모름")]


def _mark_grab(frames):
    grabbed = False
    for f in frames:
        grabbed = grabbed or f["action"] == "Grab"
        f["_grabbed"] = "Grab" if grabbed else ""


def save_animation(world, frames, path, fps=3, title=""):
    """탐험 과정 GIF. 마지막 장면은 조금 더 오래 보여 준다."""
    _mark_grab(frames)
    seq = frames + [frames[-1]] * (fps * 2)
    fig = plt.figure(figsize=(7.6, 4.6), dpi=110)
    gax = fig.add_axes([.02, .1, .55, .78]); iax = fig.add_axes([.6, .12, .38, .76])
    fig.legend(handles=legend_patches(), loc="lower left", ncol=5, fontsize=7.5, frameon=False,
               bbox_to_anchor=(.02, 0))

    def update(i):
        f = seq[i]
        draw_frame(gax, world, f)
        draw_info(iax, f, len(frames))
        fig.suptitle(title, fontsize=11, x=.02, ha="left", y=.97)
    anim = FuncAnimation(fig, update, frames=len(seq), interval=1000 / fps)
    anim.save(path, writer=PillowWriter(fps=fps))
    plt.close(fig)
    return path


def key_frames(frames, k=6):
    """지식이 크게 바뀐 순간을 고른다: 첫 턴, 새 구덩이/웜퍼스 확정, 안전 칸 급증, 사격, 금, 마지막"""
    must, extra = {0, len(frames) - 1}, []
    for i in range(1, len(frames)):
        a, b = frames[i - 1], frames[i]
        if b["action"] in ("Grab", "Shoot") or (b["known_wumpus"] and not a["known_wumpus"]):
            must.add(i)                                  # 사격·금·웜퍼스 확정은 꼭 넣는다
        elif len(b["known_pit"]) > len(a["known_pit"]) or len(b["safe"]) - len(a["safe"]) >= 2:
            extra.append(i)                              # 그다음은 구덩이 확정·안전 칸 급증
    must = sorted(must)[:k]
    rest = [i for i in extra if i not in must]
    while len(must) < k and rest:                        # 남는 자리는 고르게 채운다
        must.append(rest.pop(len(rest) // 2))
    return sorted(must)


def save_step_panels(world, frames, path, title=""):
    _mark_grab(frames)
    idx = key_frames(frames)
    cols = 3; rows = (len(idx) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(3.3 * cols, 3.9 * rows + .6), dpi=150,
                             gridspec_kw=dict(hspace=.35, wspace=.08))
    axes = list(axes.flat) if hasattr(axes, "flat") else [axes]
    for ax, i in zip(axes, idx):
        f = frames[i]
        draw_frame(ax, world, f, compact=True)
        ax.set_title(f"t={f['t']}  [{f['pos'][0]},{f['pos'][1]}] {_percept_words(f['percept'])}\n→ {f['action']}"
                     f"   (안전 {len(f['safe'])}칸)", fontsize=8.5, color=INK)
    for ax in axes[len(idx):]: ax.axis("off")
    fig.legend(handles=legend_patches(), loc="lower center", ncol=5, fontsize=8, frameon=False)
    fig.suptitle(title, fontsize=12, x=.02, ha="left")
    fig.subplots_adjust(left=.02, right=.98, top=.9, bottom=.07)
    fig.savefig(path, bbox_inches="tight"); plt.close(fig)
    return path


# ------------------------------------------------------------------ 실험 대시보드
def _run(world, agent):
    from main import run_episode
    return run_episode(world, agent)


def experiments(n=300):
    """정책·사격·엔진별로 n개 무작위 세계를 돌려 요약값을 반환"""
    configs = [("무작위 에이전트", lambda i: RandomAgent(seed=i)),
               ("safe · 사격 X", lambda i: HybridWumpusAgent(policy="safe", shoot=False)),
               ("safe · 사격 O", lambda i: HybridWumpusAgent(policy="safe")),
               ("risk · 사격 O", lambda i: HybridWumpusAgent(policy="risk"))]
    res = []
    for name, make in configs:
        try:
            make(0)
        except TypeError:                                  # shoot 옵션이 없는 agent.py
            print(f"  (건너뜀: {name} — agent.py에 shoot 옵션 없음)"); continue
        rows = [_run(WumpusWorld.random(seed=i), make(i)) for i in range(n)]
        cnt = lambda *ks: 100 * sum(r["outcome"] in ks for r in rows) / n
        res.append(dict(name=name, win=cnt("win"), climb=cnt("climb"), death=cnt("pit", "wumpus"),
                        timeout=cnt("timeout"), score=st.mean(r["score"] for r in rows)))
        print(f"  {name:12s} 성공 {res[-1]['win']:5.1f}%  사망 {res[-1]['death']:5.1f}%  평균 점수 {res[-1]['score']:7.1f}")
    eng = []
    for name, kw in [("DPLL", dict(method="dpll")), ("TT", dict(method="tt")),
                     ("DPLL\n가지치기 X", dict(method="dpll", prune=False))]:
        rows = [_run(WumpusWorld.random(seed=i), HybridWumpusAgent(**kw)) for i in range(min(n, 200))]
        ms = 1000 * sum(r["ask_time"] for r in rows) / max(1, sum(r["asks"] for r in rows))
        eng.append(dict(name=name, ms=ms))
        print(f"  {name.replace(chr(10), ' '):12s} ASK 1회 {ms:.3f} ms")
    return res, eng


def save_dashboard(res, eng, path, n):
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.9), dpi=150, gridspec_kw=dict(width_ratios=[1.5, 1, 1]))
    # (1) 결과 비율 — 100% 누적 가로 막대
    ax = axes[0]
    names = [r["name"] for r in res][::-1]
    left = [0] * len(names)
    for key, label in [("win", "성공"), ("climb", "빈손 탈출"), ("death", "사망"), ("timeout", "시간 초과")]:
        if not any(r[key] for r in res):
            continue                                     # 0%인 항목은 범례에서 뺀다
        vals = [r[key] for r in res][::-1]
        ax.barh(names, vals, left=left, color=OUTCOME_COLOR[key], label=label, height=.6)
        for i, (l, v) in enumerate(zip(left, vals)):
            if v >= 7:
                ax.text(l + v / 2, i, f"{v:.0f}%", ha="center", va="center", fontsize=8,
                        color="white" if key in ("win", "death") else INK)
        left = [l + v for l, v in zip(left, vals)]
    ax.set_xlim(0, 100); ax.set_xlabel("세계 비율 (%)")
    ax.set_title(f"결과 비율 (무작위 세계 {n}개)", fontsize=10, loc="left")
    ax.legend(ncol=4, fontsize=7.5, frameon=False, loc="upper left", bbox_to_anchor=(0, -.15))
    # (2) 평균 점수
    ax = axes[1]
    sc = [r["score"] for r in res]
    best = max(range(len(sc)), key=lambda i: sc[i])
    ax.bar(range(len(sc)), sc, color=["#2A9D8F" if i == best else "#B8C4CC" for i in range(len(sc))])
    ax.axhline(0, color=INK, lw=.8)
    for i, v in enumerate(sc):
        ax.text(i, v + 15 if v >= 0 else 15, f"{v:.0f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(range(len(sc)), [r["name"].replace(" · ", "\n") for r in res], fontsize=7.5)
    ax.set_title("평균 점수 (높을수록 좋음)", fontsize=10, loc="left")
    # (3) ASK 시간
    ax = axes[2]
    ms = [e["ms"] for e in eng]
    ax.bar(range(len(ms)), ms, color=["#2A9D8F", "#B8C4CC", "#B8C4CC"][:len(ms)])
    for i, v in enumerate(ms):
        ax.text(i, v, f"{v:.3f} ms", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(range(len(ms)), [e["name"] for e in eng], fontsize=8)
    ax.set_title("ASK 1회 평균 시간", fontsize=10, loc="left")
    for a in axes:
        for s in ("top", "right"): a.spines[s].set_visible(False)
    fig.tight_layout(); fig.savefig(path, bbox_inches="tight"); plt.close(fig)
    return path


# ------------------------------------------------------------------ CLI
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--world", help="세계 파일")
    ap.add_argument("--seed", type=int, help="무작위 세계 시드")
    ap.add_argument("--engine", default="dpll", choices=["dpll", "tt"])
    ap.add_argument("--policy", default="safe", choices=["safe", "risk"])
    ap.add_argument("--fps", type=int, default=3)
    ap.add_argument("--experiments", type=int, default=0, help="실험 대시보드용 무작위 세계 수")
    args = ap.parse_args()
    setup_korean_font()
    OUT.mkdir(exist_ok=True)

    if args.experiments:
        res, eng = experiments(args.experiments)
        print("저장:", save_dashboard(res, eng, OUT / "experiments.png", args.experiments))
        return
    if args.world:
        world, name = WumpusWorld.from_file(args.world), Path(args.world).stem
    else:
        seed = args.seed or 0
        world, name = WumpusWorld.random(seed=seed), f"seed{seed}"
    agent = HybridWumpusAgent(method=args.engine, policy=args.policy)
    frames = record_episode(world, agent)
    outcome = {"win": "성공", "climb": "빈손 탈출", "pit": "구덩이 사망", "wumpus": "웜퍼스 사망",
               "timeout": "시간 초과"}[world.outcome]
    title = f"{name} · {args.engine.upper()}/{args.policy} · {outcome} (점수 {world.score}, {world.steps}동작)"
    print("저장:", save_animation(world, frames, OUT / f"anim_{name}.gif", args.fps, title))
    print("저장:", save_step_panels(world, frames, OUT / f"steps_{name}.png", title))


if __name__ == "__main__":
    main()
