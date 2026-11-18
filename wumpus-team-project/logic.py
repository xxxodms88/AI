"""
logic.py — 명제논리(propositional logic) 표현, CNF 변환, 함축(entailment) 검사

  · Expr / Symbol      : 문장 표현.  ~a(부정)  a & b(논리곱)  a | b(논리합)
                         a >> b(함의 ⇒)  Iff(a, b)(동치 ⇔)
  · to_cnf(s)          : 문장 → 절(clause)들의 집합 (절 = 리터럴의 frozenset)
  · tt_entails(...)    : 진리표 열거에 의한 모델 검사 (AIMA 그림 7.10)   ← [TODO 1]
  · DPLL (AIMA 그림 7.17)  clause_status / dpll ← [TODO 2-1, 2-2 필수]
                          find_pure_symbol / find_unit_clause ← [TODO 2-3, 2-4 가산점]
  · dpll_entails()     : DPLL을 이용한 함축 검사 (귀류법)                 ← [TODO 3]
  · PropKB             : TELL / ASK 인터페이스를 갖는 지식베이스

리터럴 표기:  'P13'  (양), '~P13' (부정)
"""
from __future__ import annotations
import time
from collections import defaultdict


# ====================================================================== 문장
class Expr:
    __slots__ = ("op", "args")

    def __init__(self, op, *args):
        self.op, self.args = op, args

    def __invert__(self): return Expr("~", self)
    def __and__(self, o): return Expr("&", self, o)
    def __or__(self, o): return Expr("|", self, o)
    def __rshift__(self, o): return Expr("=>", self, o)

    def __repr__(self):
        if self.op == "SYM": return self.args[0]
        if self.op == "~": return "¬" + repr(self.args[0])
        sym = {"&": " ∧ ", "|": " ∨ ", "=>": " ⇒ ", "<=>": " ⇔ "}[self.op]
        return "(" + sym.join(map(repr, self.args)) + ")"

    def symbols(self):
        if self.op == "SYM": return {self.args[0]}
        s = set()
        for a in self.args: s |= a.symbols()
        return s

    def pl_true(self, model):
        """모델(dict: 기호→bool)에서 문장의 참·거짓."""
        op, a = self.op, self.args
        if op == "SYM": return model[a[0]]
        if op == "~": return not a[0].pl_true(model)
        if op == "&": return all(x.pl_true(model) for x in a)
        if op == "|": return any(x.pl_true(model) for x in a)
        if op == "=>": return (not a[0].pl_true(model)) or a[1].pl_true(model)
        if op == "<=>": return a[0].pl_true(model) == a[1].pl_true(model)
        raise ValueError(op)


def Symbol(name): return Expr("SYM", name)
def Iff(a, b): return Expr("<=>", a, b)
def Implies(a, b): return Expr("=>", a, b)
def Not(a): return Expr("~", a)


def And(*xs):
    xs = list(xs)
    if not xs: raise ValueError("And() 인자 없음")
    return xs[0] if len(xs) == 1 else Expr("&", *xs)


def Or(*xs):
    xs = list(xs)
    if not xs: raise ValueError("Or() 인자 없음")
    return xs[0] if len(xs) == 1 else Expr("|", *xs)


# ====================================================================== CNF
def _elim(s):            # ⇔, ⇒ 제거
    op, a = s.op, s.args
    if op == "SYM": return s
    a = [_elim(x) for x in a]
    if op == "=>": return Expr("|", Expr("~", a[0]), a[1])
    if op == "<=>":
        return Expr("&", Expr("|", Expr("~", a[0]), a[1]), Expr("|", Expr("~", a[1]), a[0]))
    return Expr(op, *a)


def _push_not(s):        # 드모르간, 이중부정 → 부정 정규형(NNF)
    op, a = s.op, s.args
    if op == "SYM": return s
    if op == "~":
        t = a[0]
        if t.op == "SYM": return s
        if t.op == "~": return _push_not(t.args[0])
        if t.op == "&": return Expr("|", *[_push_not(Expr("~", x)) for x in t.args])
        if t.op == "|": return Expr("&", *[_push_not(Expr("~", x)) for x in t.args])
    return Expr(op, *[_push_not(x) for x in a])


def _clauses(s):         # NNF → 절 리스트 (∨ 를 ∧ 위로 분배)
    if s.op == "SYM": return [frozenset([s.args[0]])]
    if s.op == "~": return [frozenset(["~" + s.args[0].args[0]])]
    if s.op == "&":
        out = []
        for x in s.args: out += _clauses(x)
        return out
    if s.op == "|":
        acc = [frozenset()]
        for x in s.args:
            acc = [c1 | c2 for c1 in acc for c2 in _clauses(x)]
        return acc
    raise ValueError(s.op)


def negate(lit): return lit[1:] if lit.startswith("~") else "~" + lit
def var(lit): return lit.lstrip("~")


def to_cnf(s):
    """문장 → 절 집합. 항진 절(P ∨ ¬P 포함)은 제거한다."""
    out = set()
    for c in _clauses(_push_not(_elim(s))):
        if not any(negate(l) in c for l in c):
            out.add(c)
    return out


# ============================================================ 관련 절 추출
def relevant_clauses(clauses, query_syms):
    """질의 기호와 (공유 기호를 통해) 연결된 절만 남긴다.
    KB가 충족 가능하고, 나머지 절들이 질의와 기호를 공유하지 않으면
    KB ⊨ α  ⇔  (관련 절) ⊨ α  이므로 건전하다."""
    by_sym = defaultdict(list)
    for c in clauses:
        for l in c: by_sym[var(l)].append(c)
    seen_s, seen_c, stack = set(query_syms), set(), list(query_syms)
    while stack:
        s = stack.pop()
        for c in by_sym.get(s, ()):
            if c in seen_c: continue
            seen_c.add(c)
            for l in c:
                v = var(l)
                if v not in seen_s:
                    seen_s.add(v); stack.append(v)
    return seen_c



# ====================================================== 1) 진리표 모델 검사
def _clause_true(c, model):
    """완전 모델(model: 기호→bool)에서 절 c(리터럴 집합)가 참인가?"""
    return any((model[l[1:]] is False) if l[0] == "~" else model[l] for l in c)


def tt_entails(kb_clauses, alpha, stats=None):
    """[TODO 1] TT-ENTAILS(KB, α)
    KB가 참인 '모든' 모델에서 α도 참이면 True, 아니면 False.

    kb_clauses : 절의 집합 (절 = 'P12', '~W13' 같은 리터럴들의 frozenset)
    alpha      : Expr (alpha.symbols(), alpha.pl_true(model) 사용 가능)
    stats      : dict 또는 None. None이 아니면 다음 값을 갱신할 것
                 stats["models"] += 검사한 (완전) 모델 수
                 stats["symbols_max"] = max(stats["symbols_max"], 기호 수)

    의사코드 (AIMA 그림 7.10)
      symbols ← KB와 α에 나오는 기호 목록
      return TT-CHECK-ALL(KB, α, symbols, {})
      TT-CHECK-ALL(KB, α, symbols, model):
        if symbols가 비었으면:
            if PL-TRUE?(KB, model) then return PL-TRUE?(α, model)
            else return true            # KB가 거짓인 모델은 무관
        P ← FIRST(symbols); rest ← REST(symbols)
        return TT-CHECK-ALL(KB, α, rest, model ∪ {P=true}) and
               TT-CHECK-ALL(KB, α, rest, model ∪ {P=false})
    힌트: KB가 참 ⇔ 모든 절에 대해 _clause_true(c, model)
    """
    raise NotImplementedError("TODO 1: tt_entails")


# =============================================================== 2) DPLL
#  교재 그림 7.17을 작은 함수로 나누었습니다. 위에서부터 차례로 구현하고 test_agent.py로 확인하세요.
#    [TODO 2-1] clause_status     : 부분 모델에서 절의 상태               (필수)
#    [TODO 2-2] dpll              : 조기 종료 + 분기 = 기본 DPLL          (필수)
#    [TODO 2-3] find_pure_symbol  : 순수 기호 휴리스틱                   (가산점)
#    [TODO 2-4] find_unit_clause  : 단위 절 휴리스틱                     (가산점)
#  2-3, 2-4를 구현하지 않아도 (None, None)을 반환하므로 기본 DPLL로 올바르게 동작합니다.

def _lit_value(l, model):
    """부분 모델에서 리터럴 l의 값: True / False / None(미할당)   (제공)
    예) model = {'P12': False}  →  _lit_value('~P12', model) = True,  _lit_value('P21', model) = None"""
    v = model.get(var(l))
    if v is None: return None
    return (not v) if l[0] == "~" else v


def clause_status(c, model):
    """[TODO 2-1] (필수) 부분 모델 model에서 절 c(리터럴의 frozenset)의 상태를 돌려준다.
    반환: ("true", [])        참인 리터럴이 하나라도 있음
          ("false", [])       모든 리터럴이 거짓
          ("undecided", ls)   그 외 — ls = 아직 할당되지 않은 리터럴들의 리스트
    예) c = {'P12', 'P21'},  model = {'P12': False}  →  ("undecided", ['P21'])
        c = {'P12', 'P21'},  model = {'P12': False, 'P21': False}  →  ("false", [])
    힌트: 각 리터럴에 _lit_value(l, model)을 적용해 True / None 을 모은다. (약 8줄)"""
    raise NotImplementedError("TODO 2-1: clause_status")


def find_pure_symbol(symbols, clauses, model):
    """[TODO 2-3] (가산점) 순수 기호 휴리스틱
    아직 참이 되지 않은("undecided") 절들의 미할당 리터럴만 보았을 때,
    한 가지 부호로만 나타나는 미할당 기호 p를 찾아 (p, 값)을 반환한다.
      양(P)으로만 나오면 값 True, 음(~P)으로만 나오면 값 False.  없으면 (None, None)
    예) clauses = [{'A','~B'}, {'~B','C'}, {'~C','A'}], model = {}  →  ('A', True)  (B도 가능: ('B', False))
    힌트: 기호별로 나온 부호의 집합 {True, False}을 dict로 모은다. (약 10줄)"""
    return None, None          # ← 구현하지 않으면 휴리스틱 없이 동작


def find_unit_clause(clauses, model):
    """[TODO 2-4] (가산점) 단위 절 휴리스틱
    clause_status가 ("undecided", [l]) — 즉 미할당 리터럴이 정확히 1개인 절을 찾아
    그 리터럴을 참으로 만드는 (기호, 값)을 반환한다.  없으면 (None, None)
    예) clauses = [{'A','B'}], model = {'A': False}  →  ('B', True)
        clauses = [{'~C'}],    model = {}            →  ('C', False)
    힌트: clause_status를 그대로 이용하면 5줄 정도면 된다."""
    return None, None          # ← 구현하지 않으면 휴리스틱 없이 동작


def dpll(clauses, symbols, model, stats=None, use_pure=True, use_unit=True):
    """[TODO 2-2] (필수) DPLL(clauses, symbols, model)
    부분 모델 model을 확장하여 모든 절을 참으로 만들 수 있으면 True, 없으면 False.
    clauses: 절 리스트, symbols: 정렬된 전체 기호 리스트, model: dict(기호→bool)
    ※ 재귀 호출할 때는 model을 직접 바꾸지 말고 {**model, p: 값} 처럼 새 dict를 넘기세요."""
    if stats is not None: stats["dpll_calls"] += 1          # (제공) 호출 수 기록

    # ① [TODO 2-2] 조기 종료
    #    clause_status로 모든 절의 상태를 구해서
    #    "false"인 절이 하나라도 있으면 return False,  모든 절이 "true"이면 return True
    raise NotImplementedError("TODO 2-2: dpll ① 조기 종료")

    # ② 순수 기호 휴리스틱 (제공 — find_pure_symbol을 구현하면 자동으로 사용됨)
    if use_pure:
        p, v = find_pure_symbol(symbols, clauses, model)
        if p is not None:
            return dpll(clauses, symbols, {**model, p: v}, stats, use_pure, use_unit)
    # ③ 단위 절 휴리스틱 (제공 — find_unit_clause를 구현하면 자동으로 사용됨)
    if use_unit:
        p, v = find_unit_clause(clauses, model)
        if p is not None:
            return dpll(clauses, symbols, {**model, p: v}, stats, use_pure, use_unit)

    # ④ [TODO 2-2] 분기
    #    아직 model에 없는 첫 기호 p를 골라
    #    p=True 로 재귀 호출한 결과 or p=False 로 재귀 호출한 결과 를 반환
    #    (재귀 호출에도 stats, use_pure, use_unit 을 그대로 넘길 것)


def dpll_satisfiable(clauses, stats=None, use_pure=True, use_unit=True):
    """DPLL-SATISFIABLE?(s): 절 집합이 충족 가능하면 True   (제공)"""
    clauses = list(clauses)
    symbols = sorted({var(l) for c in clauses for l in c})
    if stats is not None:
        stats["symbols_max"] = max(stats["symbols_max"], len(symbols))
    return dpll(clauses, symbols, {}, stats, use_pure, use_unit)


def dpll_entails(kb_clauses, alpha, stats=None, use_pure=True, use_unit=True):
    """[TODO 3] KB ⊨ α  ⇔  KB ∧ ¬α 가 충족 불가능 (귀류법)
    힌트: to_cnf(Not(alpha)) 로 ¬α의 절을 얻어 KB 절과 합친 뒤
          dpll_satisfiable(..., stats, use_pure, use_unit) 의 결과를 뒤집는다. (1줄)"""
    raise NotImplementedError("TODO 3: dpll_entails")


# ====================================================================== KB
class PropKB:
    """명제논리 지식베이스.  method = 'tt' | 'dpll',  prune = 관련 절만 사용 여부"""

    def __init__(self, method="dpll", prune=True, use_pure=True, use_unit=True):
        self.method, self.prune = method, prune
        self.use_pure, self.use_unit = use_pure, use_unit
        self.clauses = set()
        self.stats = defaultdict(float)
        self.stats["symbols_max"] = 0

    def tell(self, sentence):
        self.clauses |= to_cnf(sentence)

    def ask(self, query):
        """KB ⊨ query 이면 True."""
        t0 = time.perf_counter()
        kb = relevant_clauses(self.clauses, query.symbols()) if self.prune else self.clauses
        if self.method == "tt":
            r = tt_entails(kb, query, self.stats)
        elif self.method == "dpll":
            r = dpll_entails(kb, query, self.stats, self.use_pure, self.use_unit)
        else:
            raise ValueError(self.method)
        self.stats["asks"] += 1
        self.stats["ask_time"] += time.perf_counter() - t0
        return r

    def __len__(self): return len(self.clauses)

