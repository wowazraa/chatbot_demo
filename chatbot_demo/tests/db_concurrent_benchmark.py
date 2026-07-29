"""Yonlendirme: birlesik suite kullanin.

    python tests/benchmark_chatbot_suite.py
    python tests/benchmark_chatbot_suite.py --only db
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    suite = Path(__file__).resolve().parent / "benchmark_chatbot_suite.py"
    sys.argv = [str(suite), "--only", "db"]
    runpy.run_path(str(suite), run_name="__main__")
