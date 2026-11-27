# Word Count test generation

## Purpose

This document explains how the Word Count exercise's generated Go tests are produced and verified.

## Inputs

- `exercises/practice/word-count/.meta/gen.go` — exercise-specific generator and `countWords` test template.
- `exercises/practice/word-count/.meta/tests.toml` — UUID-based inclusion and exclusion settings.
- `exercises/practice/word-count/.meta/config.json` — exercise solution and test file mapping.
- `exercises/practice/word-count/.meta/example.go` — reference implementation used for verification.
- `gen/gen.go` — shared generator that loads canonical data and writes generated files.
- `gen/toml.go` — reads excluded UUIDs from `tests.toml`.
- `gen/filter.go` — filters canonical test cases using those UUIDs.
- `gotools/config.json` — Go tool configuration used by the generator.
- Canonical data — `exercism/problem-specifications` at `exercises/word-count/canonical-data.json`.

## Generation command

Run from the repository root:

    GO111MODULE=off go run exercises/practice/word-count/.meta/gen.go -github_token="$(gh auth token)"

The generator first checks for a local `problem-specifications` repository alongside the Go repository. If the canonical JSON is not available there, it downloads the data from Exercism's problem-specifications repository. The GitHub token is used when retrieving the latest canonical-data commit information.

## Generation flow and output mapping

1. The generator loads `canonical-data.json`.
2. `gen/toml.go` reads `exercises/practice/word-count/.meta/tests.toml` and identifies excluded UUIDs.
3. `gen/filter.go` removes excluded cases while retaining the canonical test descriptions and data.
4. The exercise generator in `.meta/gen.go` selects the `countWords` property and maps its cases into the Go `testCase` structure.
5. The template in `.meta/gen.go` renders the test cases into `exercises/practice/word-count/cases_test.go`.
6. The shared generator formats the generated Go file.

The current `tests.toml` contains 15 UUID entries: 14 included and 1 excluded. Therefore, `cases_test.go` contains 14 generated test cases.

## Verification

Run:

    python3 tools/course_checks/r63-t022.py

The check:
- Copies the exercise and shared generator dependencies into temporary directories.
- Runs the generator independently in two copies.
- Compares both generated files, ignoring only the generated `// Commit:` line.
- Compares the generated output with the committed `cases_test.go`.
- Checks that exactly 14 cases were generated.
- Runs the generated tests against `.meta/example.go` in the temporary copy.
- Leaves the original exercise files unchanged.

Evidence is saved under `work/R63-T022/`, including the input snapshots, expected and actual generated files, tool versions, and check output.
