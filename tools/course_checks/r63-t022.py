from pathlib import Path
import runpy

root = Path(__file__).resolve().parents[2]
checker = root / "work/R63-T022/check.py"
runpy.run_path(str(checker), run_name="__main__")
