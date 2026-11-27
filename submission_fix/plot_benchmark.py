"""
plot_benchmark.py — 에이전트·추론 엔진·정책별 성능 비교 그래프 생성
"""
from __future__ import annotations

import statistics as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from main import run_episode
from visualize import _configure_korean_font
from wumpus_env import WumpusWorld


def collect_metrics(configs, num_worlds=1000, start_seed=0):
    """설정 목록별로 무작위 세계 실험을 수행하고 주요 성능 지표를 집계한다."""
    worlds = [WumpusWorld.random(seed=start_seed + i) for i in range(num_worlds)]
    summary_rows = []

    for cfg in configs:
        name = cfg["label"]
        rows = [run_episode(w, cfg["make_agent"](start_seed + idx)) for idx, w in enumerate(worlds)]

        n = len(rows)
        wins = sum(r["outcome"] == "win" for r in rows)
        solvable_rows = [r for r in rows if r["solvable"]]
        solvable_wins = sum(r["outcome"] == "win" for r in solvable_rows)

        total_asks = sum(r["asks"] for r in rows)
        total_ask_time = sum(r["ask_time"] for r in rows)

        summary_rows.append({
            "label": name,
            "win_rate": 100.0 * wins / n if n else 0.0,
            "solvable_win_rate": 100.0 * solvable_wins / len(solvable_rows) if solvable_rows else 0.0,
            "avg_score": st.mean(r["score"] for r in rows),
            "avg_steps": st.mean(r["steps"] for r in rows),
            "avg_ask_ms": (1000.0 * total_ask_time / total_asks) if total_asks > 0 else 0.0,
            "avg_ep_ms": 1000.0 * st.mean(r["time"] for r in rows),
        })

    return summary_rows


def plot_performance(summary_rows, out_path="benchmark.png"):
    """성능 지표를 2×2 서브플롯 그래프로 저장한다."""
    _configure_korean_font()

    labels = [r["label"] for r in summary_rows]
    win_rates = [r["win_rate"] for r in summary_rows]
    solv_rates = [r["solvable_win_rate"] for r in summary_rows]
    avg_scores = [r["avg_score"] for r in summary_rows]
    avg_steps = [r["avg_steps"] for r in summary_rows]
    avg_ep_ms = [r["avg_ep_ms"] for r in summary_rows]
    avg_ask_ms = [r["avg_ask_ms"] for r in summary_rows]

    colors = ["#2A9D8F", "#457B9D", "#E9C46A", "#E76F51", "#8D99AE"][:len(labels)]

    fig, axes = plt.subplots(2, 2, figsize=(12, 8.2), dpi=150)
    fig.suptitle("Hybrid Wumpus Agent 성능 비교", fontsize=14, weight="bold", y=0.98)

    # 1) 승률 (%) — 전체 승률 vs 해결 가능 세계 기준 승률
    ax = axes[0, 0]
    x = range(len(labels))
    w = 0.36
    b1 = ax.bar([i - w / 2 for i in x], win_rates, width=w, color="#2A9D8F", label="전체 승률 (%)")
    b2 = ax.bar([i + w / 2 for i in x], solv_rates, width=w, color="#264653", label="해결 가능 승률 (%)")
    ax.set_title("성공률 비교")
    ax.set_ylabel("성공률 (%)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=15, ha="right", fontsize=9)
    ax.set_ylim(0, 110)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.legend(fontsize=8)
    for bars in (b1, b2):
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 1.5, f"{h:.1f}%",
                    ha="center", va="bottom", fontsize=7.5)

    # 2) 평균 점수
    ax = axes[0, 1]
    bars = ax.bar(labels, avg_scores, color=colors)
    ax.axhline(0, color="#555555", lw=0.9)
    ax.set_title("에피소드 평균 점수")
    ax.set_ylabel("평균 점수")
    ax.tick_params(axis="x", rotation=15, labelsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    for bar in bars:
        h = bar.get_height()
        va = "bottom" if h >= 0 else "top"
        offset = 8 if h >= 0 else -12
        ax.text(bar.get_x() + bar.get_width() / 2, h + offset, f"{h:.1f}",
                ha="center", va=va, fontsize=8)

    # 3) 평균 동작 수
    ax = axes[1, 0]
    bars = ax.bar(labels, avg_steps, color=colors)
    ax.set_title("에피소드 평균 동작 수 (Steps)")
    ax.set_ylabel("평균 동작 수")
    ax.tick_params(axis="x", rotation=15, labelsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + 0.5, f"{h:.1f}",
                ha="center", va="bottom", fontsize=8)

    # 4) 추론/실행 시간 (ms)
    ax = axes[1, 1]
    x = range(len(labels))
    w = 0.36
    b1 = ax.bar([i - w / 2 for i in x], avg_ep_ms, width=w, color="#457B9D", label="에피소드 평균 (ms)")
    b2 = ax.bar([i + w / 2 for i in x], avg_ask_ms, width=w, color="#E76F51", label="ASK 1회 평균 (ms)")
    ax.set_title("실행 및 추론 시간 비교")
    ax.set_ylabel("시간 (ms)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=15, ha="right", fontsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.legend(fontsize=8)
    for bars in (b1, b2):
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.5, f"{h:.2f}",
                    ha="center", va="bottom", fontsize=7.5)

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return out_path


if __name__ == "__main__":
    from agent import HybridWumpusAgent, RandomAgent

    configs = [
        {"label": "DPLL + Safe", "make_agent": lambda s: HybridWumpusAgent(method="dpll", policy="safe", prune=True)},
        {"label": "DPLL + Risk", "make_agent": lambda s: HybridWumpusAgent(method="dpll", policy="risk", prune=True)},
        {"label": "DPLL (No Prune)", "make_agent": lambda s: HybridWumpusAgent(method="dpll", policy="safe", prune=False)},
        {"label": "Random", "make_agent": lambda s: RandomAgent(seed=s)},
    ]

    # TT 엔진은 세계 수가 많으면 느릴 수 있으므로 필요 시 num_worlds를 줄여 추가하세요.
    summary = collect_metrics(configs, num_worlds=1000, start_seed=0)
    out = plot_performance(summary, "benchmark.png")
    print("저장 완료:", out)