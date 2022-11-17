#!/usr/bin/env bash
set -e

function fail() {
  echo -e "\x1b[33mWarning: $1; some automatic fixes will be disabled" >&2
  exit
}

if ! [[ "$(which python3)" ]]; then
  fail "python3 not found in \$PATH (version 3.9 or greater is required)"
fi
function version() {
  printf '%05d' ${1//./ }
}
: "${BB_PYTHON_BINARY:=python3}"
py_version=$("$BB_PYTHON_BINARY" --version | awk '{print $2}')
# TODO: work with earlier Python versions?
required_py_version="3.8.0"
if [[ "$(version "$py_version")" < "$(version "$required_py_version")" ]]; then
  fail "python3 version $py_version is less than minimum required version $required_py_version"
fi

exec python3 ./post_bazel.py "$@"
