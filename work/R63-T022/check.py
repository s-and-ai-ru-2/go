import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXERCISE = ROOT / "exercises/practice/word-count"
EVIDENCE = ROOT / "work/R63-T022"
CONFIG = EXERCISE / ".meta/config.json"


def run(command, cwd, env=None):
    result = subprocess.run(
        command, cwd=cwd, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    if result.returncode:
        raise RuntimeError(result.stdout)
    return result.stdout


def normalized(path):
    return re.sub(r"(?m)^// Commit:.*\n", "", path.read_text())


def make_copy(parent, name):
    destination = parent / name
    destination.mkdir()
    shutil.copytree(EXERCISE, destination / "exercises/practice/word-count")
    shutil.copytree(ROOT / "gen", destination / "gen")
    if (ROOT / "gotools").exists():
        shutil.copytree(ROOT / "gotools", destination / "gotools")
    return destination


def main():
    config = json.loads(CONFIG.read_text())
    solution = config["files"]["solution"][0]

    inputs = EVIDENCE / "inputs"
    expected_dir = EVIDENCE / "expected"
    actual_dir = EVIDENCE / "actual"

    for folder in (inputs, expected_dir, actual_dir):
        folder.mkdir(parents=True, exist_ok=True)

    input_files = [
        "exercises/practice/word-count/.meta/config.json",
        "exercises/practice/word-count/.meta/tests.toml",
        "exercises/practice/word-count/.meta/gen.go",
        "exercises/practice/word-count/.meta/example.go",
        "exercises/practice/word-count/.docs/instructions.md",
    ]

    for relative in input_files:
        source = ROOT / relative
        destination = inputs / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    for folder in ("gen", "gotools"):
        source = ROOT / folder
        if source.exists():
            destination = inputs / folder
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(source, destination)

    tool_versions = (
        run(["go", "version"], ROOT)
        + run(["python3", "--version"], ROOT)
        + run(["gh", "--version"], ROOT).splitlines()[0]
        + "\n"
        + "Platform: " + sys.platform + "\n"
    )
    (EVIDENCE / "tool-versions.txt").write_text(tool_versions)

    token = os.environ.get("GH_TOKEN", "")
    if not token:
        try:
            token = run(["gh", "auth", "token"], ROOT).strip()
        except (FileNotFoundError, RuntimeError):
            pass

    log = []
    checked_in = EXERCISE / "cases_test.go"
    shutil.copy2(checked_in, expected_dir / "cases_test.go")

    with tempfile.TemporaryDirectory(prefix="r63-t022-") as temporary:
        copies = []

        for name in ("first", "second"):
            copy = make_copy(Path(temporary), name)
            env = os.environ.copy()
            env["GO111MODULE"] = "off"
            generator = "exercises/practice/word-count/.meta/gen.go"

            output = run(
                ["go", "run", generator, f"-github_token={token}"],
                copy, env
            )
            log.append(f"GENERATION: {name}\n{output}")

            cases = copy / "exercises/practice/word-count/cases_test.go"
            if not cases.is_file():
                raise RuntimeError("Generator did not produce cases_test.go")

            copies.append((copy, cases))

        first, second = copies[0][1], copies[1][1]

        if normalized(first) != normalized(second):
            raise RuntimeError("The two generated files differ.")

        if normalized(first) != normalized(checked_in):
            raise RuntimeError(
                "Generated output does not match committed cases_test.go."
            )

        shutil.copy2(first, actual_dir / "cases_test.go")
        shutil.copy2(second, EVIDENCE / "second-generated-cases_test.go")

        count = len(re.findall(r"(?m)^\s*description:", first.read_text()))
        if count != 14:
            raise RuntimeError(f"Expected 14 generated cases, found {count}.")

        log.append("PASS: both independent generations match.")
        log.append("PASS: generated output matches committed cases_test.go.")
        log.append(f"PASS: found {count} generated test cases.")

        exercise = copies[0][0] / "exercises/practice/word-count"
        reference = exercise / ".meta/example.go"
        target = exercise / solution

        if not reference.is_file():
            raise RuntimeError("Reference implementation is missing.")

        shutil.copy2(reference, target)

        test_output = run(
            ["go", "test", "-count=1", "./..."],
            exercise, os.environ.copy()
        )
        log.append("REFERENCE TESTS:\n" + test_output)
        log.append("PASS: reference implementation passes generated tests.")

    (EVIDENCE / "checks.txt").write_text("\n".join(log) + "\n")
    print("\n".join(log))
    print(f"\nEvidence saved in: {EVIDENCE}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise SystemExit(f"FAIL: {error}")
