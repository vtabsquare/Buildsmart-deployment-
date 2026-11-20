"""Configuration and environment inspector for BuildSmart deployment."""
import os
import re
from pathlib import Path

DEPLOYER_ROOT = Path(__file__).resolve().parent.parent
BUILDSMART_ROOT = (DEPLOYER_ROOT.parent / "BuildSmart_New").resolve()

# Fallback if moved inside BuildSmart_New
if not BUILDSMART_ROOT.is_dir() and (DEPLOYER_ROOT / "app").is_dir():
    BUILDSMART_ROOT = DEPLOYER_ROOT

KEY_REGEX = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
DEFAULT_REPO_URL = os.environ.get("TARGET_REPO_URL", "https://github.com/vtabsquare/Build-smart-application.git")


def read_env_file(env_path: Path) -> dict:
    entries = {}
    if not env_path.is_file():
        return entries
    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, val = line.removeprefix("export ").partition("=")
        key, val = key.strip(), val.strip()
        if not sep or not KEY_REGEX.match(key):
            continue
        if val.startswith(('"', "'")) and len(val) >= 2 and val[-1] == val[0]:
            val = val[1:-1]
        else:
            val = re.split(r'\s+#', val, maxsplit=1)[0].rstrip()
        entries[key] = val
    return entries


def get_local_google_refresh_token() -> str:
    """Read cached refresh token from local SQLite or environment variable."""
    if os.environ.get("GOOGLE_REFRESH_TOKEN"):
        return os.environ.get("GOOGLE_REFRESH_TOKEN")
    try:
        import sqlite3
        import json
        db_path = BUILDSMART_ROOT / "data" / "buildsmart.sqlite3"
        if db_path.is_file():
            conn = sqlite3.connect(str(db_path), timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM metadata WHERE key='google_setup_connection'")
            row = cursor.fetchone()
            conn.close()
            if row and row[0]:
                data = json.loads(row[0])
                token = data.get("refresh_token", "")
                if token:
                    return token
    except Exception:
        pass
    return ""


def get_buildsmart_env() -> dict:
    entries = {}
    if (DEPLOYER_ROOT / ".env").is_file():
        entries.update(read_env_file(DEPLOYER_ROOT / ".env"))
    if (BUILDSMART_ROOT / ".env").is_file():
        entries.update(read_env_file(BUILDSMART_ROOT / ".env"))

    # Pull environment variables if set in os.environ (e.g. Render env vars)
    for key, val in os.environ.items():
        if val and (key not in entries or not entries[key]):
            entries[key] = val

    # Default non-secret configurations
    defaults = {
        "BUILDSMART_SHEET_ID": "1Jb1Ht0fxR3eQUj6Rwk3N6_8hIvsTdRzMe-AGacbQYvI",
        "BREVO_SENDER_EMAIL": "vitabsquare@gmail.com",
        "BREVO_SENDER_NAME": "BuildSmart 360",
        "BUILDSMART_ADMIN_EMAIL": "vitabsquare@gmail.com",
        "BUILDSMART_ADMIN_PASSWORD": "VtabAdmin@2026!",
        "BUILDSMART_BUILDER_EMAIL": "vigneshrajas.vtab@gmail.com",
        "BUILDSMART_BUILDER_PASSWORD": "VtabBuilder@2026!",
    }
    for k, v in defaults.items():
        if k not in entries or not entries[k]:
            entries[k] = v

    return entries


def get_render_env_vars(render_service_name: str = "buildsmart-360") -> list:
    """Build the exact dictionary of environment variables for Render."""
    local_env = get_buildsmart_env()
    refresh_token = local_env.get("GOOGLE_REFRESH_TOKEN") or get_local_google_refresh_token()
    
    render_url = f"https://{render_service_name}.onrender.com"
    redirect_uri = f"{render_url}/setup/google/callback"

    vars_dict = {
        "BUILDSMART_MODE": "production",
        "PYTHON_VERSION": "3.11.9",
        "BUILDSMART_SHEET_ID": local_env.get("BUILDSMART_SHEET_ID") or "1Jb1Ht0fxR3eQUj6Rwk3N6_8hIvsTdRzMe-AGacbQYvI",
        "GOOGLE_OAUTH_CLIENT_ID": local_env.get("GOOGLE_OAUTH_CLIENT_ID", ""),
        "GOOGLE_OAUTH_CLIENT_SECRET": local_env.get("GOOGLE_OAUTH_CLIENT_SECRET", ""),
        "GOOGLE_REFRESH_TOKEN": refresh_token,
        "GOOGLE_OAUTH_REDIRECT_URI": redirect_uri,
        "BREVO_API_KEY": local_env.get("BREVO_API_KEY", ""),
        "BREVO_SENDER_EMAIL": local_env.get("BREVO_SENDER_EMAIL") or "vitabsquare@gmail.com",
        "BREVO_SENDER_NAME": local_env.get("BREVO_SENDER_NAME") or "BuildSmart 360",
        "BUILDSMART_ADMIN_EMAIL": local_env.get("BUILDSMART_ADMIN_EMAIL") or "vitabsquare@gmail.com",
        "BUILDSMART_ADMIN_PASSWORD": local_env.get("BUILDSMART_ADMIN_PASSWORD") or "VtabAdmin@2026!",
        "BUILDSMART_BUILDER_EMAIL": local_env.get("BUILDSMART_BUILDER_EMAIL") or "vigneshrajas.vtab@gmail.com",
        "BUILDSMART_BUILDER_PASSWORD": local_env.get("BUILDSMART_BUILDER_PASSWORD") or "VtabBuilder@2026!",
        "BUILDSMART_ALLOW_EXISTING_DATA": "true",
        "CORS_ALLOWED_ORIGINS": render_url,
    }
    return [{"key": k, "value": v} for k, v in vars_dict.items()]
