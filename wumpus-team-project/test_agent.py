"""
test_agent.py — 구현 자가 점검용 테스트.   실행: python test_agent.py
TODO를 하나씩 완성할 때마다 실행해 보세요. (통과한 항목은 PASS로 표시)
"""
import traceback
from logic import (Symbol, Iff, Or, Not, to_cnf, tt_entails, dpll_satisfiable, dpll_entails, PropKB,
                   clause_status, find_pure_symbol, find_unit_clause)


class Bonus(Exception):
    """가산점 항목이 아직 구현되지 않았음을 알림"""

P11, P12, P21, P22, P31, B11, B21 = map(Symbol, ["P11", "P12", "P21", "P22", "P31", "B11", "B21"])


def kb_textbook():
    """AIMA 7.4.3 의 R1~R5"""
    kb = set()
    for s in [Not(P11), Iff(B11, Or(P12, P21)), Iff(B21, Or(P11, P22, P31)), Not(B11), B21]:
        kb |= to_cnf(s)
    return kb


def t1_tt():
    kb = kb_textbook()
    assert tt_entails(kb, Not(P12)) is True, "R1~R5 ⊨ ¬P12 이어야 함"
    assert tt_entails(kb, Not(P22)) is False, "R1~R5 ⊭ ¬P22 이어야 함"
    assert tt_entails(kb, P22) is False, "R1~R5 ⊭ P22 이어야 함"
    assert tt_entails(kb, Or(P22, P31)) is True, "R1~R5 ⊨ P22 ∨ P31 이어야 함"


def t21_clause_status():
    fs = frozenset
    assert clause_status(fs({"P12", "P21"}), {"P12": False}) == ("undecided", ["P21"])
    assert clause_status(fs({"P12", "P21"}), {"P12": False, "P21": False}) == ("false", [])
    assert clause_status(fs({"~P12", "P21"}), {"P12": False}) == ("true", [])
    st, ls = clause_status(fs({"P12", "~P21"}), {})
    assert st == "undecided" and sorted(ls) == ["P12", "~P21"], (st, ls)


def t22_dpll_basic():
    """휴리스틱을 끈 기본 DPLL (조기 종료 + 분기)"""
    for up, uu in [(False, False), (True, True)]:
        assert dpll_satisfiable(to_cnf(Or(P11, P12) & Not(P11)), None, up, uu) is True
        assert dpll_satisfiable(to_cnf(Or(P11, P12) & Not(P11) & Not(P12)), None, up, uu) is False
        assert dpll_satisfiable(to_cnf(P11 & Not(P11) | (P12 & Not(P12))), None, up, uu) is False
        assert dpll_satisfiable(kb_textbook(), None, up, uu) is True


def t23_pure():
    fs = frozenset
    cl = [fs({"A", "~B"}), fs({"~B", "C"}), fs({"~C", "A"})]
    r = find_pure_symbol(["A", "B", "C"], cl, {})
    if r == (None, None): raise Bonus("find_pure_symbol 미구현")
    assert r == ("A", True), r
    assert find_pure_symbol(["A", "B", "C"], cl, {"A": True}) == ("B", False), "A가 할당되면 참이 된 절은 무시"
    assert find_pure_symbol(["A"], [fs({"A"}), fs({"~A"})], {}) == (None, None)


def t24_unit():
    fs = frozenset
    r = find_unit_clause([fs({"A", "B"})], {"A": False})
    if r == (None, None): raise Bonus("find_unit_clause 미구현")
    assert r == ("B", True), r
    assert find_unit_clause([fs({"~C"})], {}) == ("C", False)
    assert find_unit_clause([fs({"A", "B"})], {}) == (None, None)
    assert find_unit_clause([fs({"A", "B"})], {"A": True}) == (None, None), "이미 참인 절은 단위 절이 아님"


def t3_dpll_entails():
    kb = kb_textbook()
    for q in [Not(P12), Not(P22), P22, Or(P22, P31), Not(P21)]:
        assert dpll_entails(kb, q) == tt_entails(kb, q), f"질의 {q}: DPLL과 TT 결과가 다름"


def t4_astar():
    from planner import plan_route
    allowed = {(1, 1), (2, 1), (3, 1), (1, 2), (2, 2)}
    plan = plan_route((1, 1), 0, {(3, 1)}, allowed)
    assert plan == ["Forward", "Forward"], plan
    plan = plan_route((1, 1), 0, {(2, 2)}, allowed)
    assert plan is not None and len(plan) == 3, f"[1,1]→[2,2] 최소 동작 수는 3: {plan}"
    assert plan_route((1, 1), 0, {(4, 4)}, allowed - {(2, 1), (1, 2)}) is None


def t5_agent_fig72():
    from wumpus_env import WumpusWorld
    from agent import HybridWumpusAgent
    from main import run_episode
    w = WumpusWorld.from_file("worlds/world_fig7_2.txt")
    r = run_episode(w, HybridWumpusAgent())
    assert r["outcome"] == "win", f"그림 7.2 세계에서는 금을 가지고 탈출해야 함: {r['outcome']}"


def t6_agent_sound():
    from wumpus_env import WumpusWorld
    from agent import HybridWumpusAgent
    from main import run_episode
    for i in range(200):
        w = WumpusWorld.random(seed=i)
        a = HybridWumpusAgent(policy="safe")
        r = run_episode(w, a)
        assert r["outcome"] not in ("pit", "wumpus"), f"seed {i}: 안전 정책인데 사망 ({r['outcome']})"
        m = {f"{k}{x}{y}": ((x, y) in w.pits if k == "P" else (x, y) == w.wumpus)
             for k in "PW" for x in range(1, 5) for y in range(1, 5)}
        for c in a.kb.clauses:
            assert any((not m[l[1:]]) if l[0] == "~" else m[l] for l in c), f"seed {i}: 실제 세계에서 거짓인 절 {set(c)}"


if __name__ == "__main__":
    tests = [("TODO 1    tt_entails", t1_tt),
             ("TODO 2-1  clause_status", t21_clause_status), ("TODO 2-2  dpll (기본: 조기 종료+분기)", t22_dpll_basic),
             ("TODO 2-3  find_pure_symbol [가산점]", t23_pure), ("TODO 2-4  find_unit_clause [가산점]", t24_unit),
             ("TODO 3    dpll_entails", t3_dpll_entails), ("TODO 4    A*", t4_astar),
             ("TODO 5~7 에이전트 (그림 7.2)", t5_agent_fig72), ("TODO 5~7 에이전트 (무작위 200개, 건전성)", t6_agent_sound)]
    ok = 0
    for name, f in tests:
        try:
            f(); print(f"PASS  {name}"); ok += 1
        except Bonus as e:
            print(f"(+)   {name}  (가산점 항목, {e} — 기본 DPLL로 동작함)")
        except NotImplementedError as e:
            print(f"----  {name}  (미구현: {e})")
        except Exception as e:
            print(f"FAIL  {name}  → {e}")
            traceback.print_exc(limit=1)
    print(f"\n{ok}/{len(tests)} 통과  (필수 {len(tests) - 2}개 + 가산점 2개)")
