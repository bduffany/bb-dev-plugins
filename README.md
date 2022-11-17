# bduffany/bb-dev-plugins

This repo contains a collection of [`bb`](https://buildbuddy.io/cli)
plugins that make developing in the BuildBuddy codebase a bit easier.

Its current features are:

- **Fix unused imports**: Looks for "unused import" errors in the build
  output, and delete unused imports automatically.

- **Fix missing imports**: Looks for undefined symbol references in the build
  which look like package references, and optimistically
  imports those packages for you. For example, if you write
  `&repb.Action{}` and you get an error in your build like
  `foo.go:12:1: undefined: "repb"`, the plugin will auto-add an import like
  `repb "github.com/buildbuddy-io/buildbuddy/proto/remote_execution"` since we
  most commonly import the remote execution proto as `repb`.

## Installation

The plugins can be installed for your user account in `~/buildbuddy.yaml`
using:

```
bb install --user bduffany/bb-dev-plugins
```

## Pre-requisites

_TODO(bduffany): Remove some of these requirements and make this plugin less specific to buildbuddy development._

- `BUILDBUDDY_REPO_PATH` and `BUILDBUDDY_INTERNAL_REPO_PATH` environment
  variables set in your `~/.bashrc`, like this:

```
export BUILDBUDDY_REPO_PATH=~/bb/buildbuddy
export BUILDBUDDY_INTERNAL_REPO_PATH=~/bb/buildbuddy-internal
```

- Python 3.8 or higher. If you have 3.8 installed but `python3 --version`
  returns an older version, you can alternatively set the
  `BB_PYTHON_BINARY` env var, like `export BB_PYTHON_BINARY=/usr/bin/python3.8`.

- OPTIONAL: To add missing BUILD deps for TypeScript, `buildozer` must be
  available in `$PATH`. (BUILD deps for Go are managed by the
  [go-deps](https://github.com/buildbuddy-io/plugins/tree/main/go-deps#readme)
  plugin)
