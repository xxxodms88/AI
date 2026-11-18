"""
make_submission.py — 공지의 예시 구조대로 제출용 zip을 만든다.

  python tools/make_submission.py --team 3
  → Wumpus_Team3.zip  (빠진 파일이 있으면 경고하고, --force 없이는 만들지 않음)
"""
from __future__ import annotations
import argparse
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ["main.py", "agent.py", "logic.py", "planner.py", "wumpus_env.py", "visualize.py"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--team", required=True, help="팀 번호 또는 이름 (예: 3)")
    ap.add_argument("--force", action="store_true", help="빠진 파일이 있어도 zip 생성")
    ap.add_argument("--skip-tests", action="store_true", help="test_agent.py 실행 생략")
    args = ap.parse_args()

    name = f"Wumpus_Team{args.team}"
    report = f"{name}_Report.pptx"
    team_worlds = [p for p in (ROOT / "worlds").glob("world_*.txt")
                   if p.name not in {"world_fig7_2.txt", "world_breeze_start.txt", "world_shoot.txt"}]

    problems = []
    for f in SOURCES + ["worlds/world_fig7_2.txt", "result_path.png", report]:
        if not (ROOT / f).exists():
            problems.append(f"없음: {f}")
    if not team_worlds:
        problems.append("팀이 설계한 세계 파일이 없음 (worlds/world_team*.txt 등)")

    if not args.skip_tests:
        out = subprocess.run([sys.executable, "test_agent.py"], cwd=ROOT,
                             capture_output=True, text=True).stdout
        last = out.strip().splitlines()[-1] if out.strip() else "(출력 없음)"
        print("test_agent.py →", last)
        if "FAIL" in out or "미구현" in out:
            problems.append("test_agent.py 에 FAIL 또는 미구현 항목이 있음")

    for p in problems:
        print("⚠️ ", p)
    if problems and not args.force:
        print("\n문제를 해결하거나 --force 로 다시 실행하세요.")
        sys.exit(1)

    files = [f for f in SOURCES + [report, "result_path.png"] if (ROOT / f).exists()]
    files += [str(p.relative_to(ROOT)) for p in sorted((ROOT / "worlds").glob("*.txt"))]
    out_zip = ROOT / f"{name}.zip"
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(ROOT / f, f)
    print(f"\n✅ {out_zip.name} 생성 ({len(files)}개 파일)")
    for f in files:
        print("   ", f)


if __name__ == "__main__":
    main()
