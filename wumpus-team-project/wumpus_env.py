"""
wumpus_env.py — 웜퍼스 세계(Wumpus World) 환경 시뮬레이터
(AIMA 4판 7.2절의 PEAS 명세를 따름)

좌표계: (x, y), 1 ≤ x, y ≤ N.  x = 열(동쪽으로 증가), y = 행(북쪽으로 증가)
시작:  에이전트는 [1,1]에서 동쪽(East)을 바라보고 시작
방향:  0 = East, 1 = North, 2 = West, 3 = South

지각(percept): [Stench, Breeze, Glitter, Bump, Scream]
동작(action):  Forward, TurnLeft, TurnRight, Grab, Shoot, Climb
점수:          금을 가지고 [1,1]에서 Climb +1000, 사망 −1000,
               동작 1회당 −1, 화살 사용 −10

※ 이 파일은 학생에게 완성본으로 제공되는 파일입니다. 수정하지 마세요.
"""
from __future__ import annotations
import random
from dataclasses import dataclass

ACTIONS = ("Forward", "TurnLeft", "TurnRight", "Grab", "Shoot", "Climb")
DIRS = {0: (1, 0), 1: (0, 1), 2: (-1, 0), 3: (0, -1)}
DIR_NAME = {0: "E", 1: "N", 2: "W", 3: "S"}


@dataclass(frozen=True)
class Percept:
    stench: bool = False
    breeze: bool = False
    glitter: bool = False
    bump: bool = False
    scream: bool = False

    def __str__(self):
        names = ("Stench", "Breeze", "Glitter", "Bump", "Scream")
        vals = (self.stench, self.breeze, self.glitter, self.bump, self.scream)
        return "[" + ", ".join(n if v else "None" for n, v in zip(names, vals)) + "]"


class WumpusWorld:
    """웜퍼스 세계 환경. reset() 후 step(action)을 반복 호출한다."""

    def __init__(self, size=4, pits=(), wumpus=(1, 3), gold=(2, 3), max_steps=500):
        self.size = size
        self.pits = set(map(tuple, pits))
        self.wumpus = tuple(wumpus)
        self.gold = tuple(gold)
        self.max_steps = max_steps
        for c in [*self.pits, self.wumpus, self.gold]:
            if not self.inside(c):
                raise ValueError(f"격자 밖 좌표: {c}")
        if (1, 1) in self.pits or self.wumpus == (1, 1):
            raise ValueError("[1,1]에는 구덩이·웜퍼스를 둘 수 없습니다.")
        self.reset()

    # ------------------------------------------------------------------ 생성
    @classmethod
    def from_file(cls, path, **kw):
        """텍스트 파일에서 세계를 읽는다. 첫 줄 = 가장 위쪽 행(y = N).
        토큰: '.' 빈칸, 'P' 구덩이, 'W' 웜퍼스, 'G' 금, 'A' 시작(=[1,1], 생략 가능)
        한 칸에 여러 개면 붙여 쓴다. 예) 'WG' = 웜퍼스와 금이 같은 칸"""
        rows = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.split("#")[0].strip()
                if line:
                    rows.append(line.split())
        n = len(rows)
        if any(len(r) != n for r in rows):
            raise ValueError("세계 파일은 N×N 정사각형이어야 합니다.")
        pits, wumpus, gold = [], None, None
        for i, row in enumerate(rows):
            y = n - i
            for j, tok in enumerate(row):
                x = j + 1
                if "P" in tok: pits.append((x, y))
                if "W" in tok: wumpus = (x, y)
                if "G" in tok: gold = (x, y)
        if wumpus is None or gold is None:
            raise ValueError("웜퍼스(W)와 금(G)이 각각 하나씩 있어야 합니다.")
        return cls(n, pits, wumpus, gold, **kw)

    @classmethod
    def random(cls, seed=None, size=4, p_pit=0.2, **kw):
        """AIMA 규칙대로 무작위 생성: [1,1]을 제외한 각 칸에 확률 p_pit로 구덩이,
        웜퍼스와 금은 [1,1]을 제외한 칸 중에서 균등하게 선택."""
        rng = random.Random(seed)
        cells = [(x, y) for y in range(1, size + 1) for x in range(1, size + 1) if (x, y) != (1, 1)]
        pits = [c for c in cells if rng.random() < p_pit]
        return cls(size, pits, rng.choice(cells), rng.choice(cells), **kw)

    def to_text(self):
        lines = []
        for y in range(self.size, 0, -1):
            toks = []
            for x in range(1, self.size + 1):
                t = ("P" if (x, y) in self.pits else "") + ("W" if (x, y) == self.wumpus else "") \
                    + ("G" if (x, y) == self.gold else "")
                toks.append(t or ".")
            lines.append(" ".join(toks))
        return "\n".join(lines)

    # ------------------------------------------------------------- 유틸리티
    def inside(self, c):
        return 1 <= c[0] <= self.size and 1 <= c[1] <= self.size

    def neighbors(self, c):
        x, y = c
        return [n for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)) if self.inside(n)]

    # ------------------------------------------------------------ 진행
    def reset(self):
        self.agent = (1, 1)
        self.direction = 0
        self.has_arrow = True
        self.has_gold = False
        self.gold_taken = False
        self.wumpus_alive = True
        self.score = 0
        self.steps = 0
        self.done = False
        self.outcome = None          # 'win' | 'climb' | 'pit' | 'wumpus' | 'timeout'
        self.trajectory = [(self.agent, self.direction, None)]
        self._bump = self._scream = False
        return self.percept()

    def percept(self):
        a = self.agent
        nb = self.neighbors(a) + [a]
        p = Percept(
            stench=self.wumpus in nb,                       # 죽은 웜퍼스도 냄새는 남는다
            breeze=any(n in self.pits for n in self.neighbors(a)),
            glitter=(a == self.gold and not self.gold_taken),
            bump=self._bump, scream=self._scream)
        self._bump = self._scream = False
        return p

    def step(self, action):
        """동작 하나를 실행하고 (percept, reward, done)을 돌려준다."""
        if self.done:
            raise RuntimeError("에피소드가 끝났습니다. reset()을 호출하세요.")
        if action not in ACTIONS:
            raise ValueError(f"알 수 없는 동작: {action}")
        reward = -1
        self.steps += 1
        if action == "Forward":
            dx, dy = DIRS[self.direction]
            nxt = (self.agent[0] + dx, self.agent[1] + dy)
            if self.inside(nxt):
                self.agent = nxt
            else:
                self._bump = True
        elif action == "TurnLeft":
            self.direction = (self.direction + 1) % 4
        elif action == "TurnRight":
            self.direction = (self.direction - 1) % 4
        elif action == "Grab":
            if self.agent == self.gold and not self.gold_taken:
                self.gold_taken = self.has_gold = True
        elif action == "Shoot":
            if self.has_arrow:
                self.has_arrow = False
                reward -= 10
                dx, dy = DIRS[self.direction]
                c = self.agent
                while self.inside(c):
                    if c == self.wumpus and self.wumpus_alive:
                        self.wumpus_alive = False
                        self._scream = True
                        break
                    c = (c[0] + dx, c[1] + dy)
        elif action == "Climb":
            if self.agent == (1, 1):
                self.done = True
                if self.has_gold:
                    reward += 1000
                    self.outcome = "win"
                else:
                    self.outcome = "climb"
        # 사망 판정
        if not self.done:
            if self.agent in self.pits:
                reward -= 1000; self.done = True; self.outcome = "pit"
            elif self.agent == self.wumpus and self.wumpus_alive:
                reward -= 1000; self.done = True; self.outcome = "wumpus"
            elif self.steps >= self.max_steps:
                self.done = True; self.outcome = "timeout"
        self.score += reward
        self.trajectory.append((self.agent, self.direction, action))
        return self.percept(), reward, self.done

    def render(self):
        """콘솔용 간단한 그림."""
        arrow = {0: ">", 1: "^", 2: "<", 3: "v"}
        out = []
        for y in range(self.size, 0, -1):
            row = []
            for x in range(1, self.size + 1):
                c = (x, y)
                s = ("P" if c in self.pits else "") + \
                    (("W" if self.wumpus_alive else "w") if c == self.wumpus else "") + \
                    ("G" if c == self.gold and not self.gold_taken else "")
                if c == self.agent:
                    s += arrow[self.direction]
                row.append(f"{s:^5}")
            out.append("|" + "|".join(row) + "|")
        return "\n".join(out)


def gold_reachable(world: WumpusWorld) -> bool:
    """구덩이를 지나지 않고 [1,1]에서 금까지 갈 수 있는가? (웜퍼스는 사살 가능하므로 통과 허용)
    → '해결 가능한 세계'의 상한 판정용. 실험 분석에 사용한다."""
    if world.gold in world.pits:
        return False
    seen, stack = {(1, 1)}, [(1, 1)]
    while stack:
        c = stack.pop()
        if c == world.gold:
            return True
        for n in world.neighbors(c):
            if n not in seen and n not in world.pits:
                seen.add(n); stack.append(n)
    return False
