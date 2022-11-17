import os
import shutil

# TODO: Remove BuildBuddy repo references
OSS_REPO_PATH = os.getenv("BUILDBUDDY_REPO_PATH")
OSS_PREFIX = "external/com_github_buildbuddy_io_buildbuddy/"
INTERNAL_REPO_PATH = os.getenv("BUILDBUDDY_INTERNAL_REPO_PATH")

WORKSPACE_DIRECTORY = os.getenv("BUILD_WORKSPACE_DIRECTORY") or os.getcwd()
DEBUG = os.getenv("BB_GO_FIX_DEBUG") == "1"
