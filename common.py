import contextlib
import os
import subprocess
import sys
from typing import List

from config import WORKSPACE_DIRECTORY


def print_fix_details(file_path, message):
    rel_path = trim_prefix(file_path, WORKSPACE_DIRECTORY + "/")
    sys.stdout.write(f"\x1b[32m> {rel_path}:\x1b[m {message}  ✅ fix applied\n")


def sh(command: str, **kwargs):
    return subprocess.run(
        command, shell=True, encoding="utf-8", capture_output=True, **kwargs
    )


def sh_run(command, **kwargs):
    return subprocess.run(command, shell=True, **kwargs)


def shl(command, **kwargs):
    return nonempty_lines(sh(command, **kwargs).stdout)


def nonempty(lines: List[str]) -> List[str]:
    return [line for line in lines if line]


def nonempty_lines(output: str):
    return nonempty((line.strip() for line in output.splitlines()))


def readlines(filepath: str):
    with open(filepath, "r") as f:
        return f.readlines()


def writelines(filepath: str, lines: List[str]):
    with open(filepath, "w") as f:
        return f.writelines(lines)


# TODO: Batch rewrite lines
def rewrite_line(filepath: str, line_number: int, line: str):
    if not line.endswith("\n"):
        line = line + "\n"
    lines = readlines(filepath)
    lines[line_number - 1] = line
    writelines(filepath, lines)


def delete_line(path: str, line_number: int):
    lines = readlines(path)
    lines = lines[: line_number - 1] + lines[line_number:]
    with open(path, "w") as f:
        f.writelines(lines)


def strip_ctrl_seqs(line: str) -> str:
    line = line.replace("\x1b[1A", "")
    line = line.replace("\x1b[K", "")
    line = line.replace("\r", "")
    if "\x1b" in line:
        warn(f"WARNING: Ctrl sequence found in line: {repr(line)}")
    return line


def trim_suffix(val: str, suffix: str):
    if val.endswith(suffix):
        return val[: -len(suffix)]
    return val


def trim_prefix(val: str, prefix: str):
    if val.startswith(prefix):
        return val[len(prefix) :]
    return val


@contextlib.contextmanager
def workdir(path: str):
    start_dir = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(start_dir)


def warn(msg: str):
    sys.stderr.write("\x1b[33mWarning: " + msg + "\x1b[m\n")


def fatal(msg: str):
    sys.stderr.write(msg + "\n")
    sys.exit(1)


COLOR_CODES = {
    "orange": b"33",
}
