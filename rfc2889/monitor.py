#!/usr/bin/env python3
"""Monitor run_xoa_rfc.py progress by tailing the log file."""
import re, time, subprocess, sys
from pathlib import Path
from datetime import datetime

LOG = Path(__file__).parent / "run_xoa_rfc.log"
PROC_NAME = "run_xoa_rfc.py"
INTERVAL = 300  # seconds between reports
MAX_WAIT = 4 * 3600  # 4 hours hard cap

RE_FINAL = re.compile(r"test result \(final\)")
RE_INIT  = re.compile(r"__do_test \| init.*?(test_\w+)")
RE_TS    = re.compile(r"(\d{2}:\d{2}:\d{2})")


def is_running() -> bool:
    r = subprocess.run(["pgrep", "-f", PROC_NAME],
                       capture_output=True, text=True)
    return r.returncode == 0


def scan_log():
    if not LOG.exists():
        return 0, set(), ""
    text = LOG.read_text(errors="replace")
    finals = len(RE_FINAL.findall(text))
    suites = list(dict.fromkeys(RE_INIT.findall(text)))  # ordered unique
    timestamps = RE_TS.findall(text)
    last_ts = timestamps[-1] if timestamps else ""
    return finals, suites, last_ts


def report(elapsed: int, finals: int, suites: list, last_ts: str,
           running: bool):
    now = datetime.now().strftime("%H:%M:%S")
    mins = elapsed // 60
    status = "🟢 RUNNING" if running else "🏁 FINISHED"
    current = suites[-1] if suites else "—"

    print(f"\n{'='*60}")
    print(f"  {status}  |  {now}  |  elapsed {mins}m  |  log_ts {last_ts}")
    print(f"  Final results: {finals}  |  Current test: {current}")
    if suites:
        done = suites[:-1] if running else suites
        for s in done:
            print(f"    ✅ {s}")
        if running:
            print(f"    ⏳ {current}")
    print(f"{'='*60}")


def main():
    print(f"Monitoring {PROC_NAME} — reporting every {INTERVAL//60} min")
    print(f"Log file: {LOG}")

    start = time.time()
    last_report = -INTERVAL  # force immediate first report
    prev_finals = -1

    while True:
        elapsed = int(time.time() - start)
        running = is_running()
        finals, suites, last_ts = scan_log()

        # report every INTERVAL or when test finishes
        if elapsed - last_report >= INTERVAL or not running or finals != prev_finals and elapsed - last_report >= 30:
            report(elapsed, finals, suites, last_ts, running)
            last_report = elapsed
            prev_finals = finals

        if not running:
            print("\nTest process exited.")
            # check for errors
            if LOG.exists():
                text = LOG.read_text(errors="replace")
                tbs = text.count("Traceback")
                print(f"Tracebacks in log: {tbs}")
                if tbs:
                    # print last traceback
                    idx = text.rfind("Traceback")
                    print("--- last traceback ---")
                    print(text[idx:idx+500])
            break

        if elapsed >= MAX_WAIT:
            print(f"\n⏰ Hard timeout ({MAX_WAIT//3600}h) reached, process still running.")
            break

        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
