import io

import go

MULTILINE_IMPORT = """package test

import (
    "context"
)
"""


def test_grok():
    block = go.find_block(MULTILINE_IMPORT.split("\n"), "import \\(")
    assert block == (2, 5)


def test_go_imports():
    imports = go.get_imports(MULTILINE_IMPORT.split("\n"))
    assert imports == go.ImportSection(
        line_range=(2, 5), imports=[go.GoImport("context", None, None)]
    )


BADLY_SORTED_IMPORTS = """package runner

import (
	"time"
	"github.com/buildbuddy-io/buildbuddy-internal/enterprise/server/remote_execution/workspace"

	"github.com/buildbuddy-io/buildbuddy/server/interfaces"
	"sync"

	aclpb "github.com/buildbuddy-io/buildbuddy/proto/acl"

	_ "google.golang.org/grpc/encoding/gzip" // imported for side effects; DO NOT REMOVE.
)
"""

CORRECT_IMPORTS = """import (
\t"sync"
\t"time"

\t"github.com/buildbuddy-io/buildbuddy-internal/enterprise/server/remote_execution/workspace"
\t"github.com/buildbuddy-io/buildbuddy/server/interfaces"

\t_ "google.golang.org/grpc/encoding/gzip" // imported for side effects; DO NOT REMOVE.
\taclpb "github.com/buildbuddy-io/buildbuddy/proto/acl"
)
"""


def test_render_go_imports():
    import_section = go.get_imports(BADLY_SORTED_IMPORTS.split("\n"))
    rendered = go.render_sorted_imports(import_section.imports)

    assert "".join(rendered) == CORRECT_IMPORTS
