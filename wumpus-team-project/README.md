# 🧭 웜퍼스 세계 논리 에이전트 — 팀프로젝트

인공지능 입문 팀프로젝트. 명제논리(TT·DPLL)와 A* 경로 계획으로 웜퍼스 세계를 탐험하는 하이브리드 논리 에이전트를 구현합니다.
📒 노션: [팀프로젝트 페이지](https://app.notion.com/p/41b5fd89719d81b4b6cffcef0f016926) (작업 보드 · 일정 · 회의록) · 저장소 사본: [`docs/NOTION_PROJECT.md`](docs/NOTION_PROJECT.md)

(기본 제공 코드 설명은 [`STARTER_README.md`](STARTER_README.md) 참고)

> ⏰ **제출 마감: 2026-11-27(금) 23:00** · LMS "Wumpus World Agent Team Project" · `Wumpus_TeamN.zip`
> 과제 요구사항 요약: [`docs/ASSIGNMENT.md`](docs/ASSIGNMENT.md)

## 👥 팀원 · 역할 (4명, 공지의 권장 분담 기준)

| 역할 | 이름 | GitHub | 담당 |
|---|---|---|---|
| 논리 | | @ | TODO 1 · 2-1~2-4 · 3 · 5 (KB 기호·규칙, TELL, TT-ENTAILS, DPLL) |
| 탐색·에이전트 | | @ | TODO 4 · 6 · 7 (A*, ASK, 탐험·사격·귀환) |
| 실험·시각화 | | @ | 1,000개 실험, 그래프, `result_path.png`, 팀 세계 파일 |
| 문서 | | @ | PPT(20쪽 이상), 회의록, 카톡 캡처, zip 제출 |

## 🗓️ 일정

| 마감 | 목표 |
|---|---|
| 11/18(수) | 킥오프 대면 회의(단체 사진), 카톡방 개설 |
| 11/20(금) | TODO 1 · 2-1 · 2-2 · 3 · 4 |
| 11/22(일) | TODO 5 · 6 · 7② → `test_agent.py` 필수 7개 PASS |
| 11/24(화) | 가산점 2-3 · 2-4, 사격 7③, 팀 세계 파일, 1,000개 실험 · 그래프 |
| 11/26(목) | PPT 완성, 회의록 · 카톡 캡처 정리 |
| 11/27(금) | `python tools/make_submission.py` → LMS 제출 |

## ✅ 진행 현황

| TODO | 파일 | 내용 | 구분 | 상태 |
|---|---|---|---|---|
| 1 | `logic.py` | `tt_entails` 진리표 모델 검사 (그림 7.10) | 필수 | ⬜ |
| 2-1 | `logic.py` | `clause_status` | 필수 | ⬜ |
| 2-2 | `logic.py` | `dpll` 조기 종료 + 분기 (그림 7.17) | 필수 | ⬜ |
| 2-3 | `logic.py` | `find_pure_symbol` 순수 기호 | 가산점 | ⬜ |
| 2-4 | `logic.py` | `find_unit_clause` 단위 절 | 가산점 | ⬜ |
| 3 | `logic.py` | `dpll_entails` (귀류법) | 필수 | ⬜ |
| 4 | `planner.py` | `astar` A* 탐색 | 필수 | ⬜ |
| 5 | `agent.py` | `tell_percept` 지각 → TELL | 필수 | ⬜ |
| 6 | `agent.py` | `update_knowledge` 안전 칸 ASK | 필수 | ⬜ |
| 7 | `agent.py` | `choose_plan` ② 안전 칸 이동(필수) · ③ 사격(선택) | 필수/선택 | ⬜ |

의존 관계: **1 → 3**, **2-1 → 2-2 → 3**, **4**는 독립, **5~7**은 1~4가 끝나야 전체 테스트 가능.
→ 1·2·4를 병렬로 먼저 진행하고, 5~7은 그동안 설계부터 시작하는 것을 권장합니다.

## 🚀 시작하기

```bash
cd wumpus-team-project
pip install matplotlib
python test_agent.py            # 필수 7개 PASS + 가산점 2개 (+)
```

실행 예:

```bash
python main.py --world worlds/world_fig7_2.txt --verbose     # 단일 세계 + result_path.png
python main.py --random 1000 --engine dpll --policy safe      # 무작위 1000개 통계
python main.py --random 1000 --agent random                   # 기준선
```

## 🧪 실험 계획 (보고서용)

| 실험 | 명령 | 비교 지표 |
|---|---|---|
| TT vs DPLL | `--engine tt` / `--engine dpll` | ASK 1회 평균 시간, 모델 수 |
| 가지치기 효과 | 기본 / `--no-prune` | ASK 시간, 기호 수 |
| 휴리스틱 효과 | 2-3·2-4 구현 전/후 | DPLL 호출 수 |
| 정책 비교 | `--policy safe` / `--policy risk` | 성공률, 사망률, 평균 점수 |
| 기준선 | `--agent random` | 성공률, 평균 점수 |

## 📦 제출

```bash
python tools/make_submission.py --team 3     # → Wumpus_Team3.zip
```

PPT(`Wumpus_Team3_Report.pptx`)와 `result_path.png`를 이 폴더에 둔 뒤 실행하면, 공지의 예시 구조대로 zip을 만들고 빠진 파일을 알려 줍니다.

## 🤝 협업 규칙

[`CONTRIBUTING.md`](CONTRIBUTING.md) 참고 — 브랜치 이름, 커밋 메시지, PR 규칙.
