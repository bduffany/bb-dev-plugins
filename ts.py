import os
import shutil
from typing import List, TypedDict

from common import print_fix_details, readlines, sh_run, trim_suffix, writelines

CANNOT_FIND_NAME_PATTERN = r"^(.*?):\d+:\d+.*?TS2304: Cannot find name \'(.*?)\'"
MISSING_IMPORT_PATTERN = r"^(.*?):\d+:\d+.*?\[strictDeps\] transitive dependency on bazel-out/[^/]+?/bin/(.*?) not allowed."


def try_fix_import(file_path, imported_file_path):
    if not shutil.which("buildozer"):
        return False

    # imported_file_path is relative to workspace root
    imported_file_package = os.path.dirname(imported_file_path)
    imported_file_target = f"//{imported_file_package}"

    package_to_fix = os.path.dirname(file_path)
    target_to_fix = f"//{package_to_fix}"

    sh_run(f'buildozer "add deps {imported_file_target}" {target_to_fix}')
    print_fix_details(file_path, f"add dep {imported_file_target}")


class TsSymbol(TypedDict):
    name: str
    path: str
    default: bool


# TODO: Discover this list automatically using frequency analysis
TS_SYMBOLS: List[TsSymbol] = [
    {"name": x[0], "path": x[1], "default": x[2]}
    for x in [
        ("router", "app/router/router.tsx", True),
        ("Checkbox", "app/components/checkbox/checkbox.tsx", True),
    ]
]


def resolve_import_path(source_path, import_path) -> str:
    rel_path_parts = []
    cur_dir = os.path.dirname(source_path)
    while cur_dir and not import_path.startswith(cur_dir + "/"):
        rel_path_parts.append("..")
        cur_dir = os.path.dirname(cur_dir)

    if cur_dir:
        rel_path_parts.append(import_path[len(cur_dir + "/") :])
    else:
        rel_path_parts.append(import_path)
    out = "/".join(rel_path_parts)
    out = trim_suffix(out, ".tsx")
    out = trim_suffix(out, ".ts")
    return out


def try_fix_cannot_find_name(file_path, name):
    resolved_symbol = None
    for symbol in TS_SYMBOLS:
        if symbol["name"] == name:
            resolved_symbol = symbol
            break
    if not resolved_symbol:
        return False

    import_path = resolve_import_path(file_path, resolved_symbol["path"])

    lines = readlines(file_path)
    for (i, line) in enumerate(lines):
        if "React" in line:
            # React import comes first.
            continue
        import_line = f'import {name} from "{import_path}";\n'
        out_lines = [*lines[:i], import_line, *lines[i:]]
        writelines(file_path, out_lines)
        print_fix_details(file_path, f"add import '{name}'")
        return True

    return False
