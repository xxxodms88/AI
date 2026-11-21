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
    def __init__(self, size=4, method="dpll", policy="safe", prune=True, verbose=False, shoot=True):
        self.size, self.policy, self.verbose = size, policy, verbose
        self.use_shot = shoot                   # TODO 7-③ 사격 사용 여부 (실험용 스위치)
        self.search_stats = {"expanded": 0}     # A*가 확장한 노드 수 누적 (보고서용)
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
        # (1) 지금 살아서 c에 서 있다 → c에는 구덩이가 없다
        self.kb.tell(Not(P(c)))
        # (2) 웜퍼스가 살아 있는데 c에서 죽지 않았다 → c에 웜퍼스도 없다
        #     (웜퍼스가 죽은 뒤에는 그 칸에 들어갈 수 있으므로 ¬W(c)를 말하면 거짓이 될 수 있음.
        #      W_xy 는 '처음 위치'를 뜻하는 비시간적 기호이기 때문)
        if not self.wumpus_dead:
            self.kb.tell(Not(W(c)))
        # (3) 바람 규칙  B_c ⇔ ∨P(이웃)  에 관측값 대입
        if p.breeze:
            self.kb.tell(Or(*[P(n) for n in nb]))
        else:
            self.kb.tell(And(*[Not(P(n)) for n in nb]))
        # (4) 냄새 규칙  S_c ⇔ W(c) ∨ ∨W(이웃)   — 환경은 웜퍼스 칸 자신에서도 냄새를 주고,
        #     죽은 웜퍼스도 냄새가 남으므로 웜퍼스 생사와 무관하게 항상 참인 규칙이다.
        around = [c] + nb
        if p.stench:
            self.kb.tell(Or(*[W(n) for n in around]))
        else:
            self.kb.tell(And(*[Not(W(n)) for n in around]))
        # (5) KB가 바뀌었으니 다음 update_knowledge에서 다시 ASK
        self.dirty = True

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
        #
        # 구현 메모
        #   · 한 번 증명된 사실은 KB가 커져도 바뀌지 않는다(단조성, monotonicity).
        #     그래서 이미 not_pit / known_pit 등에 들어간 칸은 다시 묻지 않는다 → ASK 횟수 절약.
        #   · ASK(¬X)가 거짓이라고 X가 참인 것은 아니다("모른다"일 수 있음) → ASK(X)를 따로 해야 함.
        #   · 웜퍼스 위치가 확정되면 나머지 칸은 ¬W 를 TELL 해서 이후 추론을 쉽게 만든다.
        for c in self.cells:
            # ---- 구덩이
            if c not in self.not_pit and c not in self.known_pit:
                if self.kb.ask(Not(P(c))):
                    self.not_pit.add(c)
                elif self.kb.ask(P(c)):
                    self.known_pit.add(c)
            # ---- 웜퍼스 (살아 있고, 아직 위치를 모를 때만)
            if not self.wumpus_dead and self.known_wumpus is None and c not in self.not_wumpus:
                if self.kb.ask(Not(W(c))):
                    self.not_wumpus.add(c)
                elif self.kb.ask(W(c)):
                    self.known_wumpus = c
                    for o in self.cells:                 # 웜퍼스는 정확히 하나
                        if o != c:
                            self.kb.tell(Not(W(o)))
                            self.not_wumpus.add(o)
        if self.verbose:
            unvisited_safe = sorted(self.safe - self.visited)
            print(f"      ASK → 안전·미방문 {unvisited_safe}  구덩이 {sorted(self.known_pit)}"
                  f"  웜퍼스 {self.known_wumpus}")

    # ------------------------------------------------------------- 행동 결정
    def choose_plan(self, p):
        allowed = self.safe | self.visited
        if p.glitter and not self.has_gold:
            home = plan_route(self.pos, self.dir, {(1, 1)}, allowed, self.search_stats) or []
            return ["Grab"] + home + ["Climb"]
        # [TODO 7-②] 방문하지 않은 안전 칸(self.safe − self.visited)이 있으면
        #            plan_route(self.pos, self.dir, 그 칸들, allowed) 결과를 반환
        # [TODO 7-③] (선택) 화살이 있고 웜퍼스가 살아 있을 때, 구덩이는 없다고 증명되었지만
        #            웜퍼스 때문에 들어가지 못하는 칸이 있으면 plan_shot(...) 으로 사격 계획 반환
        #            사격 후 Scream 여부는 tell_percept 앞부분에서 이미 처리됨

        # ② 탐험: 방문하지 않은 안전 칸 중 (동작 수 기준) 가장 가까운 칸으로
        #    plan_route는 여러 목표를 한 번에 받아 A*로 가장 가까운 목표를 찾는다.
        frontier = self.safe - self.visited
        if frontier:
            plan = plan_route(self.pos, self.dir, frontier, allowed, self.search_stats)
            if plan:
                return plan

        # ③ 사격: 구덩이는 없다고 증명됐지만 웜퍼스 가능성 때문에 못 가는 칸이 있을 때
        if self.use_shot and self.has_arrow and not self.wumpus_dead:
            plan = self.plan_wumpus_shot(allowed)
            if plan:
                return plan

        # ④ 모험: 증명상 위험하지 않은 칸 (구덩이·웜퍼스가 확정되지 않은 칸)
        if self.policy == "risk":
            cand = [c for c in self.cells if c not in self.visited and c not in self.known_pit
                    and (self.wumpus_dead or c != self.known_wumpus)
                    and any(n in self.visited for n in self.neighbors(c))]
            risk = lambda c: (c not in self.not_pit) + (not self.wumpus_dead and c not in self.not_wumpus)
            for c in sorted(cand, key=lambda c: (risk(c), abs(c[0] - self.pos[0]) + abs(c[1] - self.pos[1]))):
                plan = plan_route(self.pos, self.dir, {c}, allowed, self.search_stats)
                if plan: return plan
        # ⑤ 귀환
        return (plan_route(self.pos, self.dir, {(1, 1)}, allowed, self.search_stats) or []) + ["Climb"]

    def plan_wumpus_shot(self, allowed):
        """[TODO 7-③] PLAN-SHOT — 웜퍼스 때문에만 막힌 칸을 열기 위한 사격 계획.

        후보(target) = 방문 안 함 ∧ 구덩이 없음(증명) ∧ 웜퍼스 없음은 증명 안 됨
          · 웜퍼스 위치가 확정(known_wumpus)되어 있으면 그 칸만 노린다 (맞으면 Scream 확정).
          · 확정이 아니면 후보 칸 중 하나를 노린다. 빗나가도 tell_percept가
            '화살이 지나간 줄에는 웜퍼스가 없다'를 TELL 하므로 정보를 얻는다.
        같은 행·열의 안전 칸에서 쏘므로, 사격 위치까지 가는 길도 안전하다.
        화살 −10점은 금 +1000점에 비해 작으므로, 막힌 칸이 있으면 쏘는 것이 이득이다.
        """
        blocked = [c for c in self.cells
                   if c not in self.visited and c in self.not_pit and c not in self.not_wumpus]
        if self.known_wumpus is not None:
            blocked = [c for c in blocked if c == self.known_wumpus]
        if not blocked:
            return None
        # 방문한 칸과 붙어 있는(=죽이면 바로 들어갈 수 있는) 칸을 먼저 고려하고,
        # 같은 그룹 안에서는 사격 계획(이동+회전+Shoot)이 가장 짧은 것을 고른다.
        near = [c for c in blocked if any(n in self.visited for n in self.neighbors(c))]
        far = [c for c in blocked if c not in near]
        best = None
        for group in (near, far):
            for target in sorted(group):
                plan = plan_shot(self.pos, self.dir, target, allowed, self.size, self.search_stats)
                if plan and (best is None or len(plan) < len(best)):
                    best = plan
            if best is not None:
                break
        if self.verbose and best:
            print(f"      PLAN-SHOT → 후보 {blocked}, 계획 {best}")
        return best

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
