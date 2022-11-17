import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import List, Tuple, Union

from common import (
    delete_line,
    print_fix_details,
    readlines,
    rewrite_line,
    sh_run,
    shl,
    strip_ctrl_seqs,
    warn,
    workdir,
)
from config import INTERNAL_REPO_PATH, OSS_REPO_PATH
from workspace import get_source_file_info

LINE_PATTERN = r"/[^/]*?\.go:\d+:\d+:.*"
MISSING_IMPORT_PATTERN = r'^\s*(.*?\.go): import of "(.*)"'

Lines = List[str]
LineRange = Tuple[int, int]

BLOCK_DELIMITERS = ["()", r"{}", "[]"]


# TODO: build import index only if needed
_PACKAGE_RESOLUTIONS = None


def try_fix_error(line) -> bool:
    line = strip_ctrl_seqs(line)
    m = re.search(r"(.*?\.go):(\d+)", line)
    if not m:
        return False

    file_path = m.group(1)
    source = get_source_file_info(file_path)
    if source is None:
        warn(f"Could not locate source for {file_path} based on line {line}")
        return False
    source_path = source["realpath"]

    line_number = int(m.group(2))

    if "imported and not used" in line:
        delete_line(source_path, line_number)
        print_fix_details(source_path, f"remove unused import")
        return True

    m = re.search(r"undefined:\s+([A-Za-z_]+)$", line)
    if m:
        undef_symbol = m.group(1)
        source_lines = readlines(source["realpath"])
        # Never try to resolve symbols that refer to the current package.
        if undef_symbol == get_package_name(source_lines):
            return False
        # If the symbol is not followed by `.` in the source line referenced by the error,
        # then the symbol is not referring to a package, so do nothing.
        source_line = source_lines[line_number - 1]
        if (undef_symbol + ".") not in source_line:
            return False

        for symbol, import_url in package_resolutions().items():
            if undef_symbol == symbol:
                alias = None
                if not import_url.endswith(f"/{symbol}") and not import_url == symbol:
                    alias = symbol
                return add_import(source["realpath"], import_url, alias=alias)

    if "unexpected { in type declaration" in line:
        lines = readlines(source["realpath"])
        if match := re.search(r"type\s+([^\s]+)\s*{$", lines[line_number - 1]):
            struct_name = match.group(1)
            rewrite_line(
                source["realpath"], line_number, f"type {struct_name} struct {{"
            )
            print_fix_details(
                source["realpath"],
                f"rewrite `type {struct_name} {{` -> `type {struct_name} struct {{`",
            )
            return True

    if "non-declaration statement outside function body" in line:
        lines = readlines(source["realpath"])
        interface_match = re.search(
            r"^(interface|struct)\s+([^\s]+)\s*\{$", lines[line_number - 1]
        )
        if interface_match:
            token = interface_match.group(1)
            name = interface_match.group(2)
            rewrite_line(source["realpath"], line_number, f"type {name} {token} {{")
            print_fix_details(
                source["realpath"], f"rewrite `{token} {name}` -> `type {name} {token}`"
            )
            return True

    return False


def try_fix_import(file_path, import_url) -> bool:
    source = get_source_file_info(file_path)
    if source is None:
        warn(f"Could not determine source info for {file_path}")
        return False

    parent_dir_path = os.path.dirname(source["workspace_relative_path"])
    sh_run(
        f'cd {source["workspace_path"]} && bazel run //:gazelle -- {parent_dir_path}'
    )
    print_fix_details(file_path, "gazelle")


def package_resolutions():
    global _PACKAGE_RESOLUTIONS
    if _PACKAGE_RESOLUTIONS is None:
        _PACKAGE_RESOLUTIONS = build_import_index()
    return _PACKAGE_RESOLUTIONS


def add_import(file_path, url, alias=None) -> bool:
    with open(file_path, "r") as f:
        lines = f.readlines()
    go_imports = get_imports(lines)
    if go_imports is None:
        package_line_index = get_package_line_index(lines)
        if package_line_index is None:
            return False
        imports = [GoImport(url, alias, None)]
        lines[package_line_index + 1 : package_line_index + 1] = [
            "\n"
        ] + render_sorted_imports(imports)
    else:
        imports = go_imports.imports
        imports.append(GoImport(url, alias, None))
        start, end = go_imports.line_range
        lines[start:end] = render_sorted_imports(imports)

    with open(file_path, "w") as f:
        f.writelines(lines)
    print_fix_details(file_path, f'add import "{url}"')
    return True


@dataclass
class GoImport:
    url: str
    alias: Union[str, None]
    trailing_comment: Union[str, None]

    def ref_token(self) -> Union[str, None]:
        if self.alias == "_":
            return None
        if self.alias is not None:
            return self.alias
        return self.url.split("/")[-1]


def _go_import_sort_key(go_import: GoImport) -> str:
    if go_import.alias is not None:
        return go_import.alias
    return go_import.url


@dataclass
class ImportSection:
    line_range: LineRange
    imports: List[GoImport]


def get_package_line_index(lines: List[str]) -> Union[int, None]:
    for (i, line) in enumerate(lines):
        if line.startswith("package "):
            return i
    return None


def get_imports(lines: List[str]) -> Union[ImportSection, None]:
    import_block = find_block(lines, r"^import\s+\(")
    if import_block is None:
        return None

    imports = []
    start, end = import_block
    for line in lines[start + 1 : end - 1]:
        go_import = parse_import(line)
        if go_import:
            imports.append(go_import)
    return ImportSection(line_range=(start, end), imports=imports)


def get_package_name(lines: List[str]) -> Union[str, None]:
    if not lines:
        return None
    if m := re.match(r"^package\s+([A-Za-z0-9_]+)$", lines[0]):
        return m.group(1)
    return None


def render_sorted_imports(imports: List[GoImport]) -> List[str]:
    standard = []
    aliased = []
    urls = []

    for imp in imports:
        if imp.alias:
            aliased.append(imp)
        elif "." not in imp.url:
            standard.append(imp)
        else:
            urls.append(imp)
    sections = []
    for lst in (standard, urls, aliased):
        section = ""
        lst.sort(key=_go_import_sort_key)
        for imp in lst:
            line = "\t"
            if imp.alias:
                line += imp.alias + " "
            line += f'"{imp.url}"'
            if imp.trailing_comment:
                line += " //" + imp.trailing_comment
            line += "\n"
            section += line
        if section:
            sections.append(section)

    return (
        [
            "import (\n",
            "\n".join(sections),
            ")\n",
        ]
        if sections
        else []
    )


def parse_import(line: str) -> Union[GoImport, None]:
    line = line.strip()
    line = re.sub(r"\s+", " ", line)
    if not line or line.startswith("//"):
        return None
    tokens = line.split()
    alias_token = None
    trailing_comment = None
    if len(tokens) == 1:
        url_token = tokens[0]
    else:
        alias_token = tokens[0]
        url_token = tokens[1]
        if len(tokens) > 2 and tokens[2].startswith("//"):
            comment_parts = line.split("//")
            trailing_comment = "//".join(comment_parts[1:])
    if not (url_token[0] == '"' and url_token[-1] == '"'):
        return None
    return GoImport(
        url=url_token[1:-1], alias=alias_token, trailing_comment=trailing_comment
    )


def find_block(lines: Lines, start_pattern: str) -> Union[LineRange, None]:
    delims = None
    for (delim_start, delim_end) in BLOCK_DELIMITERS:
        if delim_start in start_pattern:
            delims = (delim_start, delim_end)
    if delims is None:
        raise ValueError("start_pattern is missing opening delimiter")
    delim_start, delim_end = delims

    start = None
    for i, line in enumerate(lines):
        if start is not None:
            if delim_end in line:
                return (start, i + 1)
        else:
            if re.search(start_pattern, line):
                start = i
    return None


def line_matches(pattern, lines: Lines):
    out = []
    for line in lines:
        if m := re.search(pattern, line):
            out.append(m)
    return out


PATHS_TO_INDEX = [OSS_REPO_PATH, INTERNAL_REPO_PATH]

LIST_FILES_COMMAND = "git ls-files --exclude-standard --cached --others"


def find_all_imports_by_go_reference():
    all_imports: List[GoImport] = []
    for path in shl(LIST_FILES_COMMAND + r" | grep -E '\.go$'"):
        lines = readlines(path)
        if go_imports := get_imports(lines):
            all_imports.extend(go_imports.imports)
    return all_imports


def find_all_imports_by_BUILD_declaration():
    all_imports: List[GoImport] = []
    for path in shl(LIST_FILES_COMMAND + r" | grep BUILD"):
        if not (path == "BUILD" or path.endswith("/BUILD")):
            continue
        lines = readlines(path)
        for m in line_matches(r'importpath[\s]*?=[\s]*?"(.*?)"', lines):
            all_imports.append(
                GoImport(url=m.group(1), alias=None, trailing_comment=None)
            )
    return all_imports


def most_common_import_urls_by_ref_token(all_imports: List[GoImport]):
    url_count_by_ref_token = defaultdict(Counter)
    for go_import in all_imports:
        ref_token = go_import.ref_token()
        if not ref_token:
            # Imported as "_"; ignore.
            continue
        url_count_by_ref_token[ref_token][go_import.url] += 1

    urls_by_ref_token = {}
    for ref_token, url_count in url_count_by_ref_token.items():
        urls_by_ref_token[ref_token] = url_count.most_common()[0][0]

    return urls_by_ref_token


def build_import_index():
    all_imports: List[GoImport] = []
    for path in PATHS_TO_INDEX:
        with workdir(path):
            all_imports.extend(find_all_imports_by_go_reference())
            all_imports.extend(find_all_imports_by_BUILD_declaration())
    return most_common_import_urls_by_ref_token(all_imports)
