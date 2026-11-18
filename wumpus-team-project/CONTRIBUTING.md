# 협업 규칙

## 1. 브랜치

- `main` : 항상 `python test_agent.py`가 깨지지 않는 상태 유지. 직접 push 금지.
- 작업 브랜치: `todo<번호>-<짧은설명>`

| 예 | 작업 |
|---|---|
| `todo1-tt-entails` | TODO 1 |
| `todo2-dpll` | TODO 2-1, 2-2 |
| `todo2-heuristics` | TODO 2-3, 2-4 (가산점) |
| `todo4-astar` | TODO 4 |
| `todo5-7-agent` | TODO 5~7 |
| `exp-<이름>` | 실험 스크립트 · 결과 |
| `docs-<이름>` | 보고서 · 발표 자료 |

```bash
git checkout main && git pull
git checkout -b todo4-astar
# ... 작업 ...
git add planner.py
git commit -m "[TODO4] A* 우선순위 큐와 경로 역추적 구현"
git push -u origin todo4-astar
```

## 2. 커밋 메시지

`[TODO번호] 무엇을 했는지` 형식, 한국어 OK.

```
[TODO1] tt_entails 재귀 열거 구현
[TODO2-2] dpll 분기 단계 추가
[EXP] TT vs DPLL 1000개 세계 실험 결과
[DOCS] 보고서 3장 초안
[FIX] tell_percept 냄새 규칙에서 자기 칸 누락 수정
```

## 3. Pull Request

1. PR 본문에 `python test_agent.py` 실행 결과를 붙여 넣는다.
2. 팀원 **1명 이상** 리뷰 후 merge.
3. merge 후 README의 「진행 현황」 표와 노션 작업 보드 상태를 `완료`로 바꾼다.

## 4. 지켜야 할 것

- `wumpus_env.py`는 **수정 금지** (과제 규칙).
- `result_path.png`, `__pycache__/` 등은 커밋하지 않는다 (`.gitignore`에 등록됨).
- 새 세계 파일은 `worlds/` 에 추가하고, 파일 맨 위 주석에 어떤 상황을 시험하는지 적는다.
