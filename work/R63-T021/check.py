#!/usr/bin/env python3
"""Validate R63-T021 metadata and test the reference in an isolated scratch module."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASK_DIR = Path(__file__).resolve().parent
INPUTS = TASK_DIR / "inputs"
BASELINE_TOML = INPUTS / "tests.toml.before"
CONFIG_SNAPSHOT = INPUTS / "config.json"
EXPECTED_TOML_ENTRIES = 29
EXPECTED_INCLUDED = 24
EXPECTED_EXCLUDED = 5
SELECTED = {
    "70d747a1-2e84-4ebc-bc3f-dcbee6a05f6b": "push -> Can push to an empty list",
    "b97d00b6-2fab-435d-ae74-3233dcc13698": "toList LIFO -> Empty linked list to list is empty",
    "eedeb95f-b5cf-431d-8ad6-5854ba6b251c": "toList LIFO -> To list with multiple values",
}


def run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)


def parse_toml(path: Path) -> dict:
    with path.open("rb") as stream:
        return tomllib.load(stream)


def validate_metadata(exercise: Path) -> tuple[int, int, int, int]:
    current_path = exercise / ".meta" / "tests.toml"
    baseline = parse_toml(BASELINE_TOML)
    current = parse_toml(current_path)

    assert len(baseline) == EXPECTED_TOML_ENTRIES, f"baseline entry count is {len(baseline)}, expected {EXPECTED_TOML_ENTRIES}"
    assert len(current) == EXPECTED_TOML_ENTRIES, f"current entry count is {len(current)}, expected {EXPECTED_TOML_ENTRIES}"
    assert set(current) == set(baseline), "canonical UUID set changed"

    for uuid, old_values in baseline.items():
        new_values = current[uuid]
        assert old_values.get("description") == new_values.get("description"), f"description changed for {uuid}"
        assert old_values.get("reimplements") == new_values.get("reimplements"), f"reimplements changed for {uuid}"
        if uuid in SELECTED:
            old_rest = {k: v for k, v in old_values.items() if k not in {"comment", "comments"}}
            new_rest = {k: v for k, v in new_values.items() if k not in {"comment", "comments"}}
            assert old_rest == new_rest, f"non-comment metadata changed for selected UUID {uuid}"
            assert isinstance(new_values.get("comment"), str) and new_values["comment"].strip(), f"missing singular comment for {uuid}"
            assert "comments" not in new_values, f"use singular comment key for {uuid}"
            assert new_values["description"] == SELECTED[uuid], f"unexpected description for {uuid}"
        else:
            assert new_values == old_values, f"unselected metadata changed for {uuid}"

    before_excluded = sum(v.get("include") is False for v in baseline.values())
    after_excluded = sum(v.get("include") is False for v in current.values())
    before_included = len(baseline) - before_excluded
    after_included = len(current) - after_excluded
    assert (before_included, before_excluded) == (EXPECTED_INCLUDED, EXPECTED_EXCLUDED), "unexpected baseline include/exclude counts"
    assert (after_included, after_excluded) == (before_included, before_excluded), "include/exclude counts changed"

    docs = ROOT / "docs" / "maintenance" / "simple-linked-list.md"
    doc_text = docs.read_text(encoding="utf-8")
    for uuid in SELECTED:
        assert uuid in doc_text, f"documentation mapping missing UUID {uuid}"
    return before_included, before_excluded, after_included, after_excluded


def main() -> int:
    actual_log = TASK_DIR / "actual-results.txt"
    versions_log = TASK_DIR / "tool-versions.txt"
    test_log = []
    try:
        exercise = ROOT / "exercises" / "practice" / "simple-linked-list"
        config_path = exercise / ".meta" / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        snapshot_config = json.loads(CONFIG_SNAPSHOT.read_text(encoding="utf-8"))
        assert config == snapshot_config, "exercise config.json differs from the saved input snapshot"

        files = config["files"]
        solution_files = files["solution"]
        example_files = files["example"]
        test_files = files["test"]
        assert len(solution_files) == 1, "expected exactly one learner solution file"
        assert len(example_files) == 1, "expected exactly one reference example file"
        for relative in solution_files + example_files + test_files:
            assert (exercise / relative).is_file(), f"configured exercise file is missing: {relative}"

        before_included, before_excluded, included, excluded = validate_metadata(exercise)
        test_source = "\n".join((exercise / name).read_text(encoding="utf-8") for name in test_files)
        expected_case_count = len(re.findall(r"^\s*description:\s*", test_source, re.MULTILINE))
        assert expected_case_count > 0, "no generated cases found in configured test files"

        py = run([sys.executable, "--version"], ROOT)
        go = run(["go", "version"], ROOT)
        go_env = run(["go", "env", "GOVERSION"], ROOT)
        versions_log.write_text(
            f"Python: {py.stdout.strip() or py.stderr.strip()}\nGo: {go.stdout.strip() or go.stderr.strip()}\nGo GOVERSION: {go_env.stdout.strip()}\n",
            encoding="utf-8",
        )
        assert py.returncode == 0 and go.returncode == 0 and go_env.returncode == 0, "could not determine tool versions"

        with tempfile.TemporaryDirectory(prefix="r63-t021-") as temp_name:
            scratch_root = Path(temp_name)
            scratch_exercise = scratch_root / "simple-linked-list"
            # copytree copies hidden files and directories too, including .meta.
            shutil.copytree(exercise, scratch_exercise)
            reference = scratch_exercise / example_files[0]
            solution = scratch_exercise / solution_files[0]
            shutil.copy2(reference, solution)
            (scratch_exercise / "go.mod").write_text("module r63t021/simplelinkedlist\n\ngo 1.24\n", encoding="utf-8")

            env = os.environ.copy()
            env.setdefault("GOTOOLCHAIN", "auto")
            required = run(["go", "test", "-count=1", "./..."], scratch_exercise, env)
            test_log.append("$ go test -count=1 ./...\n" + required.stdout + required.stderr + f"\nexit code: {required.returncode}\n")
            assert required.returncode == 0, "reference-backed go test command failed; see actual-results.txt"

            counted = run(["go", "test", "-json", "-count=1", "./..."], scratch_exercise, env)
            test_log.append("$ go test -json -count=1 ./...\n" + counted.stdout + counted.stderr + f"\nexit code: {counted.returncode}\n")
            assert counted.returncode == 0, "JSON test-count command failed; see actual-results.txt"
            executed = 0
            for line in counted.stdout.splitlines():
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("Action") == "run" and str(event.get("Test", "")).startswith("TestList/"):
                    executed += 1
            assert executed > 0, "zero TestList cases executed"
            assert executed == expected_case_count, f"executed {executed} cases, expected {expected_case_count} from configured generated tests"

        actual_log.write_text(
            f"PASS: metadata validation\nBefore: {before_included} included, {before_excluded} excluded\nAfter: {included} included, {excluded} excluded\nGenerated cases expected/executed: {expected_case_count}/{executed}\n\n" + "\n".join(test_log),
            encoding="utf-8",
        )
        print(f"PASS: before {before_included}/{before_excluded} and after {included}/{excluded} (included/excluded); {executed} generated cases executed against reference.")
        return 0
    except Exception as exc:
        actual_log.write_text("FAIL: " + str(exc) + "\n\n" + "\n".join(test_log), encoding="utf-8")
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
