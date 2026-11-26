"""
test_search_agent.py — 탐색·에이전트 담당(TODO 4 · 5 · 6 · 7) 추가 테스트.   실행: python test_search_agent.py

test_agent.py(공식 자가 점검)보다 더 자세히 확인합니다.
  · A*  : 최적성(휴리스틱 없는 균일 비용 탐색과 길이 비교), 시작=목표, 통과 불가 칸, 확장 노드 수
  · PLAN-SHOT : 목표 칸을 바라보고 Shoot 으로 끝나는지
  · TELL (TODO 5) : 바람·냄새 지각이 올바른 절로 바뀌는지  ← logic.py 미구현이어도 실행됨(to_cnf만 사용)
  · ASK·행동 (TODO 6·7) : 그림 7.2, 사격 세계, 무작위 세계  ← logic.py TODO 1~3 이 필요 (없으면 SKIP)
"""
import random
import traceback

from planner import plan_route, plan_shot, astar, successors, DIRS
from wumpus_env import Percept, WumpusWorld


class Skip(Exception):
    pass


def needs_logic(f):
    """logic.py(TODO 1~3)가 아직 없으면 SKIP 처리"""
    def g():
        try:
            return f()
        except NotImplementedError as e:
            raise Skip(f"logic.py 미구현: {e}")
    g.__name__ = f.__name__
    return g


# ------------------------------------------------------------------ A*
def t_astar_basic():
    allowed = {(1, 1), (2, 1), (3, 1), (1, 2), (2, 2)}
    assert plan_route((1, 1), 0, {(1, 1)}, allowed) == [], "시작 칸이 목표면 빈 계획"
    assert plan_route((1, 1), 0, {(3, 1)}, allowed) == ["Forward", "Forward"]
    assert plan_route((1, 1), 2, {(2, 1)}, allowed) in (["TurnLeft", "TurnLeft", "Forward"],
                                                        ["TurnRight", "TurnRight", "Forward"])
    assert plan_route((1, 1), 0, set(), allowed) is None, "목표가 없으면 None"


def t_astar_blocked():
    # (2,1),(1,2)를 막으면 [1,1]에 갇힘
    assert plan_route((1, 1), 0, {(3, 3)}, {(1, 1), (3, 3)}) is None
    # 벽을 돌아가야 하는 경우: ㄷ자 통로
    allowed = {(1, 1), (1, 2), (1, 3), (2, 3), (3, 3), (3, 2), (3, 1)}
    plan = plan_route((1, 1), 0, {(3, 1)}, allowed)
    assert plan is not None and plan.count("Forward") == 6, plan


def _simulate(start, plan, allowed):
    x, y, d = start
    for a in plan:
        if a == "TurnLeft": d = (d + 1) % 4
        elif a == "TurnRight": d = (d - 1) % 4
        elif a == "Forward":
            dx, dy = DIRS[d]; x, y = x + dx, y + dy
            assert (x, y) in allowed, f"허용되지 않은 칸 {(x, y)} 통과"
        else:
            raise AssertionError(a)
    return x, y, d


def t_astar_optimal_random():
    """무작위 허용 칸 500개 사례에서 A*(맨해튼) 길이 == 균일 비용 탐색(h=0) 길이, 그리고 확장 노드 수 ≤"""
    rng = random.Random(7)
    cells = [(x, y) for x in range(1, 5) for y in range(1, 5)]
    exp_a = exp_u = 0
    for _ in range(500):
        allowed = {c for c in cells if rng.random() < 0.7} | {(1, 1)}
        goal = rng.choice(cells)
        d = rng.randrange(4)
        sa, su = {"expanded": 0}, {"expanded": 0}
        pa = plan_route((1, 1), d, {goal}, allowed, sa)
        pu = astar((1, 1, d), lambda s: (s[0], s[1]) == goal, lambda s: 0, allowed | {goal}, su)
        assert (pa is None) == (pu is None)
        if pa is not None:
            assert len(pa) == len(pu), f"A* 길이 {len(pa)} ≠ 최적 {len(pu)}"
            end = _simulate((1, 1, d), pa, allowed | {goal, (1, 1)})
            assert end[:2] == goal
        exp_a += sa["expanded"]; exp_u += su["expanded"]
    assert exp_a <= exp_u, (exp_a, exp_u)
    print(f"      확장 노드 수 합계  A* {exp_a}  vs  균일 비용(h=0) {exp_u}  ({100 * (1 - exp_a / exp_u):.1f}% 절약)")


def t_plan_shot():
    allowed = {(1, 1), (2, 1), (1, 2)}
    plan = plan_shot((1, 1), 0, (1, 3), allowed, 4)       # [1,3]을 쏘려면 북쪽을 봐야 함
    assert plan is not None and plan[-1] == "Shoot"
    x, y, d = _simulate((1, 1, 0), plan[:-1], allowed)
    assert x == 1 and d == 1, (x, y, d)
    assert plan_shot((1, 1), 0, (3, 3), {(1, 1)}, 4) is None, "같은 행·열의 허용 칸이 없으면 None"


# ---------------------------------------------------------- TELL (TODO 5)
def t_tell_percept():
    from agent import HybridWumpusAgent
    a = HybridWumpusAgent()
    a.tell_percept(Percept(breeze=True))                  # [1,1]에서 바람
    cl = a.kb.clauses
    assert frozenset({"P21", "P12"}) in cl, "바람 → P21 ∨ P12"
    for c in ["W11", "W21", "W12"]:
        assert frozenset({"~" + c}) in cl, f"냄새 없음 → ¬{c} (자기 칸 포함)"
    n = len(cl)
    a.tell_percept(Percept(breeze=True))                  # 같은 칸 두 번째 → 중복 TELL 없음
    assert len(a.kb.clauses) == n

    b = HybridWumpusAgent()
    b.pos = (2, 2)
    b.tell_percept(Percept(stench=True))
    assert frozenset({"W22", "W12", "W32", "W21", "W23"}) in b.kb.clauses, "냄새 → 자기 칸 + 이웃 중 웜퍼스"
    for c in ["P12", "P32", "P21", "P23", "P22"]:
        assert frozenset({"~" + c}) in b.kb.clauses


def t_tell_after_scream():
    from agent import HybridWumpusAgent
    a = HybridWumpusAgent()
    a.shot = ((1, 1), 0)
    a.tell_percept(Percept(scream=True))
    assert a.wumpus_dead
    a2 = HybridWumpusAgent()
    a2.shot = ((1, 1), 1)                                 # 북쪽으로 쐈는데 빗나감
    a2.tell_percept(Percept())
    for y in range(1, 5):
        assert frozenset({f"~W1{y}"}) in a2.kb.clauses, "빗나간 화살 줄에는 웜퍼스 없음"


# ---------------------------------------------------- ASK·행동 (TODO 6·7)
def _run(path=None, seed=None, **kw):
    from agent import HybridWumpusAgent
    from main import run_episode
    w = WumpusWorld.from_file(path) if path else WumpusWorld.random(seed=seed)
    a = HybridWumpusAgent(**kw)
    return w, a, run_episode(w, a)


@needs_logic
def t_update_knowledge_fig72():
    from agent import HybridWumpusAgent
    a = HybridWumpusAgent()
    a.tell_percept(Percept())                             # [1,1] 아무 지각 없음
    a.update_knowledge()
    assert {(2, 1), (1, 2)} <= a.safe, a.safe
    a.pos = (2, 1); a.tell_percept(Percept(breeze=True))
    a.pos = (1, 2); a.tell_percept(Percept(stench=True))
    a.update_knowledge()
    assert (3, 1) in a.known_pit, "교재 7.3절: [3,1] 구덩이"
    assert a.known_wumpus == (1, 3), "교재 7.3절: [1,3] 웜퍼스"
    assert (2, 2) in a.safe


@needs_logic
def t_fig72_both_engines():
    for m in ("dpll", "tt"):
        _, a, r = _run("worlds/world_fig7_2.txt", method=m)
        assert r["outcome"] == "win", (m, r["outcome"])
        assert r["score"] >= 970, (m, r["score"])


@needs_logic
def t_shoot_world():
    w, a, r = _run("worlds/world_shoot.txt")
    assert r["outcome"] == "win", r["outcome"]
    assert r["shot"] and a.wumpus_dead, "웜퍼스를 쏴서 길을 열어야 함"
    _, _, r2 = _run("worlds/world_shoot.txt", shoot=False)
    assert r2["outcome"] == "climb", "사격 없이는 금에 갈 수 없는 세계"


@needs_logic
def t_team_world():
    """팀 설계 세계: 조합 추론으로 웜퍼스 [3,1]·구덩이 [1,3] 확정, 사격해야만 성공"""
    w, a, r = _run("worlds/world_team.txt")
    assert r["outcome"] == "win" and r["score"] == 969, (r["outcome"], r["score"])
    assert a.wumpus_dead and {(1, 3), (2, 3), (4, 2)} <= a.known_pit, a.known_pit
    assert _run("worlds/world_team.txt", shoot=False)[2]["outcome"] == "climb"
    assert _run("worlds/world_team.txt", policy="risk", shoot=False)[2]["outcome"] == "pit"


@needs_logic
def t_random_sound_and_rational():
    """무작위 300개: safe 정책은 절대 죽지 않고, 금을 찾으면 반드시 들고 나오며, 시간 초과가 없다."""
    for i in range(300):
        _, a, r = _run(seed=i)
        assert r["outcome"] in ("win", "climb"), (i, r["outcome"])
        if a.has_gold:
            assert r["outcome"] == "win", (i, "금을 들고도 탈출 못 함")
        assert a.pos == (1, 1)


if __name__ == "__main__":
    tests = [("A* 기본", t_astar_basic), ("A* 막힌 길·우회", t_astar_blocked),
             ("A* 최적성 (무작위 500)", t_astar_optimal_random), ("PLAN-SHOT", t_plan_shot),
             ("TELL 지각 → 절", t_tell_percept), ("TELL 사격 결과", t_tell_after_scream),
             ("ASK 교재 7.3절 추론", t_update_knowledge_fig72), ("그림 7.2 (DPLL·TT)", t_fig72_both_engines),
             ("사격 세계", t_shoot_world), ("팀 설계 세계", t_team_world), ("무작위 300 (건전성·합리성)", t_random_sound_and_rational)]
    ok = skip = 0
    for name, f in tests:
        try:
            f(); print(f"PASS  {name}"); ok += 1
        except Skip as e:
            print(f"SKIP  {name}  ({e})"); skip += 1
        except Exception as e:
            print(f"FAIL  {name}  → {e}")
            traceback.print_exc(limit=2)
    print(f"\n{ok}/{len(tests)} 통과, {skip}개 SKIP")
