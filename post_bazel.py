#!/usr/bin/env python3

import os
import re
import sys
from typing import List

import go
import ts
from config import DEBUG

ANSI_ESCAPE_PATTERN = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


class Fix:
    def __init__(self, func, args):
        self.func = func
        self.args = args

    def __call__(self):
        return self.func(*self.args)


def is_build_failed_line(line):
    if re.search(
        r"(ERROR|INFO|FAILED):.*Build (completed|did NOT complete) successfully", line
    ):
        return True
    if re.search(r"ERROR:.*Build failed. Not running target", line):
        return True
    if re.search(r"Executed \d+ out of \d+ tests?:.*?fails? to build", line):
        return True
    return False


def plaintext(text):
    line = re.sub(ANSI_ESCAPE_PATTERN, "", text)
    line = re.sub(r"\r", "", text)
    return line


def main():
    os.umask(0)

    fixes_to_apply: List[Fix] = []

    bazel_logs_path = sys.argv[1]
    with open(bazel_logs_path, "r") as f:
        lines = f.readlines()

    is_build_failed = any((is_build_failed_line(plaintext(line)) for line in lines))
    if not is_build_failed:
        return

    for line in lines:
        line = plaintext(line)

        # TODO: encapsulate line-matching logic into fixes themselves
        match = re.search(go.LINE_PATTERN, line)
        if match:
            fixes_to_apply.append(Fix(go.try_fix_error, (line,)))

        # Disabling Gazelle for now (this is handled by the go-deps plugin)
        # match = re.search(go.MISSING_IMPORT_PATTERN, line)
        # if match:
        #     fixes_to_apply.append(
        #         Fix(go.try_fix_import, (match.group(1), match.group(2)))
        #     )

        match = re.search(ts.MISSING_IMPORT_PATTERN, line)
        if match:
            fixes_to_apply.append(
                Fix(ts.try_fix_import, (match.group(1), match.group(2)))
            )

        match = re.search(ts.CANNOT_FIND_NAME_PATTERN, line)
        if match:
            fixes_to_apply.append(
                Fix(ts.fix_cannot_find_name, (match.group(1), match.group(2)))
            )

    if not fixes_to_apply:
        return

    if DEBUG:
        for fix in fixes_to_apply:
            print(f"- {fix.func.__name__}{repr(fix.args)}")

    fixed = False
    for fix in fixes_to_apply:
        fixed = fix()
        if fixed is None or fixed == True:
            # Only apply at most one fix at a time. Otherwise source
            # files get too messed up.
            # TODO: Improve logic so that multiple fixes can be applied at once.
            break

    # TODO: print the fix here, instead of in fixes themselves


if __name__ == "__main__":
    main()
