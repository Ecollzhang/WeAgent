"""Dedicated debug logger for [LOG] messages. Output goes to debug.log."""
import os
import time
import threading

_log_lock = threading.Lock()


def _find_project_root():
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        if os.path.exists(os.path.join(d, "run.py")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return d


LOG_DIR = _find_project_root()
LOG_PATH = os.path.join(LOG_DIR, "debug.log")


def _write(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with _log_lock:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{ts} {msg}\n")
    print(f"{ts} {msg}")


def card_log(label: str, text: str):
    _write(f"[LOG Card] {text}")


def write_log(label: str, text: str):
    _write(f"[LOG write] {text}")
