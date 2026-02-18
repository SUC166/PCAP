"""
GitHub-backed JSON store for PCAP admin credentials.
Reads/writes admins.json in a private GitHub repo via the REST API.
"""
import json, base64, hashlib, requests, streamlit as st
from datetime import datetime, timezone

GITHUB_API = "https://api.github.com"


# ── Secret helpers (safe — never raise KeyError to callers) ──────────────────

def secrets_configured() -> bool:
    """Return True only if all required secrets are present and non-empty."""
    try:
        gh = st.secrets["github"]
        token = gh["token"]
        repo  = gh["repo"]
        return (
            bool(token)
            and token != "ghp_YOUR_TOKEN_HERE"
            and bool(repo)
            and repo != "YOUR_GITHUB_USERNAME/pcap-data"
        )
    except Exception:
        return False


def _headers():
    return {
        "Authorization": f"token {st.secrets['github']['token']}",
        "Accept": "application/vnd.github+json",
    }

def _repo():
    return st.secrets["github"]["repo"]

def _path():
    return st.secrets["github"].get("admins_path", "admins.json")


# ── Core GitHub file I/O ─────────────────────────────────────────────────────

def _get_file():
    """Returns (content_dict_or_None, sha_or_None). Raises on network error."""
    url = f"{GITHUB_API}/repos/{_repo()}/contents/{_path()}"
    r = requests.get(url, headers=_headers(), timeout=10)
    if r.status_code == 404:
        return None, None
    r.raise_for_status()
    data = r.json()
    content = json.loads(base64.b64decode(data["content"]).decode())
    return content, data["sha"]


def load_admins() -> list:
    """Returns list of admin dicts. Falls back to [] if file not found."""
    content, _ = _get_file()
    if content is None:
        return []
    return content.get("admins", [])


def save_admins(admins_list: list) -> bool:
    """Writes the full admins list back to GitHub."""
    content, sha = _get_file()
    payload = {"admins": admins_list}
    encoded = base64.b64encode(json.dumps(payload, indent=2).encode()).decode()
    url = f"{GITHUB_API}/repos/{_repo()}/contents/{_path()}"
    body = {
        "message": (
            f"PCAP admin update "
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
        ),
        "content": encoded,
    }
    if sha:
        body["sha"] = sha
    r = requests.put(url, headers=_headers(), json=body, timeout=10)
    r.raise_for_status()
    return True


# ── Auth helpers ─────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_admin(username: str, password: str):
    """Returns admin dict if credentials valid, else None."""
    admins = load_admins()
    h = hash_password(password)
    for a in admins:
        if a["username"].lower() == username.lower() and a["password_hash"] == h:
            return a
    return None


def create_admin(username: str, password: str, phone: str, created_by: str):
    """Creates a new admin. Returns (True, '') or (False, reason_str)."""
    admins = load_admins()
    if any(a["username"].lower() == username.lower() for a in admins):
        return False, "Username already exists."
    admins.append({
        "username": username,
        "password_hash": hash_password(password),
        "phone": phone,
        "created_by": created_by,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    })
    save_admins(admins)
    return True, ""


def update_admin_credentials(
    username: str, new_username: str, new_password: str, new_phone: str
):
    """Allows an admin to update ONLY THEIR OWN credentials."""
    admins = load_admins()
    for a in admins:
        if (
            a["username"].lower() == new_username.lower()
            and a["username"].lower() != username.lower()
        ):
            return False, "New username is already taken."
    for i, a in enumerate(admins):
        if a["username"].lower() == username.lower():
            admins[i]["username"] = new_username
            admins[i]["password_hash"] = hash_password(new_password)
            admins[i]["phone"] = new_phone
            save_admins(admins)
            return True, ""
    return False, "Admin not found."


def bootstrap_needed() -> bool:
    """True if no admins exist yet in GitHub (first-ever run)."""
    return len(load_admins()) == 0
