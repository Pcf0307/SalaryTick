from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_REPORT = "测试执行结果.txt"


def build_command(tests_dir: Path, pattern: str, verbosity: int) -> list[str]:
    return [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        str(tests_dir),
        "-p",
        pattern,
        "-v" if verbosity >= 2 else "-q",
    ]


def run_tests(project_root: Path, tests_dir: Path, report_path: Path, pattern: str) -> int:
    started = datetime.now()
    command = build_command(tests_dir, pattern, verbosity=2)

    environment = os.environ.copy()
    existing_pythonpath = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = (
        str(project_root)
        if not existing_pythonpath
        else str(project_root) + os.pathsep + existing_pythonpath
    )

    process = subprocess.run(
        command,
        cwd=project_root,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    finished = datetime.now()
    elapsed = (finished - started).total_seconds()
    status = "通过" if process.returncode == 0 else "失败"
    command_text = subprocess.list2cmdline(command)

    report = [
        "SalaryTick 自动测试报告",
        "=" * 80,
        f"执行状态：{status}",
        f"返回代码：{process.returncode}",
        f"开始时间：{started:%Y-%m-%d %H:%M:%S}",
        f"结束时间：{finished:%Y-%m-%d %H:%M:%S}",
        f"执行耗时：{elapsed:.3f} 秒",
        f"项目目录：{project_root}",
        f"测试目录：{tests_dir}",
        f"文件规则：{pattern}",
        f"执行命令：{command_text}",
        "=" * 80,
        "",
        process.stdout.rstrip(),
        "",
        "=" * 80,
        f"最终结果：{status}",
        "",
    ]
    report_path.write_text("\n".join(report), encoding="utf-8")

    print("\n".join(report))
    print(f"报告文件：{report_path}")
    return process.returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="自动执行项目 tests 目录下的 unittest 测试，并收集结果到 TXT 文件。"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="项目根目录，默认是本脚本所在目录。",
    )
    parser.add_argument(
        "--tests",
        default="tests",
        help="测试目录名称或路径，默认是 tests。",
    )
    parser.add_argument(
        "--pattern",
        default="test_*.py",
        help="测试文件匹配规则，默认是 test_*.py。",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help=f"报告输出路径，默认是项目根目录下的 {DEFAULT_REPORT}。",
    )
    args = parser.parse_args()

    project_root = args.root.expanduser().resolve()
    tests_dir = Path(args.tests).expanduser()
    if not tests_dir.is_absolute():
        tests_dir = project_root / tests_dir
    tests_dir = tests_dir.resolve()
    report_path = args.report.expanduser() if args.report else project_root / DEFAULT_REPORT
    if not report_path.is_absolute():
        report_path = (project_root / report_path).resolve()

    if not project_root.is_dir():
        parser.error(f"项目目录不存在：{project_root}")
    if not tests_dir.is_dir():
        parser.error(f"测试目录不存在：{tests_dir}")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    return run_tests(project_root, tests_dir, report_path, args.pattern)


if __name__ == "__main__":
    raise SystemExit(main())
