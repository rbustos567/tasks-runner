#!/usr/bin/env python3
import argparse
import json
import logging
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Optional


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an ordered list of tasks from a JSON file with optional per-task timeouts."
    )
    parser.add_argument(
        "--tasks-list",
        required=True,
        type=Path,
        help="Full path to the JSON file containing the tasks.",
    )
    parser.add_argument(
        "--log-file",
        required=True,
        type=Path,
        help="Full path to the log file.",
    )
    return parser.parse_args()


def setup_logging(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def parse_timeout(raw_timeout: object) -> Optional[int]:
    # Treat missing key, null, or empty string as no timeout (run until completion).
    if raw_timeout is None or raw_timeout == "":
        return None
    timeout = int(raw_timeout)
    return timeout if timeout > 0 else None


def run_with_timeout(command: str, timeout: Optional[int]) -> int:
    # Start a new session so the process gets its own process group ID (PGID),
    # allowing us to terminate child processes cleanly on timeout.
    proc = subprocess.Popen(
        command,
        shell=True,
        executable="/bin/bash",
        start_new_session=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    pgid = os.getpgid(proc.pid)

    try:
        # When timeout is None, communicate() blocks until the process finishes.
        output, _ = proc.communicate(timeout=timeout)
        if output:
            for line in output.rstrip().splitlines():
                logging.info("    | %s", line)
        return proc.returncode
    except subprocess.TimeoutExpired:
        logging.warning(
            "Timeout (%ss) reached for PGID %s. Sending SIGTERM...", timeout, pgid
        )
        try:
            os.killpg(pgid, signal.SIGTERM)
            proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            logging.error(
                "Process group %s did not exit after SIGTERM. Sending SIGKILL...", pgid
            )
            os.killpg(pgid, signal.SIGKILL)
            proc.communicate()
        return 124


def main() -> None:
    args = parse_args()
    tasks_path = args.tasks_list.expanduser().resolve()
    log_path = args.log_file.expanduser().resolve()

    setup_logging(log_path)

    if not tasks_path.is_file():
        raise FileNotFoundError(f"Tasks file not found: {tasks_path}")

    data = json.loads(tasks_path.read_text(encoding="utf-8"))
    jobs = sorted(data.get("jobs", []), key=lambda job: job["index"])

    logging.info("Loaded tasks from %s (%d jobs)", tasks_path, len(jobs))

    for job in jobs:
        idx = job["index"]
        name = job.get("name", job["command"])
        command = job["command"]
        timeout = parse_timeout(job.get("timeout"))
        timeout_label = f"{timeout}s" if timeout is not None else "none"

        logging.info("Start [%s] %s (timeout=%s)", idx, name, timeout_label)
        start_time = time.monotonic()
        return_code = run_with_timeout(command, timeout)
        elapsed = time.monotonic() - start_time
        logging.info("End [%s] %s -> rc=%s in %.1fs", idx, name, return_code, elapsed)


if __name__ == "__main__":
    main()
