# Tasks Runner

A lightweight Python runner designed to execute an ordered list of shell commands or scripts from a JSON configuration file, enforce per-job timeouts with process group cleanup, and write daily timestamped logs. Built to run unattended via `cron` without external dependencies.

## Features

- **Ordered execution:** Sorts jobs by `index` and runs them sequentially.
- **Optional timeouts:** Supports per-job `timeout` values in seconds; omits timeouts when the field is missing, `null`, empty (`""`), or less than or equal to `0`, letting the job run until completion.
- **Process group termination:** Launches each job in a new session (`start_new_session=True`) so timed-out tasks send `SIGTERM` to the entire process group first and escalate to `SIGKILL` after a 5-second grace period (returning exit code `124`).
- **Date placeholders in log paths:** Supports `{timestamp}` (`YYYY-MM-DD_HH-MM-SS`) inside `--log-file` and automatically creates parent directories.
- **Zero external dependencies:** Uses Python 3 standard library modules only.

## Repository Structure

```text
.
├── tasks_runner.py
├── jobs.example.json
└── README.md
```

## Usage

### Run manually
```bash
python3 /usr/local/bin/tasks_runner.py \
  --tasks-list /path/to/jobs.json \
  --log-file /path/to/logs/daily_runner_2026-11-21.log
```

### Run from crontab
```bash
30 8 * * * /bin/sh -c '/usr/bin/python3 /usr/local/bin/tasks_runner.py --tasks-list /home/user/config/jobs.json --log-file "/home/user/logs/tasks_runner_$(date +\%Y-\%m-\%d).log"'
```
