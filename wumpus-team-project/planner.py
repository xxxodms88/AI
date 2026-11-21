"""
planner.py — 안전한 칸만 지나는 경로 계획 (A* 탐색)

상태 = (x, y, dir).  동작 Forward / TurnLeft / TurnRight 의 비용은 모두 1.
휴리스틱 h = 가장 가까운 목표 칸까지의 맨해튼 거리 (허용적 → A*는 최적)
"""
from __future__ import annotations
import heapq
from itertools import count

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

    구현 메모 (TODO 4, 탐색·에이전트 담당)
      · frontier : 힙 원소 = (f, tie, g, state).  tie는 삽입 순서 카운터라서
                   f가 같을 때 상태(튜플)끼리 비교하지 않게 하고, 결과를 결정적으로 만든다.
      · best_g   : 지금까지 찾은 상태별 최소 g.  힙에서 꺼낸 원소의 g가 best_g보다 크면
                   이미 더 싼 경로로 처리된 '낡은 원소'이므로 버린다 (lazy deletion).
      · closed   : 확장을 마친 상태.  h가 일관적(consistent)이므로 한 번 닫힌 상태는
                   다시 열 필요가 없다.  (맨해튼 거리는 Forward 1회에 최대 1 줄고,
                   회전은 위치를 바꾸지 않으므로 h(s) ≤ 1 + h(s') 를 만족 → 일관적)
      · goal_test는 '꺼낼 때' 검사한다.  넣을 때 검사하면 최적성이 깨질 수 있다.
    """
    tie = count()
    g0 = 0
    frontier = [(g0 + h(start), next(tie), g0, start)]
    best_g = {start: g0}
    parent = {start: None}                  # state → (이전 state, 동작)  /  시작 상태는 None
    closed = set()

    while frontier:
        f, _, g, state = heapq.heappop(frontier)
        if g > best_g.get(state, float("inf")) or state in closed:
            continue                        # 낡은 원소 (더 짧은 경로가 이미 처리됨)
        if goal_test(state):
            return _reconstruct(parent, state)
        closed.add(state)
        if stats is not None:
            stats["expanded"] = stats.get("expanded", 0) + 1
        for action, nxt in successors(state, allowed):
            ng = g + 1                      # 모든 동작 비용 = 1
            if nxt in closed or ng >= best_g.get(nxt, float("inf")):
                continue
            best_g[nxt] = ng
            parent[nxt] = (state, action)
            heapq.heappush(frontier, (ng + h(nxt), next(tie), ng, nxt))
    return None                             # 목표에 도달할 수 없음


def _reconstruct(parent, state):
    """parent 사슬을 목표에서 시작까지 거꾸로 따라가 동작 리스트를 만든다."""
    actions = []
    while parent[state] is not None:
        state, action = parent[state]
        actions.append(action)
    actions.reverse()
    return actions


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
