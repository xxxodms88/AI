"""
planner.py — 안전한 칸만 지나는 경로 계획 (A* 탐색)

상태 = (x, y, dir).  동작 Forward / TurnLeft / TurnRight 의 비용은 모두 1.
휴리스틱 h = 가장 가까운 목표 칸까지의 맨해튼 거리 (허용적 → A*는 최적)
"""
from __future__ import annotations
import heapq  # noqa: F401  (A* 구현에 사용)
from itertools import count  # noqa: F401

DIRS = {0: (1, 0), 1: (0, 1), 2: (-1, 0), 3: (0, -1)}


def successors(state, allowed):
    x, y, d = state
    yield "TurnLeft", (x, y, (d + 1) % 4)
    yield "TurnRight", (x, y, (d - 1) % 4)
    dx, dy = DIRS[d]
    nxt = (x + dx, y + dy)
    if nxt in allowed:
        yield "Forward", (nxt[0], nxt[1], d)


def astar(start, goal_test, h, allowed, stats=None):
    """[TODO 4] A* 탐색
    start     : 시작 상태 (x, y, dir)
    goal_test : 상태 → bool
    h         : 상태 → 휴리스틱 값 (허용적이어야 함)
    allowed   : 지나가도 되는 칸 (x, y)의 집합 → successors(state, allowed) 사용
    반환      : 동작 리스트 ['TurnLeft', 'Forward', ...]  (경로 없으면 None)
    stats     : None이 아니면 stats["expanded"] += 확장한 노드 수

    구현 포인트
      · 우선순위 큐(heapq)에 (f = g + h, 동점 처리용 카운터, g, state) 저장
      · parent[state] = (이전 상태, 동작) 으로 경로를 기록해 두었다가 역추적
      · 같은 상태를 더 작은 g로 다시 만나면 갱신 (모든 동작 비용 = 1)
    """
    raise NotImplementedError("TODO 4: astar")


def manhattan_to(goals):
    goals = list(goals)
    return lambda s: min(abs(s[0] - gx) + abs(s[1] - gy) for gx, gy in goals)


def plan_route(pos, d, goals, allowed, stats=None):
    """PLAN-ROUTE: 현재 (pos, d)에서 goals 중 한 칸까지, allowed 칸만 지나는 최단 동작열."""
    goals = set(goals)
    if not goals: return None
    allowed = set(allowed) | goals | {pos}
    return astar((pos[0], pos[1], d), lambda s: (s[0], s[1]) in goals,
                 manhattan_to(goals), allowed, stats)


def plan_shot(pos, d, target, allowed, size, stats=None):
    """PLAN-SHOT: target 칸과 같은 행/열에 있는 allowed 칸으로 가서 target을 바라보는 동작열 + Shoot."""
    tx, ty = target
    goal_states = set()
    for (x, y) in allowed:
        if x == tx and y != ty: goal_states.add((x, y, 1 if ty > y else 3))
        if y == ty and x != tx: goal_states.add((x, y, 0 if tx > x else 2))
    if not goal_states: return None
    cells = {(x, y) for x, y, _ in goal_states}
    plan = astar((pos[0], pos[1], d), lambda s: s in goal_states,
                 manhattan_to(cells), set(allowed) | {pos}, stats)
    return None if plan is None else plan + ["Shoot"]
