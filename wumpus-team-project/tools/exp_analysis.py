"""
exp_analysis.py — 보고서 '분석 및 비교'용 심화 실험 2가지

  python tools/exp_analysis.py symbols      # ① 기호 수에 따른 TT vs DPLL 시간  → results/exp_symbols.png
  python tools/exp_analysis.py failures     # ② 빈손 탈출 원인 분류 (1000개)     → results/exp_failures.png
  python tools/exp_analysis.py all

① 기호 수 실험
   가지치기(관련 절 추출)를 끈 에이전트가 실제로 던진 ASK 질의(KB 절 집합 + 질의)를 모아서,
   기호 수 n별로 TT-ENTAILS와 DPLL의 1회 시간을 잰다. 같은 질의를 두 엔진에 넣으므로 공정한 비교이고,
   두 엔진의 답이 같은지도 확인한다. TT는 n ≤ --tt-max(기본 18)까지만 직접 재고, 그 이상은 2^n 추세로 추정한다.
   DPLL은 휴리스틱(순수 기호·단위 절) 켜기/끄기도 비교한다.

② 실패 분석
   safe 정책(사격 O)이 금을 못 가져온 세계를 원인별로 분류하고,
   같은 세계를 risk 정책으로 돌렸을 때 결과(성공/사망/빈손)를 함께 본다.
"""
from __future__ import annotations
import argparse
import statistics as st
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import matplotlib                                              # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                # noqa: E402

from wumpus_env import WumpusWorld, gold_reachable             # noqa: E402
from agent import HybridWumpusAgent                            # noqa: E402
from main import run_episode                                   # noqa: E402
from logic import tt_entails, dpll_entails, var                # noqa: E402
from viz_plus import setup_korean_font                         # noqa: E402

OUT = ROOT / "results"
INK, QUIET, ACCENT, GREY = "#1F2147", "#6B7080", "#2A9D8F", "#B8C4CC"


# ====================================================================== ① 기호 수
def collect_queries(worlds=60, per_n=5):
    """가지치기 없이 에이전트를 돌리며 ASK 질의를 기호 수별로 per_n개씩 모은다."""
    samples = defaultdict(list)
    for i in range(worlds):
        a = HybridWumpusAgent(prune=False)
        orig = a.kb.ask

        def ask(q, kb=a.kb, orig=orig):
            cl = frozenset(kb.clauses)
            n = len({var(l) for c in cl for l in c} | q.symbols())
            if len(samples[n]) < per_n:
                samples[n].append((cl, q))
            return orig(q)
        a.kb.ask = ask
        run_episode(WumpusWorld.random(seed=i), a)
    return samples


def timed(f, *args, **kw):
    t = time.perf_counter(); r = f(*args, **kw)
    return r, time.perf_counter() - t


def exp_symbols(tt_max=18, worlds=60, per_n=5):
    samples = collect_queries(worlds, per_n)
    rows = []
    for n in sorted(samples):
        td, tdn, calls_h, calls_n, tt = [], [], [], [], []
        agree = True
        for cl, q in samples[n]:
            s1 = defaultdict(float); r1, t1 = timed(dpll_entails, cl, q, s1)
            s2 = defaultdict(float); _, t2 = timed(dpll_entails, cl, q, s2, False, False)
            td.append(t1); tdn.append(t2); calls_h.append(s1["dpll_calls"]); calls_n.append(s2["dpll_calls"])
            if n <= tt_max:
                r3, t3 = timed(tt_entails, cl, q)
                tt.append(t3); agree &= (r1 == r3)
        rows.append(dict(n=n, dpll=st.median(td) * 1000, dpll_noh=st.median(tdn) * 1000,
                         calls=st.mean(calls_h), calls_noh=st.mean(calls_n),
                         tt=st.median(tt) * 1000 if tt else None, agree=agree))
    # TT 추세: 측정한 구간의 log2(시간) 직선 맞춤 → 큰 n 추정
    import math
    pts = [(r["n"], math.log2(r["tt"])) for r in rows if r["tt"] and r["n"] >= 10]
    mx, my = st.mean(p[0] for p in pts), st.mean(p[1] for p in pts)
    slope = sum((x - mx) * (y - my) for x, y in pts) / sum((x - mx) ** 2 for x, _ in pts)
    anchor = max((r for r in rows if r["tt"]), key=lambda r: r["n"])   # 직접 잰 가장 큰 n
    est = lambda n: anchor["tt"] * 2 ** (n - anchor["n"])               # 모델 수 2^n 에 비례 (이론)
    for r in rows:
        r["tt_est"] = est(r["n"])

    print("\n### ① 기호 수에 따른 ASK 1회 시간 (같은 질의, 중앙값)\n")
    print("| 기호 수 | TT (ms) | DPLL 휴리스틱 O (ms) | DPLL 휴리스틱 X (ms) | DPLL 호출 수 O / X | 답 일치 |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        tt = f"{r['tt']:.2f}" if r["tt"] is not None else f"(추정 {fmt_ms(r['tt_est'])})"
        print(f"| {r['n']} | {tt} | {r['dpll']:.3f} | {r['dpll_noh']:.3f} | {r['calls']:.0f} / {r['calls_noh']:.0f} | "
              f"{('O' if r['agree'] else 'X') if r['tt'] is not None else '-'} |")
    print(f"\nTT 측정 추세: 기호 1개 늘 때마다 시간 ×{2 ** slope:.2f} (이론 ×2)  →  "
          f"n={anchor['n']} 실측 {anchor['tt']:.0f}ms × 2^(32−{anchor['n']}) = 기호 32개면 1회 약 {fmt_ms(est(32))}")
    ratio_c = st.mean(r["calls"] / r["calls_noh"] for r in rows)
    ratio_t = st.mean(r["dpll"] / r["dpll_noh"] for r in rows)
    print(f"DPLL 휴리스틱: 호출 수 ×{ratio_c:.2f} (줄어듦), 시간 ×{ratio_t:.2f} — 호출마다 모든 절을 훑어 순수 기호·단위 절을 찾는 비용")
    return rows, slope


def fmt_ms(ms):
    s = ms / 1000
    if s < 1: return f"{ms:.0f} ms"
    if s < 120: return f"{s:.0f}초"
    if s < 7200: return f"{s / 60:.0f}분"
    if s < 172800: return f"{s / 3600:.1f}시간"
    return f"{s / 86400:.0f}일"


def plot_symbols(rows, slope, path, prune_max=8):
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(12.5, 4.4), dpi=150, gridspec_kw=dict(width_ratios=[1.6, 1]))
    ns = [r["n"] for r in rows]
    m = [r for r in rows if r["tt"] is not None]
    ax.axvspan(min(ns) - .5, prune_max + .5, color="#EEF5F3", zorder=0)
    ax.text(prune_max + .3, 3e5, "가지치기 켜면\n실제 질의는 여기\n(최대 8개)", ha="right", va="top", fontsize=8, color=ACCENT)
    ax.plot([r["n"] for r in m], [r["tt"] for r in m], "o-", color="#D1495B", lw=2, ms=4, label="TT-ENTAILS (측정)")
    big = [r for r in rows if r["n"] >= m[-1]["n"]]
    ax.plot([r["n"] for r in big], [r["tt_est"] for r in big], "--", color="#D1495B", lw=1.5, alpha=.7,
            label=f"TT 추정 (실측 기울기 ×{2 ** slope:.2f} ≈ 이론 ×2)")
    ax.plot(ns, [r["dpll"] for r in rows], "o-", color=ACCENT, lw=2, ms=4, label="DPLL (측정)")
    ax.set_yscale("log"); ax.set_xlabel("질의에 쓰인 기호 수 n"); ax.set_ylabel("ASK 1회 시간 (로그 축)")
    ticks = [(.1, "0.1ms"), (1, "1ms"), (10, "10ms"), (100, "0.1초"), (1000, "1초"), (6e4, "1분"), (3.6e6, "1시간")]
    ax.set_yticks([t for t, _ in ticks], [l for _, l in ticks]); ax.minorticks_off()
    last = rows[-1]
    ax.annotate(f"TT ≈ 1회 {fmt_ms(last['tt_est'])}", (last["n"], last["tt_est"]), xytext=(-30, -56),
                textcoords="offset points", ha="right", va="top", fontsize=9, color="#D1495B")
    ax.annotate(f"DPLL {last['dpll']:.2f} ms", (last["n"], last["dpll"]), xytext=(-8, 8),
                textcoords="offset points", ha="right", fontsize=9, color=ACCENT)
    ax.set_title("기호가 늘면 TT는 지수적으로 폭발하고, DPLL은 1ms 안팎에 머문다", fontsize=10.5, loc="left")
    ax.legend(fontsize=8, frameon=False, loc="upper left")
    # 휴리스틱 효과
    ax2.plot(ns, [r["calls_noh"] for r in rows], "o-", color=GREY, lw=2, ms=4, label="휴리스틱 X (조기 종료+분기)")
    ax2.plot(ns, [r["calls"] for r in rows], "o-", color=ACCENT, lw=2, ms=4, label="휴리스틱 O (순수 기호+단위 절)")
    ratio_c = st.mean(r["calls"] / r["calls_noh"] for r in rows)
    ratio_t = st.mean(r["dpll"] / r["dpll_noh"] for r in rows)
    ax2.set_xlabel("기호 수 n"); ax2.set_ylabel("DPLL 재귀 호출 수"); ax2.set_ylim(bottom=0)
    ax2.set_title(f"휴리스틱은 호출 수를 {100 * (1 - ratio_c):.0f}% 줄이지만, 시간은 {100 * (ratio_t - 1):.0f}% 늘린다",
                  fontsize=10.5, loc="left")
    ax2.text(.38, .05, "호출마다 모든 절을 훑어 순수 기호·단위 절을\n찾는 비용이 줄어든 호출 수보다 크다 (이 크기에서)",
             transform=ax2.transAxes, fontsize=8, color=QUIET)
    ax2.legend(fontsize=8, frameon=False)
    for a in (ax, ax2):
        for s in ("top", "right"): a.spines[s].set_visible(False)
        a.grid(axis="y", color="#E5E7EB", lw=.6)
    fig.tight_layout(); fig.savefig(path, bbox_inches="tight"); plt.close(fig)
    return path


# ====================================================================== ② 실패 분석
def classify(world, agent, outcome):
    if outcome == "win":
        return "성공"
    if outcome in ("pit", "wumpus", "timeout"):
        return "사망/시간 초과"
    if world.gold in world.pits:
        return "금이 구덩이 안"
    if not gold_reachable(world):
        return "금이 구덩이에 둘러싸임"
    if agent.visited == {(1, 1)}:
        p = agent.log[0][2] if agent.log else ""
        return "[1,1]에서 바로 막힘 (Breeze)" if "Breeze" in p else "[1,1]에서 바로 막힘 (Stench)"
    frontier = [c for c in agent.cells if c not in agent.visited and c not in agent.known_pit
                and any(n in agent.visited for n in agent.neighbors(c))]
    if any(c in agent.not_pit for c in frontier):
        return "탐험 중 막힘 (웜퍼스 가능성)"
    return "탐험 중 막힘 (구덩이 가능성)"


ORDER = ["성공", "금이 구덩이 안", "금이 구덩이에 둘러싸임", "[1,1]에서 바로 막힘 (Breeze)",
         "[1,1]에서 바로 막힘 (Stench)", "탐험 중 막힘 (구덩이 가능성)", "탐험 중 막힘 (웜퍼스 가능성)", "사망/시간 초과"]


def exp_failures(n=1000):
    rows = []
    for i in range(n):
        w = WumpusWorld.random(seed=i); a = HybridWumpusAgent(policy="safe")
        r = run_episode(w, a)
        cat = classify(w, a, r["outcome"])
        risk = None
        if cat not in ("성공", "금이 구덩이 안", "금이 구덩이에 둘러싸임"):
            risk = run_episode(WumpusWorld.random(seed=i), HybridWumpusAgent(policy="risk"))["outcome"]
        rows.append(dict(seed=i, cat=cat, risk=risk, steps=r["steps"], visited=r["visited"]))
    cnt = Counter(r["cat"] for r in rows)
    solv = sum(1 for r in rows if r["cat"] not in ("금이 구덩이 안", "금이 구덩이에 둘러싸임"))
    print(f"\n### ② safe 정책(사격 O) 결과 분류 (무작위 세계 {n}개)\n")
    print("| 분류 | 세계 수 | 비율 (%) | 평균 방문 칸 | 같은 세계를 risk로: 성공 / 사망 / 빈손 |")
    print("|---|---|---|---|---|")
    for c in ORDER:
        if not cnt[c]: continue
        sub = [r for r in rows if r["cat"] == c]
        rk = Counter(r["risk"] for r in sub if r["risk"])
        rk_s = f"{rk['win']} / {rk['pit'] + rk['wumpus']} / {rk['climb']}" if rk else "-"
        print(f"| {c} | {cnt[c]} | {100 * cnt[c] / n:.1f} | {st.mean(r['visited'] for r in sub):.1f} | {rk_s} |")
    fail = [r for r in rows if r["risk"]]
    rk = Counter(r["risk"] for r in fail)
    print(f"\n해결 가능 세계 {solv}개 중 성공 {cnt['성공']}개 ({100 * cnt['성공'] / solv:.1f}%)")
    print(f"safe가 못 푼 해결 가능 세계 {len(fail)}개를 risk로 돌리면: 성공 {rk['win']}, 사망 {rk['pit'] + rk['wumpus']}, 빈손 {rk['climb']}")
    gain = 1000 * rk["win"] - 1000 * (rk["pit"] + rk["wumpus"])
    print(f"→ 이 세계들에서 모험의 점수 득실 ≈ +1000×{rk['win']} − 1000×{rk['pit'] + rk['wumpus']} = {gain:+d}점 (동작 비용 제외)")
    return rows, cnt, n


def plot_failures(rows, cnt, n, path):
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(12.5, 4.3), dpi=150, gridspec_kw=dict(width_ratios=[1.5, 1]))
    cats = [c for c in ORDER if cnt[c]][::-1]
    col = {"성공": ACCENT, "금이 구덩이 안": GREY, "금이 구덩이에 둘러싸임": GREY}
    colors = [col.get(c, "#E9A23B") for c in cats]
    ax.barh(cats, [cnt[c] for c in cats], color=colors, height=.62)
    for i, c in enumerate(cats):
        ax.text(cnt[c] + 6, i, f"{cnt[c]}  ({100 * cnt[c] / n:.1f}%)", va="center", fontsize=8.5, color=INK)
    ax.set_xlim(0, max(cnt.values()) * 1.28)
    ax.set_xlabel("세계 수")
    unsolv = cnt["금이 구덩이 안"] + cnt["금이 구덩이에 둘러싸임"]
    ax.set_title(f"빈손 탈출 = 불가능한 세계 {unsolv}개 + 증명할 수 없어 멈춘 세계 {n - unsolv - cnt['성공']}개",
                 fontsize=10.5, loc="left")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=ACCENT, label="성공"), Patch(color=GREY, label="원래 불가능 (금에 못 감)"),
                       Patch(color="#E9A23B", label="가능했지만 안전 증명 불가")],
              fontsize=8, frameon=False, loc="lower right")
    # risk로 돌렸다면
    groups = [c for c in ORDER if cnt[c] and c not in ("성공", "금이 구덩이 안", "금이 구덩이에 둘러싸임", "사망/시간 초과")]
    win = [sum(1 for r in rows if r["cat"] == c and r["risk"] == "win") for c in groups]
    die = [sum(1 for r in rows if r["cat"] == c and r["risk"] in ("pit", "wumpus")) for c in groups]
    clb = [sum(1 for r in rows if r["cat"] == c and r["risk"] == "climb") for c in groups]
    labels = [g.replace(" (", "\n(") for g in groups][::-1]
    win, die, clb = win[::-1], die[::-1], clb[::-1]
    ax2.barh(labels, win, color=ACCENT, height=.6, label="성공")
    ax2.barh(labels, die, left=win, color="#D1495B", height=.6, label="사망")
    ax2.barh(labels, clb, left=[a + b for a, b in zip(win, die)], color=GREY, height=.6, label="빈손")
    for i, (w_, d_) in enumerate(zip(win, die)):
        if w_ >= 8: ax2.text(w_ / 2, i, str(w_), ha="center", va="center", fontsize=8, color="white")
        if d_ >= 8: ax2.text(w_ + d_ / 2, i, str(d_), ha="center", va="center", fontsize=8, color="white")
    ax2.tick_params(axis="y", labelsize=8)
    ax2.set_xlabel("세계 수")
    tw, td = sum(win), sum(die)
    ax2.set_title(f"같은 세계를 risk(모험)로 돌리면 {tw}개 성공, {td}개 사망", fontsize=10.5, loc="left")
    ax2.legend(fontsize=8, frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(.5, -.16))
    for a in (ax, ax2):
        for s in ("top", "right"): a.spines[s].set_visible(False)
    fig.tight_layout(); fig.savefig(path, bbox_inches="tight"); plt.close(fig)
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["symbols", "failures", "all"])
    ap.add_argument("--n", type=int, default=1000, help="실패 분석 세계 수")
    ap.add_argument("--tt-max", type=int, default=18, help="TT를 직접 잴 최대 기호 수")
    args = ap.parse_args()
    setup_korean_font()
    OUT.mkdir(exist_ok=True)
    if args.what in ("symbols", "all"):
        rows, slope = exp_symbols(args.tt_max)
        print("저장:", plot_symbols(rows, slope, OUT / "exp_symbols.png"))
    if args.what in ("failures", "all"):
        rows, cnt, n = exp_failures(args.n)
        print("저장:", plot_failures(rows, cnt, n, OUT / "exp_failures.png"))
