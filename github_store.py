"""
GitHub-backed store for FUTO PCAP.
Manages: admins.json, students.json, logs.json, backups/
All reads/writes go through the GitHub Contents API.
"""
import json, base64, hashlib, requests, streamlit as st
from datetime import datetime, timezone

GITHUB_API = "https://api.github.com"


# ══════════════════════════════════════════════════════════════════════════════
# SECRET HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def secrets_configured() -> bool:
    try:
        gh    = st.secrets["github"]
        token = gh["token"]
        repo  = gh["repo"]
        return (
            bool(token) and token != "ghp_YOUR_TOKEN_HERE"
            and bool(repo) and repo != "YOUR_GITHUB_USERNAME/pcap-data"
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

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


# ══════════════════════════════════════════════════════════════════════════════
# LOW-LEVEL GITHUB FILE I/O
# ══════════════════════════════════════════════════════════════════════════════

def _read_file(path: str):
    """Returns (parsed_content, sha) or (None, None) if file doesn't exist."""
    url = f"{GITHUB_API}/repos/{_repo()}/contents/{path}"
    r = requests.get(url, headers=_headers(), timeout=15)
    if r.status_code == 404:
        return None, None
    r.raise_for_status()
    data = r.json()
    content = json.loads(base64.b64decode(data["content"]).decode())
    return content, data["sha"]

def _write_file(path: str, payload: dict, commit_msg: str, sha: str = None):
    """Creates or updates a file in GitHub. sha required for updates."""
    encoded = base64.b64encode(json.dumps(payload, indent=2).encode()).decode()
    url = f"{GITHUB_API}/repos/{_repo()}/contents/{path}"
    body = {"message": commit_msg, "content": encoded}
    if sha:
        body["sha"] = sha
    r = requests.put(url, headers=_headers(), json=body, timeout=15)
    r.raise_for_status()
    return r.json()


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT LOGGING
# ══════════════════════════════════════════════════════════════════════════════

LOG_PATH = "logs.json"

def append_log(actor: str, action: str, detail: str = ""):
    """Appends a single log entry to logs.json. Never raises — logging must not break the app."""
    try:
        content, sha = _read_file(LOG_PATH)
        logs = content.get("logs", []) if content else []
        logs.append({
            "timestamp": _now(),
            "actor": actor,
            "action": action,
            "detail": detail,
        })
        # Keep last 2000 entries to avoid file bloat
        if len(logs) > 2000:
            logs = logs[-2000:]
        _write_file(
            LOG_PATH,
            {"logs": logs},
            f"PCAP log: {actor} — {action} [{_now()}]",
            sha,
        )
    except Exception:
        pass  # Logging failure must never break normal operation

def load_logs() -> list:
    """Returns all log entries, newest first."""
    try:
        content, _ = _read_file(LOG_PATH)
        if content is None:
            return []
        logs = content.get("logs", [])
        return list(reversed(logs))
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN STORE  (admins.json)
# ══════════════════════════════════════════════════════════════════════════════

ADMINS_PATH = "admins.json"

def load_admins() -> list:
    content, _ = _read_file(ADMINS_PATH)
    return content.get("admins", []) if content else []

def save_admins(admins_list: list):
    content, sha = _read_file(ADMINS_PATH)
    _write_file(
        ADMINS_PATH,
        {"admins": admins_list},
        f"PCAP admin update [{_now()}]",
        sha,
    )

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_admin(username: str, password: str):
    """Returns admin dict if valid, else None."""
    admins = load_admins()
    h = hash_password(password)
    for a in admins:
        if a["username"].lower() == username.lower() and a["password_hash"] == h:
            return a
    return None

def create_admin(username: str, password: str, phone: str, created_by: str):
    admins = load_admins()
    if any(a["username"].lower() == username.lower() for a in admins):
        return False, "Username already exists."
    admins.append({
        "username": username,
        "password_hash": hash_password(password),
        "phone": phone,
        "created_by": created_by,
        "created_at": _now(),
    })
    save_admins(admins)
    append_log(created_by, "CREATE_ADMIN", f"Created admin account: {username} | Phone: {phone}")
    return True, ""

def update_admin_credentials(username: str, new_username: str, new_password: str, new_phone: str):
    admins = load_admins()
    for a in admins:
        if a["username"].lower() == new_username.lower() and a["username"].lower() != username.lower():
            return False, "New username is already taken."
    for i, a in enumerate(admins):
        if a["username"].lower() == username.lower():
            admins[i]["username"]      = new_username
            admins[i]["password_hash"] = hash_password(new_password)
            admins[i]["phone"]         = new_phone
            save_admins(admins)
            append_log(username, "UPDATE_OWN_CREDENTIALS",
                       f"Changed username to '{new_username}', phone to '{new_phone}'")
            return True, ""
    return False, "Admin not found."

def bootstrap_needed() -> bool:
    return len(load_admins()) == 0


# ══════════════════════════════════════════════════════════════════════════════
# STUDENT STORE  (students.json)
# ══════════════════════════════════════════════════════════════════════════════

STUDENTS_PATH = "students.json"

def load_students() -> list:
    """Returns list of student dicts from GitHub."""
    try:
        content, _ = _read_file(STUDENTS_PATH)
        return content.get("students", []) if content else []
    except Exception:
        return []

def save_students(students_list: list, actor: str = "system", action_note: str = "update"):
    """Persists the full student list to GitHub."""
    content, sha = _read_file(STUDENTS_PATH)
    _write_file(
        STUDENTS_PATH,
        {"students": students_list},
        f"PCAP students {action_note} by {actor} [{_now()}]",
        sha,
    )

def students_to_df(students_list: list):
    """Convert list-of-dicts to a pandas DataFrame."""
    import pandas as pd
    if not students_list:
        return None
    df = pd.DataFrame(students_list)
    # Ensure bool columns are proper bools
    for c in ["Olevel", "School_Fees", "Jamb"]:
        if c in df.columns:
            df[c] = df[c].map(lambda x: x is True or str(x).lower() in ("true","1","yes"))
    return df

def df_to_students(df) -> list:
    """Convert DataFrame to list-of-dicts for JSON storage."""
    records = []
    for _, row in df.iterrows():
        records.append({
            "SN":           int(row["SN"]),
            "Name":         str(row["Name"]),
            "Matric_Number":str(row["Matric_Number"]),
            "Jamb_Reg":     str(row["Jamb_Reg"]),
            "Department":   str(row["Department"]),
            "Olevel":       row["Olevel"] is True,
            "School_Fees":  row["School_Fees"] is True,
            "Jamb":         row["Jamb"] is True,
        })
    return records


# ══════════════════════════════════════════════════════════════════════════════
# BACKUP  (backups/students_backup_TIMESTAMP.json)
# ══════════════════════════════════════════════════════════════════════════════

def backup_students(students_list: list, actor: str) -> str:
    """
    Saves a timestamped backup of the student list to backups/.
    Returns the backup filename.
    """
    stamp     = _now_stamp()
    filename  = f"backups/students_backup_{stamp}.json"
    payload   = {
        "backed_up_at": _now(),
        "backed_up_by": actor,
        "student_count": len(students_list),
        "students": students_list,
    }
    _write_file(
        filename,
        payload,
        f"PCAP backup by {actor} [{_now()}]",
        sha=None,  # always a new file
    )
    append_log(actor, "BACKUP_CREATED", f"Backup saved: {filename} ({len(students_list)} records)")
    return filename

def clear_all_students(actor: str):
    """
    Backs up current records then wipes students.json.
    Returns backup filename.
    """
    current = load_students()
    backup_file = backup_students(current, actor)
    content, sha = _read_file(STUDENTS_PATH)
    _write_file(
        STUDENTS_PATH,
        {"students": []},
        f"PCAP CLEAR ALL students by {actor} [{_now()}]",
        sha,
    )
    append_log(actor, "CLEAR_ALL_STUDENTS",
               f"Deleted all {len(current)} student records. Backup: {backup_file}")
    return backup_file
