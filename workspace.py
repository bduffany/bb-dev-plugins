import os
import re
from typing import TypedDict, Union

from common import readlines
from config import INTERNAL_REPO_PATH, OSS_PREFIX, OSS_REPO_PATH, WORKSPACE_DIRECTORY


class SourceFileInfo(TypedDict):
    workspace_name: str
    workspace_path: str
    workspace_relative_path: str
    realpath: str
    target: str


def guess_package(path: str) -> str:
    pkg = os.path.split(path)[-1].split(".")[0]
    return pkg


def guess_go_target(repo_path: str, relative_file_path: str) -> str:
    build_file_path = os.path.join(
        repo_path, os.path.dirname(relative_file_path), "BUILD"
    )
    basename = os.path.basename(relative_file_path)
    target_name = basename.split(".")[0]

    # TODO: more robust logic here.
    if os.path.exists(build_file_path):
        build_lines = readlines(build_file_path)
        cur_name = ""
        cur_srcs = []
        for line in build_lines:
            try:
                if m := re.search(r"name\s*=\s*(.*?),", line):
                    cur_name = eval(m.group(1))
                if m := re.search(r"srcs\s*=\s*(\[.*\])", line):
                    cur_srcs = eval(m.group(1))
            except:
                continue

            if basename in cur_srcs:
                target_name = cur_name
                break

    return f"//{os.path.dirname(relative_file_path)}:{target_name}"


def get_source_file_info_from_sandbox_path(
    sandbox_file_path,
) -> Union[SourceFileInfo, None]:
    execroot_relative_path = re.sub(".*?execroot/", "", sandbox_file_path)
    (workspace_name, workspace_relative_path) = execroot_relative_path.split(
        "/", maxsplit=1
    )
    if workspace_relative_path.startswith(OSS_PREFIX):
        repo_path = OSS_REPO_PATH
        workspace_name = "buildbuddy"
        workspace_relative_path = workspace_relative_path[len(OSS_PREFIX) :]
    elif workspace_name == "buildbuddy" and not workspace_relative_path.startswith(
        "external/"
    ):
        repo_path = OSS_REPO_PATH
    elif (
        workspace_name == "buildbuddy_internal"
        and not workspace_relative_path.startswith("external/")
    ):
        repo_path = INTERNAL_REPO_PATH
    else:
        return None

    # TODO: handle non-Go srcs
    target = guess_go_target(
        repo_path=repo_path, relative_file_path=workspace_relative_path
    )
    return {
        "workspace_name": workspace_name,
        "workspace_path": repo_path,
        "workspace_relative_path": workspace_relative_path,
        "realpath": os.path.join(repo_path, workspace_relative_path),
        "target": target,
    }


def get_source_file_info(path: str) -> Union[SourceFileInfo, None]:
    if "/execroot/" in path:
        return get_source_file_info_from_sandbox_path(path)
    if path.startswith(OSS_PREFIX):
        repo_path = OSS_REPO_PATH
        workspace_name = "buildbuddy"
        workspace_relative_path = path[len(OSS_PREFIX) :]
    elif WORKSPACE_DIRECTORY.startswith(OSS_REPO_PATH) and os.path.exists(
        os.path.join(OSS_REPO_PATH, path)
    ):
        repo_path = OSS_REPO_PATH
        workspace_name = "buildbuddy"
        workspace_relative_path = path
    elif WORKSPACE_DIRECTORY.startswith(INTERNAL_REPO_PATH) and os.path.exists(
        os.path.join(INTERNAL_REPO_PATH, path)
    ):
        repo_path = INTERNAL_REPO_PATH
        workspace_name = "buildbuddy_internal"
        workspace_relative_path = path
    else:
        return None
    target = guess_go_target(
        repo_path=repo_path, relative_file_path=workspace_relative_path
    )
    return {
        "workspace_name": workspace_name,
        "workspace_path": repo_path,
        "workspace_relative_path": workspace_relative_path,
        "realpath": os.path.join(repo_path, workspace_relative_path),
        "target": target,
    }
