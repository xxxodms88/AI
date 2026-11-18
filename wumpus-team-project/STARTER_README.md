# 웜퍼스 세계 논리 에이전트 — 기본 제공 코드 (Starter Code)

인공지능 입문 팀프로젝트용 기본 코드입니다. Python 3.9 이상, 외부 라이브러리는 `matplotlib`만 사용합니다.

```
pip install matplotlib
```

## 파일 구성

| 파일 | 내용 | 수정 |
|---|---|---|
| `wumpus_env.py` | 웜퍼스 세계 환경 (PEAS, 지각·동작·점수, 세계 파일 읽기, 무작위 생성) | **수정 금지** |
| `logic.py` | 명제논리 문장(Expr), CNF 변환, 관련 절 추출, PropKB(TELL/ASK) | TODO 1~3 (2-3, 2-4는 가산점) |
| `planner.py` | 안전한 칸만 지나는 경로 계획 (A*) | TODO 4 |
| `agent.py` | 하이브리드 논리 에이전트, 무작위 에이전트(기준선) | TODO 5~7 |
| `visualize.py` | 결과 시각화 (`result_path.png`) | 자유 |
| `main.py` | 실행 스크립트 (단일 세계 / 무작위 N개 실험) | 자유 |
| `test_agent.py` | 자가 점검 테스트 | – |
| `worlds/*.txt` | 샘플 세계 파일 | 추가 가능 |

## 구현할 부분 (TODO)

1. `logic.tt_entails` — 진리표 열거 모델 검사 (교재 그림 7.10)
2. DPLL (교재 그림 7.17) — 작은 함수로 나누어 구현
   - 2-1 `logic.clause_status` — 부분 모델에서 절의 상태 (필수)
   - 2-2 `logic.dpll` — 조기 종료 + 분기 = 기본 DPLL (필수)
   - 2-3 `logic.find_pure_symbol` — 순수 기호 휴리스틱 (**가산점**)
   - 2-4 `logic.find_unit_clause` — 단위 절 휴리스틱 (**가산점**)
   - 2-3, 2-4를 구현하지 않아도 `(None, None)`을 반환하므로 기본 DPLL로 올바르게 동작합니다.
3. `logic.dpll_entails` — KB ⊨ α ⇔ KB ∧ ¬α 충족 불가능
4. `planner.astar` — A* (상태 = (x, y, 방향), 휴리스틱 = 맨해튼 거리)
5. `agent.tell_percept` — 지각을 명제논리 문장으로 TELL
6. `agent.update_knowledge` — 각 칸의 안전 여부를 ASK
7. `agent.choose_plan` ②(필수)·③(선택: 사격)

각 TODO가 끝날 때마다 다음을 실행해 확인하세요. 필수 7개가 PASS이면 완료이고, 가산점 2개는 `(+)`로 표시됩니다.

```
python test_agent.py
```

## 실행 예

```
python main.py --world worlds/world_fig7_2.txt --verbose          # 단일 세계 + result_path.png
python main.py --world worlds/world_fig7_2.txt --engine tt         # 진리표 엔진
python main.py --random 1000 --engine dpll --policy safe           # 무작위 세계 1000개 통계
python main.py --random 1000 --agent random                        # 기준선(무작위 에이전트)
```

## 세계 파일 형식 (4×4)

첫 줄이 맨 위 행(y = 4), 마지막 줄이 맨 아래 행(y = 1)입니다. 에이전트는 항상 [1,1]에서 동쪽을 보고 시작합니다.

```
. . . P        .  빈 칸     P  구덩이
W G P .        W  웜퍼스    G  금
. . . .        한 칸에 여러 개면 붙여 씀 (예: WG)
. . P .
```
