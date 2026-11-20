"""Git operations service for BuildSmart deployment."""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import requests

from deployer.config import BUILDSMART_ROOT, DEPLOYER_ROOT, DEFAULT_REPO_URL

# Approvals location: prefer BUILDSMART_ROOT/data if present, otherwise DEPLOYER_ROOT/data
APPROVALS_DIR = (BUILDSMART_ROOT / "data") if (BUILDSMART_ROOT / "data").is_dir() else (DEPLOYER_ROOT / "data")
APPROVALS_FILE = APPROVALS_DIR / "deployment_approvals.json"
_in_memory_approval = {}


def run_git(args: list[str]) -> tuple[int, str, str]:
    if not (BUILDSMART_ROOT / ".git").is_dir():
        return 1, "", "Local git repository not present."
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=BUILDSMART_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as exc:
        return 1, "", str(exc)


def get_approval_state() -> dict:
    global _in_memory_approval
    if _in_memory_approval:
        return _in_memory_approval
    if not APPROVALS_FILE.is_file():
        return {}
    try:
        with open(APPROVALS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            _in_memory_approval = data
            return data
    except Exception:
        return _in_memory_approval or {}


def save_approval_state(commit_hash: str, approver: str = "Administrator", notes: str = "") -> dict:
    global _in_memory_approval
    commit_hash = commit_hash.strip()
    commits = get_latest_commits(limit=10, fetch=False)
    matched = next((c for c in commits if c["hash"] == commit_hash or c["short_hash"] == commit_hash), None)

    if matched:
        full_hash = matched["hash"]
        short_hash = matched["short_hash"]
        subject = matched["subject"]
        author = matched["author_name"]
    else:
        full_hash = commit_hash
        short_hash = commit_hash[:7]
        subject = "Latest repository commit"
        author = "Author"
        if (BUILDSMART_ROOT / ".git").is_dir():
            _, short_hash, _ = run_git(["rev-parse", "--short", commit_hash])
            _, subject, _ = run_git(["log", "-1", "--pretty=format:%s", commit_hash])
            _, author, _ = run_git(["log", "-1", "--pretty=format:%an", commit_hash])

    state = {
        "approved_commit": full_hash,
        "short_hash": short_hash or full_hash[:7],
        "subject": subject or "Latest repository commit",
        "author": author or "Author",
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "approver": approver or "Administrator",
        "notes": notes or "Approved for Render deployment",
    }
    _in_memory_approval = state

    try:
        APPROVALS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(APPROVALS_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"Note: using in-memory state: {e}")

    return state


def fetch_github_api_commits(repo_url: str = DEFAULT_REPO_URL, limit: int = 10) -> list[dict]:
    """Fetch commits directly from GitHub API when running without a local git clone."""
    try:
        clean_url = repo_url.strip().rstrip("/").removesuffix(".git")
        parts = clean_url.split("/")
        if len(parts) >= 2:
            owner, repo = parts[-2], parts[-1]
            api_url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page={limit}"
            req = requests.get(
                api_url,
                headers={"User-Agent": "BuildSmart-Deployer", "Accept": "application/vnd.github.v3+json"},
                timeout=10,
            )
            if req.ok:
                items = req.json()
                commits = []
                approval_data = get_approval_state()
                for c in items:
                    full_hash = c.get("sha", "")
                    short_hash = full_hash[:7]
                    commit_obj = c.get("commit", {})
                    author_obj = commit_obj.get("author", {})
                    author_name = author_obj.get("name", "Author")
                    author_email = author_obj.get("email", "")
                    date_str = author_obj.get("date", "")
                    message = commit_obj.get("message", "").splitlines()[0] if commit_obj.get("message") else ""
                    
                    is_approved = (
                        approval_data.get("approved_commit") == full_hash
                        or approval_data.get("short_hash") == short_hash
                    )
                    commits.append({
                        "hash": full_hash,
                        "short_hash": short_hash,
                        "author_name": author_name,
                        "author_email": author_email,
                        "date": date_str,
                        "subject": message,
                        "is_on_origin": True,
                        "approved": is_approved,
                        "approved_at": approval_data.get("approved_at") if is_approved else None,
                        "approver": approval_data.get("approver") if is_approved else None,
                    })
                return commits
    except Exception as e:
        print(f"Error fetching commits from GitHub API: {e}")
    return []


def get_latest_commits(limit: int = 5, fetch: bool = False) -> list[dict]:
    if (BUILDSMART_ROOT / ".git").is_dir():
        if fetch:
            run_git(["fetch", "origin"])

        code, stdout, _ = run_git([
            "log",
            f"-{limit}",
            "--pretty=format:%H%x09%h%x09%an%x09%ae%x09%ad%x09%s",
            "--date=iso",
        ])
        if code == 0 and stdout.strip():
            _, origin_hash, _ = run_git(["rev-parse", "origin/main"])
            origin_hash = origin_hash.strip()

            commits = []
            approval_data = get_approval_state()

            for line in stdout.splitlines():
                if not line.strip():
                    continue
                parts = line.split("\t")
                if len(parts) >= 6:
                    full_hash, short_hash, author_name, author_email, date_str, subject = parts[:6]
                elif len(parts) == 5:
                    full_hash, short_hash, author_name, author_email, subject = parts
                    date_str = ""
                else:
                    continue

                is_approved = (
                    approval_data.get("approved_commit") == full_hash
                    or approval_data.get("short_hash") == short_hash
                )

                commits.append({
                    "hash": full_hash,
                    "short_hash": short_hash,
                    "author_name": author_name,
                    "author_email": author_email,
                    "date": date_str,
                    "subject": subject,
                    "is_on_origin": (full_hash == origin_hash),
                    "approved": is_approved,
                    "approved_at": approval_data.get("approved_at") if is_approved else None,
                    "approver": approval_data.get("approver") if is_approved else None,
                })
            return commits

    # Fallback to GitHub API for cloud-hosted Deployer instance on Render
    return fetch_github_api_commits(limit=limit)


def get_git_status(fetch_remote: bool = False) -> dict:
    if (BUILDSMART_ROOT / ".git").is_dir():
        code, stdout, stderr = run_git(["status", "--porcelain"])
        if code == 0:
            _, branch, _ = run_git(["branch", "--show-current"])
            if not branch:
                _, branch, _ = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
            _, remote, _ = run_git(["remote", "get-url", "origin"])
            _, last_commit, _ = run_git(["log", "-1", "--oneline"])
            modified = [line.strip() for line in stdout.splitlines() if line.strip()]
            commits = get_latest_commits(limit=5, fetch=fetch_remote)
            return {
                "initialized": True,
                "branch": branch or "main",
                "clean": len(modified) == 0,
                "modified_files": modified,
                "remote_origin": remote or DEFAULT_REPO_URL,
                "last_commit": last_commit or "",
                "latest_commit_details": commits[0] if commits else None,
                "commits": commits,
                "approval": get_approval_state(),
                "error": "",
                "mode": "local_git",
            }

    # Cloud/Render mode: query GitHub API directly
    commits = fetch_github_api_commits(limit=5)
    latest = commits[0] if commits else None
    return {
        "initialized": True,
        "branch": "main",
        "clean": True,
        "modified_files": [],
        "remote_origin": DEFAULT_REPO_URL,
        "last_commit": f"{latest['short_hash']} {latest['subject']}" if latest else "Up to date",
        "latest_commit_details": latest,
        "commits": commits,
        "approval": get_approval_state(),
        "error": "",
        "mode": "cloud_github_sync",
    }


def set_remote(remote_url: str) -> dict:
    remote_url = remote_url.strip()
    if not remote_url:
        return {"success": False, "error": "Remote URL cannot be empty"}
    
    if (BUILDSMART_ROOT / ".git").is_dir():
        status = get_git_status()
        if status.get("remote_origin"):
            code, out, err = run_git(["remote", "set-url", "origin", remote_url])
        else:
            code, out, err = run_git(["remote", "add", "origin", remote_url])
        if code != 0:
            return {"success": False, "error": err or out}
    return {"success": True, "remote": remote_url}


def commit_all(message: str) -> dict:
    if not message.strip():
        message = "deploy: update BuildSmart 360 production configuration"
    if (BUILDSMART_ROOT / ".git").is_dir():
        run_git(["add", "."])
        code, out, err = run_git(["commit", "-m", message])
        if code != 0 and "nothing to commit" not in (out + err):
            return {"success": False, "error": err or out}
    commits = get_latest_commits(limit=1, fetch=False)
    latest = commits[0] if commits else None
    return {"success": True, "message": "Committed successfully", "latest_commit": latest}


def push_to_remote(branch: str = "main") -> dict:
    if (BUILDSMART_ROOT / ".git").is_dir():
        run_git(["branch", "-M", branch])
        code, out, err = run_git(["push", "-u", "origin", branch])
        output = f"{out}\n{err}".strip()
        if code != 0:
            return {
                "success": False,
                "error": output or "Push failed. Check GitHub repository permissions and authentication.",
            }
    commits = get_latest_commits(limit=1, fetch=False)
    latest = commits[0] if commits else None
    return {"success": True, "output": "GitHub repository in sync.", "latest_commit": latest}
