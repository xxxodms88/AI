"""
exp_search_agent.py — 탐색·에이전트 파트(TODO 4·6·7) 실험.  보고서 '알고리즘 구현' · '성능 비교' 슬라이드용.

  python tools/exp_search_agent.py            # 무작위 1000개 (seed 0~999)
  python tools/exp_search_agent.py --n 200    # 빠르게
  python tools/exp_search_agent.py --plot     # results/exp_search_agent.png 그래프도 저장

실험 1. 사격(TODO 7-③) 켜기/끄기 × 정책(safe/risk)  → 성공률, 사망률, 평균 점수, 평균 동작 수
실험 2. A*(맨해튼) vs 균일 비용 탐색(h=0)          → 같은 경로 길이, 확장 노드 수 비교
※ logic.py(TODO 1~3)가 완성되어 있어야 실험 1이 돌아갑니다.
"""
from __future__ import annotations
import argparse
import random
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from wumpus_env import WumpusWorld          # noqa: E402
from agent import HybridWumpusAgent          # noqa: E402
from main import run_episode                 # noqa: E402
import planner                               # noqa: E402


def exp_shoot(n):
    rows = []
    for policy in ("safe", "risk"):
        for shoot in (False, True):
            res = []
            exp = 0
            for i in range(n):
                a = HybridWumpusAgent(policy=policy, shoot=shoot)
                res.append(run_episode(WumpusWorld.random(seed=i), a))
                exp += a.search_stats["expanded"]
            cnt = lambda k: sum(r["outcome"] == k for r in res)
            solv = [r for r in res if r["solvable"]]
            rows.append(dict(
                policy=policy, shoot="O" if shoot else "X",
                win=100 * cnt("win") / n,
                death=100 * (cnt("pit") + cnt("wumpus")) / n,
                win_solv=100 * sum(r["outcome"] == "win" for r in solv) / max(1, len(solv)),
                score=st.mean(r["score"] for r in res),
                steps=st.mean(r["steps"] for r in res),
                shots=sum(r["shot"] for r in res),
                expanded=exp / n))
    print(f"\n### 실험 1. 사격 × 정책 (무작위 세계 {n}개)\n")
    print("| 정책 | 사격 | 성공률(%) | 해결 가능 세계 중 성공률(%) | 사망률(%) | 평균 점수 | 평균 동작 수 | 화살 사용 | A* 확장 노드/에피소드 |")
    print("|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['policy']} | {r['shoot']} | {r['win']:.1f} | {r['win_solv']:.1f} | {r['death']:.1f} | "
              f"{r['score']:.1f} | {r['steps']:.1f} | {r['shots']} | {r['expanded']:.1f} |")
    return rows


def exp_astar(n):
    rng = random.Random(0)
    cells = [(x, y) for x in range(1, 5) for y in range(1, 5)]
    ea = eu = solved = 0
    for _ in range(n):
        allowed = {c for c in cells if rng.random() < 0.7} | {(1, 1)}
        goals = set(rng.sample(cells, rng.randint(1, 3)))
        d = rng.randrange(4)
        sa, su = {"expanded": 0}, {"expanded": 0}
        pa = planner.plan_route((1, 1), d, goals, allowed, sa)
        pu = planner.astar((1, 1, d), lambda s: (s[0], s[1]) in goals, lambda s: 0, allowed | goals, su)
        assert (pa is None) == (pu is None) and (pa is None or len(pa) == len(pu))
        ea += sa["expanded"]; eu += su["expanded"]; solved += pa is not None
    print(f"\n### 실험 2. A* vs 균일 비용 탐색 (무작위 경로 문제 {n}개, 해 있음 {solved}개)\n")
    print("| 알고리즘 | 평균 확장 노드 수 | 경로 길이 |")
    print("|---|---|---|")
    print(f"| 균일 비용 (h=0) | {eu / n:.2f} | 최적 |")
    print(f"| A* (맨해튼) | {ea / n:.2f} | 최적 (모든 문제에서 길이 동일) |")
    print(f"\n→ A*가 확장 노드를 {100 * (1 - ea / eu):.1f}% 줄임")
    return ea / n, eu / n


def plot(rows, astar_res, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), dpi=150)
    labels = [f"{r['policy']}\nshoot {r['shoot']}" for r in rows]
    colors = ["#9AA0B2", "#2A9D8F", "#E9C46A", "#E76F51"]
    axes[0].bar(labels, [r["win"] for r in rows], color=colors); axes[0].set_title("Win rate (%)")
    axes[1].bar(labels, [r["score"] for r in rows], color=colors); axes[1].set_title("Mean score")
    axes[1].axhline(0, color="black", lw=0.8)
    axes[2].bar(["UCS (h=0)", "A* (Manhattan)"], [astar_res[1], astar_res[0]], color=["#9AA0B2", "#2A9D8F"])
    axes[2].set_title("Nodes expanded / query")
    for ax in axes:
        for p in ax.patches:
            ax.annotate(f"{p.get_height():.1f}", (p.get_x() + p.get_width() / 2, p.get_height()),
                        ha="center", va="bottom", fontsize=8)
    fig.tight_layout()
    path.parent.mkdir(exist_ok=True)
    fig.savefig(path)
    print(f"\n그래프 저장: {path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--plot", action="store_true")
    args = ap.parse_args()
    rows = exp_shoot(args.n)
    a = exp_astar(args.n)
    if args.plot:
        plot(rows, a, ROOT / "results" / "exp_search_agent.png")
