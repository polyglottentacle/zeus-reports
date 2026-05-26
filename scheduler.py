import argparse
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess

BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "output" / "scheduler.log"
REMOTE_URL = os.environ.get("GIT_REMOTE_URL", "https://github.com/polyglottentacle/zeus-reports.git")


def log(message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("w", encoding="utf-8") as f:
        f.write(f"{timestamp} - {message}\n")


def append_log(message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{timestamp} - {message}\n")


def run_git_command(args, **kwargs) -> subprocess.CompletedProcess:
    env = kwargs.pop("env", os.environ.copy())
    env["GIT_TERMINAL_PROMPT"] = "0"
    return subprocess.run(
        ["git"] + args,
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        env=env,
        **kwargs,
    )


def git_available() -> bool:
    try:
        result = run_git_command(["--version"])
        return result.returncode == 0
    except FileNotFoundError:
        return False


def ensure_git_repository() -> bool:
    if not git_available():
        append_log("git non trovato nel PATH. Impossibile eseguire push.")
        return False

    git_dir = BASE_DIR / ".git"
    if not git_dir.exists():
        append_log("Inizializzo git repository locale.")
        result = run_git_command(["init"])
        append_log(f"git init returncode={result.returncode}")
        if result.stderr:
            append_log(f"git init stderr: {result.stderr.strip()}")
        branch_result = run_git_command(["branch", "-M", "main"])
        if branch_result.returncode != 0 and branch_result.stderr:
            append_log(f"git branch -M main stderr: {branch_result.stderr.strip()}")

    result = run_git_command(["remote", "-v"])
    if result.returncode != 0 or REMOTE_URL not in result.stdout:
        if result.returncode == 0 and result.stdout:
            append_log(f"Remote origin diverso o non trovato, imposto URL: {REMOTE_URL}")
            set_remote = run_git_command(["remote", "set-url", "origin", REMOTE_URL])
            append_log(f"git remote set-url returncode={set_remote.returncode}")
            if set_remote.stderr:
                append_log(f"git remote set-url stderr: {set_remote.stderr.strip()}")
        else:
            append_log(f"Aggiungo remote origin {REMOTE_URL}")
            result = run_git_command(["remote", "add", "origin", REMOTE_URL])
            append_log(f"git remote add returncode={result.returncode}")
            if result.stderr:
                append_log(f"git remote add stderr: {result.stderr.strip()}")
    return True


def commit_and_push_report() -> None:
    if not ensure_git_repository():
        return

    report_path = BASE_DIR / "output" / "daily_report.json"
    if not report_path.exists():
        append_log("Nessun file daily_report.json da aggiungere a git.")
        return

    report_relative_path = report_path.relative_to(BASE_DIR).as_posix()
    append_log("Starting git add/commit/push cycle.")

    add_result = run_git_command(["add", report_relative_path])
    append_log(f"git add returncode={add_result.returncode}")
    if add_result.stdout:
        append_log(f"git add stdout: {add_result.stdout.strip()}")
    if add_result.stderr:
        append_log(f"git add stderr: {add_result.stderr.strip()}")
    if add_result.returncode != 0:
        append_log("git add ha restituito un errore; interrompo il flusso.")
        return

    diff_result = run_git_command(["diff", "--cached", "--quiet", "--", report_relative_path])
    if diff_result.returncode == 0:
        append_log("Nessuna modifica nello storico del report. Salto il commit.")
    elif diff_result.returncode == 1:
        commit_message = f"daily report {datetime.now(timezone.utc).isoformat()}"
        commit_result = run_git_command(["commit", "-m", commit_message])
        append_log(f"git commit returncode={commit_result.returncode}")
        if commit_result.stdout:
            append_log(f"git commit stdout: {commit_result.stdout.strip()}")
        if commit_result.stderr:
            append_log(f"git commit stderr: {commit_result.stderr.strip()}")
        if commit_result.returncode != 0:
            append_log("git commit non è riuscito. Verificare lo stato del repository.")
    else:
        append_log(f"git diff --cached returncode={diff_result.returncode}. Non posso determinare se ci sono modifiche.")

    push_result = run_git_command(["push", "--set-upstream", "origin", "main"])
    append_log(f"git push returncode={push_result.returncode}")
    if push_result.stdout:
        append_log(f"git push stdout: {push_result.stdout.strip()}")
    if push_result.stderr:
        append_log(f"git push stderr: {push_result.stderr.strip()}")


def run_once() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "agents.orchestrator"],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
    )
    append_log(f"Run once completed. returncode={result.returncode}")
    if result.stdout:
        append_log(f"stdout: {result.stdout.strip()}")
    if result.stderr:
        append_log(f"stderr: {result.stderr.strip()}")

    commit_and_push_report()


def sleep_until_next_run(hour: int = 8, minute: int = 0) -> None:
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    seconds = (target - now).total_seconds()
    append_log(f"Sleeping for {seconds} seconds until next run at {target.isoformat()}")
    time.sleep(seconds)


def main(run_once_only: bool = False) -> None:
    append_log("Scheduler started.")
    if run_once_only:
        run_once()
        append_log("Scheduler run-once complete.")
        return

    while True:
        now = datetime.now()
        if now.hour == 8 and now.minute == 0:
            append_log("Scheduled run triggered.")
            run_once()
            time.sleep(60)
        else:
            sleep_until_next_run(8, 0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scheduler for the Zeus trading backend.")
    parser.add_argument("--once", action="store_true", help="Run a single orchestrator cycle and exit.")
    args = parser.parse_args()
    main(run_once_only=args.once)
