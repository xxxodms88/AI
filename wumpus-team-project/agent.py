"""
agent.py — 명제논리 기반 하이브리드 웜퍼스 에이전트 (AIMA 그림 7.20 HYBRID-WUMPUS-AGENT 단순화판)

설계 요약
  · 위치·방향은 에이전트가 스스로 추적(경로 적분) → 비시간적(atemporal) 기호 사용
      P{x}{y} : [x,y]에 구덩이가 있다      W{x}{y} : [x,y]에 (처음에) 웜퍼스가 있다
  · 지각 규칙  B_xy ⇔ ∨P(이웃),  S_xy ⇔ W_xy ∨ (∨W(이웃))  에 관측값을 대입하여 TELL
      Breeze 있음 → (P_a ∨ P_b ∨ …)      Breeze 없음 → ¬P_a ∧ ¬P_b ∧ …
  · ASK(KB, ¬P_xy), ASK(KB, ¬W_xy) 로 안전 칸 판정 (함축 검사: TT 또는 DPLL)
  · 행동 우선순위
      ① Glitter → Grab, 집으로 경로 계획, Climb
      ② 방문하지 않은 안전 칸이 있으면 A*로 가장 가까운 칸으로 이동
      ③ 화살이 있고 웜퍼스 때문에만 막힌 칸이 있으면 → 사격 계획(PLAN-SHOT)
      ④ (policy='risk') 증명상 위험하지 않은 칸으로 모험
      ⑤ 그 외 → [1,1]로 돌아가 Climb

※ 학생 구현 부분: [TODO 5] tell_percept, [TODO 6] update_knowledge, [TODO 7] choose_plan ②③
"""
from __future__ import annotations
from logic import PropKB, Symbol, Or, And, Not  # noqa: F401
from planner import plan_route, plan_shot, DIRS


def P(c): return Symbol(f"P{c[0]}{c[1]}")
def W(c): return Symbol(f"W{c[0]}{c[1]}")


class HybridWumpusAgent:
    def __init__(self, size=4, method="dpll", policy="safe", prune=True, verbose=False):
        self.size, self.policy, self.verbose = size, policy, verbose
        self.kb = PropKB(method, prune)
        self.cells = [(x, y) for y in range(1, size + 1) for x in range(1, size + 1)]
        self.pos, self.dir = (1, 1), 0
        self.visited, self.told = set(), set()
        self.not_pit, self.not_wumpus = set(), set()
        self.known_pit, self.known_wumpus = set(), None
        self.has_arrow, self.has_gold, self.wumpus_dead = True, False, False
        self.plan, self.shot, self.t = [], None, 0
        self.dirty = True                       # KB가 바뀌었는지 (ASK 재계산 필요 여부)
        self.log = []
        self.kb.tell(Not(P((1, 1))))            # 시작 칸은 안전하다 (환경 규칙)
        self.kb.tell(Not(W((1, 1))))

    # ---------------------------------------------------------------- 유틸
    def inside(self, c): return 1 <= c[0] <= self.size and 1 <= c[1] <= self.size

    def neighbors(self, c):
        x, y = c
        return [n for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)) if self.inside(n)]

    @property
    def safe(self):
        return {c for c in self.cells if c in self.not_pit and (self.wumpus_dead or c in self.not_wumpus)}

    # --------------------------------------------------------------- TELL
    def tell_percept(self, p):
        c = self.pos
        self.visited.add(c)
        if p.scream:                                    # 웜퍼스 사망
            self.wumpus_dead = True
        elif self.shot is not None:                     # 빗나감 → 화살 경로에는 웜퍼스 없음
            (x, y), d = self.shot
            dx, dy = DIRS[d]
            while self.inside((x, y)):
                self.kb.tell(Not(W((x, y)))); x, y = x + dx, y + dy
            self.dirty = True
        self.shot = None
        if c in self.told:
            return
        self.told.add(c)
        # [TODO 5] 현재 칸 c에서 받은 지각 p를 KB에 TELL 하라.
        #   (1) 살아 있으므로 c에는 구덩이가 없다           → ¬P(c)
        #   (2) 웜퍼스가 살아 있다면 c에 웜퍼스도 없다      → ¬W(c)
        #   (3) 바람:  B_c ⇔ (P(이웃1) ∨ P(이웃2) ∨ …)  에 관측값 대입
        #         p.breeze 이면 Or(*map(P, nb)),  아니면 And(*[Not(P(n)) for n in nb])
        #   (4) 냄새:  S_c ⇔ W(c) ∨ W(이웃1) ∨ …   (웜퍼스 칸 자신에서도 냄새가 남!)
        #   (5) 마지막에 self.dirty = True
        nb = self.neighbors(c)
        raise NotImplementedError("TODO 5: tell_percept")

    # ---------------------------------------------------------------- ASK
    def update_knowledge(self):
        if not self.dirty:
            return
        self.dirty = False
        # [TODO 6] 모든 칸 c에 대해 ASK 하여 지식 집합을 갱신하라.
        #   · c ∉ not_pit, c ∉ known_pit 이면
        #       ASK(KB, ¬P(c)) 가 참 → self.not_pit 에 추가
        #       아니면 ASK(KB, P(c)) 가 참 → self.known_pit 에 추가
        #   · 웜퍼스가 살아 있고 c ∉ not_wumpus 이고 아직 위치를 모르면
        #       ASK(KB, ¬W(c)) 가 참 → self.not_wumpus 에 추가
        #       아니면 ASK(KB, W(c)) 가 참 → self.known_wumpus = c,
        #             웜퍼스는 하나뿐이므로 다른 모든 칸 o 에 대해 TELL ¬W(o), not_wumpus 에 추가
        #   (self.safe 속성은 not_pit · not_wumpus 로부터 자동 계산됨)
        raise NotImplementedError("TODO 6: update_knowledge")

    # ------------------------------------------------------------- 행동 결정
    def choose_plan(self, p):
        allowed = self.safe | self.visited
        if p.glitter and not self.has_gold:
            home = plan_route(self.pos, self.dir, {(1, 1)}, allowed) or []
            return ["Grab"] + home + ["Climb"]
        # [TODO 7-②] 방문하지 않은 안전 칸(self.safe − self.visited)이 있으면
        #            plan_route(self.pos, self.dir, 그 칸들, allowed) 결과를 반환
        # [TODO 7-③] (선택) 화살이 있고 웜퍼스가 살아 있을 때, 구덩이는 없다고 증명되었지만
        #            웜퍼스 때문에 들어가지 못하는 칸이 있으면 plan_shot(...) 으로 사격 계획 반환
        #            사격 후 Scream 여부는 tell_percept 앞부분에서 이미 처리됨

        # ④ 모험: 증명상 위험하지 않은 칸 (구덩이·웜퍼스가 확정되지 않은 칸)
        if self.policy == "risk":
            cand = [c for c in self.cells if c not in self.visited and c not in self.known_pit
                    and (self.wumpus_dead or c != self.known_wumpus)
                    and any(n in self.visited for n in self.neighbors(c))]
            risk = lambda c: (c not in self.not_pit) + (not self.wumpus_dead and c not in self.not_wumpus)
            for c in sorted(cand, key=lambda c: (risk(c), abs(c[0] - self.pos[0]) + abs(c[1] - self.pos[1]))):
                plan = plan_route(self.pos, self.dir, {c}, allowed)
                if plan: return plan
        # ⑤ 귀환
        return (plan_route(self.pos, self.dir, {(1, 1)}, allowed) or []) + ["Climb"]

    # ------------------------------------------------------------ 에이전트 함수
    def __call__(self, percept):
        self.t += 1
        self.tell_percept(percept)
        self.update_knowledge()
        if percept.glitter and not self.has_gold:
            self.plan = []                               # 금 발견 시 계획 교체
        if not self.plan:
            self.plan = self.choose_plan(percept)
        action = self.plan.pop(0)
        here = self.pos
        self.apply(action)
        if self.verbose:
            print(f"t={self.t:3d} pos={here} {percept}  → {action:9s} |KB|={len(self.kb)}")
        self.log.append((self.t, here, str(percept), action, len(self.kb)))
        return action

    def apply(self, action):
        """동작이 자기 상태(위치·방향·소지품)에 미치는 영향을 스스로 기록"""
        if action == "Forward":
            dx, dy = DIRS[self.dir]
            nxt = (self.pos[0] + dx, self.pos[1] + dy)
            if self.inside(nxt): self.pos = nxt
        elif action == "TurnLeft": self.dir = (self.dir + 1) % 4
        elif action == "TurnRight": self.dir = (self.dir - 1) % 4
        elif action == "Grab": self.has_gold = True
        elif action == "Shoot":
            self.has_arrow = False
            self.shot = (self.pos, self.dir)


class RandomAgent:
    """비교 기준선: 무작위 동작 (Grab은 Glitter일 때, Climb은 금을 들고 [1,1]일 때)"""

    def __init__(self, seed=None, **_):
        import random
        self.rng = random.Random(seed)
        self.pos, self.dir, self.has_gold = (1, 1), 0, False

    def __call__(self, p):
        if p.glitter and not self.has_gold:
            self.has_gold = True; return "Grab"
        if self.has_gold and self.pos == (1, 1):
            return "Climb"
        a = self.rng.choice(["Forward", "Forward", "TurnLeft", "TurnRight"])
        if a == "Forward":
            dx, dy = DIRS[self.dir]
            n = (self.pos[0] + dx, self.pos[1] + dy)
            if 1 <= n[0] <= 4 and 1 <= n[1] <= 4: self.pos = n
        elif a == "TurnLeft": self.dir = (self.dir + 1) % 4
        else: self.dir = (self.dir - 1) % 4
        return a
