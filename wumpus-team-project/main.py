"""
main.py — 웜퍼스 세계 논리 에이전트 실행

  단일 세계 실행 + 시각화
    python main.py --world worlds/world_fig7_2.txt --engine dpll --verbose
  무작위 세계 N개 일괄 실험
    python main.py --random 1000 --engine dpll --policy safe
    python main.py --random 1000 --agent random
"""
from __future__ import annotations
import argparse
import statistics as st
import time

from wumpus_env import WumpusWorld, gold_reachable
from agent import HybridWumpusAgent, RandomAgent


def run_episode(world, agent, verbose=False):
    percept = world.reset()
    t0 = time.perf_counter()
    while not world.done:
        action = agent(percept)
        percept, reward, done = world.step(action)
        if verbose:
            print(world.render(), "\n")
    elapsed = time.perf_counter() - t0
    kb = getattr(agent, "kb", None)
    return dict(outcome=world.outcome, score=world.score, steps=world.steps,
                time=elapsed, asks=int(kb.stats["asks"]) if kb else 0,
                ask_time=kb.stats["ask_time"] if kb else 0.0,
                kb_size=len(kb) if kb else 0,
                symbols_max=int(kb.stats["symbols_max"]) if kb else 0,
                models=int(kb.stats["models"]) if kb else 0,
                visited=len(getattr(agent, "visited", ())),
                shot=not world.has_arrow, solvable=gold_reachable(world))


def make_agent(args, seed=None):
    if args.agent == "random":
        return RandomAgent(seed=seed)
    return HybridWumpusAgent(method=args.engine, policy=args.policy, prune=not args.no_prune,
                             verbose=args.verbose)


def summarize(rows, label=""):
    n = len(rows)
    cnt = lambda k: sum(r["outcome"] == k for r in rows)
    solv = [r for r in rows if r["solvable"]]
    print(f"===== {label} (세계 {n}개) =====")
    print(f"성공(금 회수 후 탈출) {cnt('win'):4d}  ({100 * cnt('win') / n:5.1f}%)")
    print(f"빈손 탈출           {cnt('climb'):4d}  ({100 * cnt('climb') / n:5.1f}%)")
    print(f"사망(구덩이/웜퍼스)  {cnt('pit') + cnt('wumpus'):4d}  ({100 * (cnt('pit') + cnt('wumpus')) / n:5.1f}%)")
    print(f"시간 초과            {cnt('timeout'):4d}")
    print(f"평균 점수            {st.mean(r['score'] for r in rows):8.1f}")
    print(f"평균 동작 수         {st.mean(r['steps'] for r in rows):8.1f}")
    if solv:
        print(f"해결 가능 세계 {len(solv)}개 중 성공률 {100 * sum(r['outcome'] == 'win' for r in solv) / len(solv):5.1f}%")
    if rows[0]["asks"]:
        print(f"평균 ASK 횟수        {st.mean(r['asks'] for r in rows):8.1f}")
        print(f"ASK 1회 평균 시간    {1000 * sum(r['ask_time'] for r in rows) / sum(r['asks'] for r in rows):8.3f} ms")
    print(f"에피소드 평균 시간   {1000 * st.mean(r['time'] for r in rows):8.2f} ms")


def main():
    ap = argparse.ArgumentParser(description="Wumpus World logical agent")
    ap.add_argument("--world", help="세계 파일 (예: worlds/world_fig7_2.txt)")
    ap.add_argument("--random", type=int, default=0, help="무작위 세계 개수")
    ap.add_argument("--seed", type=int, default=0, help="무작위 세계 시작 시드")
    ap.add_argument("--agent", choices=["hybrid", "random"], default="hybrid")
    ap.add_argument("--engine", choices=["dpll", "tt"], default="dpll", help="추론 엔진")
    ap.add_argument("--policy", choices=["safe", "risk"], default="safe", help="안전 칸이 없을 때 정책")
    ap.add_argument("--no-prune", action="store_true", help="관련 절 추출(가지치기) 끄기")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--out", default="result_path.png", help="시각화 이미지 파일")
    args = ap.parse_args()

    if args.random:
        rows = []
        for i in range(args.random):
            w = WumpusWorld.random(seed=args.seed + i)
            rows.append(run_episode(w, make_agent(args, seed=args.seed + i)))
        summarize(rows, args.agent if args.agent == "random" else f"{args.agent}/{args.engine}/{args.policy}")
        return

    world = WumpusWorld.from_file(args.world) if args.world else WumpusWorld.random(seed=args.seed)
    print("세계 (윗줄 = y4)\n" + world.to_text() + "\n")
    agent = make_agent(args)
    r = run_episode(world, agent, verbose=False)
    msg = {"win": "성공! 금을 가지고 탈출했습니다.", "climb": "금 없이 안전하게 탈출했습니다.",
           "pit": "구덩이에 빠졌습니다.", "wumpus": "웜퍼스에게 잡혔습니다.", "timeout": "시간 초과"}[r["outcome"]]
    print(f"결과: {msg}")
    print(f"점수 {r['score']}, 동작 수 {r['steps']}, 방문 칸 {r['visited']}, "
          f"ASK {r['asks']}회, KB 절 {r['kb_size']}개, 실행 시간 {1000 * r['time']:.1f} ms")
    if hasattr(agent, "visited"):
        from visualize import save_episode
        save_episode(world, agent, args.out, f"{args.engine.upper()} · {msg}  (점수 {r['score']})")
        print("시각화 저장:", args.out)


if __name__ == "__main__":
    main()
