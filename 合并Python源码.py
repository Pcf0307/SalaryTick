from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

DEFAULT_OUTPUT = "合并后的Python源码.txt"
EXCLUDED_DIRS = {
    ".git",
    ".github",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "venv",
    ".venv",
    "env",
    ".env",
    "build",
    "dist",
}


def should_include(path: Path, root: Path, output_path: Path, script_path: Path) -> bool:
    if path.resolve() in {output_path.resolve(), script_path.resolve()}:
        return False
    relative = path.relative_to(root)
    return not any(part in EXCLUDED_DIRS for part in relative.parts)


def read_text_safely(path: Path) -> tuple[str, str]:
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return path.read_text(encoding=encoding), encoding
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace"), "utf-8(replace)"


def collect_python_files(root: Path, output_path: Path, script_path: Path) -> list[Path]:
    files = [
        path
        for path in root.rglob("*.py")
        if path.is_file() and should_include(path, root, output_path, script_path)
    ]
    return sorted(files, key=lambda path: path.relative_to(root).as_posix().lower())


def merge_python_files(root: Path, output_path: Path, include_merger: bool = False) -> int:
    script_path = Path(__file__).resolve()
    if include_merger:
        script_path = Path("/__do_not_exclude__")

    files = collect_python_files(root, output_path, script_path)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with output_path.open("w", encoding="utf-8", newline="\n") as target:
        target.write("Python Source Bundle\n")
        target.write("=" * 80 + "\n")
        target.write(f"Root: {root}\n")
        target.write(f"Generated: {timestamp}\n")
        target.write(f"Python files: {len(files)}\n")
        target.write("=" * 80 + "\n\n")

        target.write("FILE INDEX\n")
        target.write("-" * 80 + "\n")
        for index, path in enumerate(files, start=1):
            target.write(f"{index:03d}. {path.relative_to(root).as_posix()}\n")
        target.write("\n")

        for index, path in enumerate(files, start=1):
            relative = path.relative_to(root).as_posix()
            content, encoding = read_text_safely(path)
            line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)

            target.write("=" * 80 + "\n")
            target.write(f"FILE {index:03d}/{len(files):03d}: {relative}\n")
            target.write(f"ENCODING: {encoding}\n")
            target.write(f"LINES: {line_count}\n")
            target.write("=" * 80 + "\n")
            target.write(content)
            if content and not content.endswith("\n"):
                target.write("\n")
            target.write(f"\n# END OF FILE: {relative}\n\n")

    return len(files)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="递归收集当前目录及子目录下的所有 .py 文件，并合并为一个 TXT。"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="扫描根目录。默认：当前目录。",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=f"输出文件。默认：扫描根目录下的 {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--include-merger",
        action="store_true",
        help="将本合并脚本自身也写入输出文件。默认排除。",
    )
    args = parser.parse_args()

    root = args.root.expanduser().resolve()
    if not root.is_dir():
        parser.error(f"扫描根目录不存在或不是目录：{root}")

    output = args.output.expanduser() if args.output else root / DEFAULT_OUTPUT
    if not output.is_absolute():
        output = (Path.cwd() / output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    count = merge_python_files(root, output, args.include_merger)
    print(f"合并完成：{count} 个 Python 文件")
    print(f"输出文件：{output}")


if __name__ == "__main__":
    main()
