"""Flask application backend for BuildSmart 360 Deployment Application."""
import os
import sys
from pathlib import Path
from flask import Flask, jsonify, render_template, request

from deployer.config import BUILDSMART_ROOT, DEFAULT_REPO_URL, get_buildsmart_env, get_render_env_vars, get_local_google_refresh_token
from deployer.git_service import (
    commit_all,
    get_approval_state,
    get_git_status,
    get_latest_commits,
    push_to_remote,
    save_approval_state,
    set_remote,
)
from deployer.render_api import RenderAPIError, RenderClient
from deployer.verifier import run_unit_tests, test_brevo_email, test_google_sheets, verify_live_url

APP_DIR = Path(__file__).resolve().parent

app = Flask(
    __name__,
    template_folder=str(APP_DIR / "templates"),
    static_folder=str(APP_DIR / "static"),
)
app.config["SECRET_KEY"] = "buildsmart-deployer-secret"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/config")
def get_config():
    env = get_buildsmart_env()
    refresh_token = env.get("GOOGLE_REFRESH_TOKEN") or get_local_google_refresh_token()
    git_st = get_git_status()
    service_name = request.args.get("service_name", "buildsmart-360")
    render_vars = get_render_env_vars(service_name)

    return jsonify({
        "buildsmart_path": str(BUILDSMART_ROOT),
        "env_file_exists": (BUILDSMART_ROOT / ".env").is_file(),
        "default_repo_url": DEFAULT_REPO_URL,
        "config_summary": {
            "sheet_id": env.get("BUILDSMART_SHEET_ID", ""),
            "has_oauth_client": bool(env.get("GOOGLE_OAUTH_CLIENT_ID")),
            "has_oauth_secret": bool(env.get("GOOGLE_OAUTH_CLIENT_SECRET")),
            "has_refresh_token": bool(refresh_token),
            "refresh_token_preview": (refresh_token[:15] + "...") if refresh_token else "",
            "brevo_sender": env.get("BREVO_SENDER_EMAIL", ""),
            "has_brevo_key": bool(env.get("BREVO_API_KEY")),
            "admin_email": env.get("BUILDSMART_ADMIN_EMAIL", ""),
            "builder_email": env.get("BUILDSMART_BUILDER_EMAIL", ""),
        },
        "git": git_st,
        "render_vars": render_vars,
    })


@app.route("/api/verify/google", methods=["POST"])
def verify_google():
    result = test_google_sheets()
    return jsonify(result), (200 if result.get("success") else 400)


@app.route("/api/verify/email", methods=["POST"])
def verify_email():
    recipient = (request.json or {}).get("recipient")
    result = test_brevo_email(recipient)
    return jsonify(result), (200 if result.get("success") else 400)


@app.route("/api/verify/tests", methods=["POST"])
def verify_tests():
    result = run_unit_tests()
    return jsonify(result), (200 if result.get("success") else 400)


@app.route("/api/git/status")
def git_status_api():
    fetch = request.args.get("fetch", "false").lower() == "true"
    return jsonify(get_git_status(fetch_remote=fetch))


@app.route("/api/git/commits")
def git_commits_api():
    fetch = request.args.get("fetch", "false").lower() == "true"
    commits = get_latest_commits(limit=10, fetch=fetch)
    approval = get_approval_state()
    latest = commits[0] if commits else None
    return jsonify({
        "success": True,
        "commits": commits,
        "latest": latest,
        "approval": approval,
    })


@app.route("/api/git/approve", methods=["POST"])
def git_approve_commit():
    data = request.json or {}
    commit_hash = str(data.get("commit_hash") or "").strip()
    approver = str(data.get("approver") or "Administrator").strip()
    notes = str(data.get("notes") or "Approved for Render deployment").strip()

    if not commit_hash:
        commits = get_latest_commits(limit=1, fetch=False)
        if commits:
            commit_hash = commits[0]["hash"]
        else:
            return jsonify({"success": False, "error": "No commits found to approve"}), 400

    approval = save_approval_state(commit_hash, approver=approver, notes=notes)
    return jsonify({"success": True, "approval": approval})


@app.route("/api/git/set-remote", methods=["POST"])
def git_set_remote():
    url = (request.json or {}).get("remote_url", "")
    res = set_remote(url)
    return jsonify(res), (200 if res.get("success") else 400)


@app.route("/api/git/commit", methods=["POST"])
def git_commit():
    msg = (request.json or {}).get("message", "deploy: prepare release for Render")
    res = commit_all(msg)
    return jsonify(res), (200 if res.get("success") else 400)


@app.route("/api/git/push", methods=["POST"])
def git_push():
    branch = (request.json or {}).get("branch", "main")
    res = push_to_remote(branch)
    return jsonify(res), (200 if res.get("success") else 400)


@app.route("/api/render/owners", methods=["POST"])
def render_owners():
    key = (request.json or {}).get("api_key", "").strip()
    if not key:
        return jsonify({"success": False, "error": "Render API key is required"}), 400
    try:
        client = RenderClient(key)
        owners = client.get_owners()
        return jsonify({"success": True, "owners": owners})
    except RenderAPIError as err:
        return jsonify({"success": False, "error": str(err)}), 400



def extract_service_id(data: dict) -> str:
    if not isinstance(data, dict):
        return ""
    if "service" in data and isinstance(data["service"], dict):
        return str(data["service"].get("id") or "")
    return str(data.get("id") or "")

def extract_deploy_id(data: dict) -> str:
    if not isinstance(data, dict):
        return ""
    if "deploy" in data and isinstance(data["deploy"], dict):
        return str(data["deploy"].get("id") or "")
    return str(data.get("deployId") or data.get("id") or "")

def extract_service_url(data: dict, fallback_name: str) -> str:
    if not isinstance(data, dict):
        return f"https://{fallback_name}.onrender.com"
    details = data.get("serviceDetails")
    if not details and "service" in data and isinstance(data["service"], dict):
        details = data["service"].get("serviceDetails")
    if isinstance(details, dict) and details.get("url"):
        return details["url"]
    return f"https://{fallback_name}.onrender.com"

@app.route("/api/render/deploy", methods=["POST"])
def render_deploy():
    data = request.json or {}
    api_key = str(data.get("api_key") or "").strip()
    owner_id = str(data.get("owner_id") or "").strip()
    service_name = str(data.get("service_name") or "buildsmart-360").strip()
    repo_url = str(data.get("repo_url") or DEFAULT_REPO_URL).strip()
    branch = str(data.get("branch") or "main").strip()
    region = str(data.get("region") or "singapore").strip()
    plan = str(data.get("plan") or "free").strip()
    commit_id = str(data.get("commit_id") or "").strip()

    if not api_key or not owner_id or not repo_url or not service_name:
        return jsonify({"success": False, "error": "Missing required fields"}), 400

    env_vars = get_render_env_vars(service_name)
    client = RenderClient(api_key)

    try:
        # Check if service already exists
        existing = client.find_service_by_name(service_name)
        if existing:
            service_id = extract_service_id(existing)
            try:
                client.update_env_vars(service_id, env_vars)
            except Exception as env_err:
                print(f"Note on update_env_vars: {env_err}")
            deploy_res = client.trigger_deploy(service_id, clear_cache=True, commit_id=commit_id or None)
            deploy_id = extract_deploy_id(deploy_res)
            commits = get_latest_commits(limit=1, fetch=False)
            latest_commit = commits[0] if commits else None
            if latest_commit:
                save_approval_state(
                    latest_commit["hash"],
                    approver=str(data.get("approver") or "Administrator"),
                    notes=f"Deployed to Render ({service_name}) with deploy ID {deploy_id}"
                )
            return jsonify({
                "success": True,
                "action": "updated",
                "service_id": service_id,
                "service_name": service_name,
                "deploy_id": deploy_id,
                "deployed_commit": latest_commit,
                "url": extract_service_url(existing, service_name),
            })
        else:
            # Create fresh web service
            created = client.create_web_service(
                name=service_name,
                owner_id=owner_id,
                repo_url=repo_url,
                branch=branch,
                region=region,
                plan=plan,
                env_vars=env_vars,
            )
            service_id = extract_service_id(created)
            deploy_id = extract_deploy_id(created)
            try:
                client.update_env_vars(service_id, env_vars)
            except Exception:
                pass
            commits = get_latest_commits(limit=1, fetch=False)
            latest_commit = commits[0] if commits else None
            if latest_commit:
                save_approval_state(
                    latest_commit["hash"],
                    approver=str(data.get("approver") or "Administrator"),
                    notes=f"Deployed to Render ({service_name}) with deploy ID {deploy_id}"
                )
            return jsonify({
                "success": True,
                "action": "created",
                "service_id": service_id,
                "service_name": service_name,
                "deploy_id": deploy_id,
                "deployed_commit": latest_commit,
                "url": extract_service_url(created, service_name),
            })
    except RenderAPIError as err:
        return jsonify({"success": False, "error": str(err)}), 400


@app.route("/api/render/deploy-status", methods=["POST"])
def render_deploy_status():
    data = request.json or {}
    api_key = str(data.get("api_key") or "").strip()
    service_id = str(data.get("service_id") or "").strip()
    deploy_id = str(data.get("deploy_id") or "").strip()
    service_name = str(data.get("service_name") or "buildsmart-360").strip()

    if not api_key:
        return jsonify({"success": False, "error": "Render API key is required"}), 400

    if service_id in ("null", "undefined", "None", ""):
        service_id = ""
    if deploy_id in ("null", "undefined", "None", ""):
        deploy_id = ""

    client = RenderClient(api_key)
    try:
        # Auto-resolve service_id by name if missing
        if not service_id:
            existing = client.find_service_by_name(service_name)
            if existing:
                service_id = extract_service_id(existing)

        if not service_id:
            return jsonify({"success": False, "error": f"Service '{service_name}' not found"}), 404

        if deploy_id:
            deploy_info = client.get_deploy_status(service_id, deploy_id)
            deploy = deploy_info.get("deploy", deploy_info) if isinstance(deploy_info, dict) else {}
            status = deploy.get("status", "unknown")
        else:
            deploys = client._request("GET", f"/services/{service_id}/deploys?limit=1")
            deploy_info = deploys[0].get("deploy", deploys[0]) if (deploys and isinstance(deploys, list)) else {}
            status = deploy_info.get("status", "unknown") if isinstance(deploy_info, dict) else "unknown"

        return jsonify({
            "success": True,
            "status": status,
            "service_id": service_id,
            "data": deploy_info,
        })
    except RenderAPIError as err:
        return jsonify({"success": False, "error": str(err)}), 400


@app.route("/api/verify/live", methods=["POST"])
def verify_live():
    url = (request.json or {}).get("url", "")
    res = verify_live_url(url)
    return jsonify(res), (200 if res.get("success") else 400)
