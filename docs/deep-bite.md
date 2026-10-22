# Deep Bite (0.4)

Deep Bite adds eight ecosystem manifests and provider signals to the deterministic pipeline.
It is development functionality, not a release announcement.

The optional tree-sitter syntax index this milestone also planned (declarations, a lexical call
graph and the first `code` cards) was postponed on 2026-10-22: native parsers reading hostile
prey, ten more packages to keep in step and digests that differ by environment outweighed what
it added. It comes back when a real evidence gap asks for it; until then `code` is a deferred
category and the runtime dependency is PyYAML alone.

## Install and use

The CLI depends only on PyYAML.

```text
uv run crab catch owner/repo --shallow --issues 100 --discussions 25 --reviews 100 --runs 10
uv run crab digest owner/repo --maw . --depth deep
uv run crab compare owner/repo --maw .
uv run crab eat https://gitlab.com/group/project --deterministic --maw . --allow-unknown-size
```

No dependency is installed inside a prey clone. `--discussions`, `--reviews` and `--runs`
are opt-in counts (0..3000) on catch, digest, compare and eat. A digest with explicit acquisition
counts refreshes those channels even when the clone already exists. Discussions require GitHub
authentication. Review prose stays in untrusted JSON; Markdown carries counts and paths only.

## Ecosystems and providers

Dependency facts cover Python, npm, .NET, Go, Rust, Ruby, JVM and PHP. Maven namespaces,
local properties and dependency management are read statically. Parent POMs are not fetched.
Gradle literal coordinates are read, with unresolved catalogs/interpolation counted explicitly.
Composer distinguishes platform requirements from packages. Rust records workspace dependency
references and target-specific requirements; an inherited workspace version is not guessed or
called pinned. Go reads require directives, never replace/exclude blocks. Ruby uses the existing
Gemfile/gemspec/lock enrichment. No package manager is launched.

GitHub shorthand remains `owner/repo`. GitLab.com accepts HTTPS and SSH URLs with nested
namespaces. Its cache uses `gitlab/`, separate from `github/`; evidence URLs use `/-/blob/`.
`GITLAB_TOKEN` is optional for public reads and is scoped to GitLab in process-local Git headers.
Ownership trust is forge-qualified (`gitlab.com/group`) so equal account names on different
forges cannot bypass licensing. GitLab supports repository/language metadata, issues, merge
request reviews, pipelines and independent wikis. GitHub Discussions have no GitLab equivalent
in this protocol and report unsupported. GitLab review threads and pipeline jobs can require a
`GITLAB_TOKEN` with read_api permission even when repository metadata and Git objects are public.
Self-hosted instances and GitLab maw publication are
outside this fetch adapter; serving explicitly refuses them instead of sending a malformed gh
command. Analysis and dry-run meals remain available.

GitLab often withholds repository size from anonymous clients. Sniff reports unknown; Feeder
refuses its size preflight unless `--allow-unknown-size` is explicit. Known size remains a
preflight, not a hard download quota ([#236](https://github.com/drevendev/HungryCrab/issues/236)).

## CI reliability evidence

`signals.json` keeps channel samples and provenance. Run statistics include failures, median
durations and jobs that failed in the previous attempt and succeeded on rerun. GitHub duration
is the sum of job seconds, not parallel wall time. GitLab duration is provider pipeline time.
Each sample records truncation; acquisition failures fail the requested command.

A job retry does not prove a flaky test. Test-level counts require JUnit's explicit
`flakyFailure`/`flakyError` markers, with no final failure, in named JUnit/test-results/Surefire
artifacts. Archives are parsed in memory, never extracted, with compressed/uncompressed/XML and
case limits; DTDs and entities are refused, including UTF-16 encodings. Archive reads use gh's
authenticated redirect handling and require actions:read. Clients without it report unavailable
test-report coverage. Missing reports yield an unknown flaky count, not zero. Logs, failure
prose and arbitrary artifact programs never become digest Markdown.

## Measured quality

The human B1 corpus is unchanged. A separate synthetic pressure pair produces more than fifty
candidates, so top-30 shows ranking as well as rule activation. Its generic priorities come
from prior human acceptance, not a new invented usefulness golden set. It reports rather than
gates: with the default scoring four of them rank 31-35, and the defaults are not tuned to its
keys. An intentionally broken scoring configuration must miss them. Real human labeling of a larger corpus remains part
of [#200](https://github.com/drevendev/HungryCrab/issues/200).

The [B2 operator guide](../benchmarks/README.md) describes the full frozen experiment pipeline.
Synthetic transcript tests validate that pipeline, not model quality or cost. The first live
sweep and human audit are [#250](https://github.com/drevendev/HungryCrab/issues/250), under the
existing release-evidence gate [#224](https://github.com/drevendev/HungryCrab/issues/224).
