"""
GitHub-backed store for FUTO PCAP.
Manages: admins.json, students.json, logs.json, backups/

KEY DESIGN: All writes to students.json and logs.json are dispatched
to a background thread so the UI never blocks or reruns waiting for
GitHub. Reads (on page load) are synchronous since we need the data.
"""
import json, base64, hashlib, requests, streamlit as st
import threading
from datetime import datetime, timezone
from collections import deque

GITHUB_API = "https://api.github.com"

# ── Background write queue ─────────────────────────────────────────────────────
# A single daemon thread drains this queue sequentially, ensuring GitHub
# writes don't race each other and never block the Streamlit main thread.
_write_queue: deque = deque()
_queue_lock  = threading.Lock()
_worker_started = False

def _ensure_worker():
    """Start the background writer thread once per process."""
    global _worker_started
    if _worker_started:
        return
    _worker_started = True
    t = threading.Thread(target=_writer_worker, daemon=True)
    t.start()

def _writer_worker():
    """Drain _write_queue continuously, executing each write job."""
    import time
    while True:
        job = None
        with _queue_lock:
            if _write_queue:
                job = _write_queue.popleft()
        if job:
            try:
                job()          # each job is a zero-arg callable
            except Exception:
                pass           # silently swallow — UI already updated
        else:
            time.sleep(0.25)  # idle wait


def _enqueue(fn):
    """Push a write callable onto the background queue."""
    _ensure_worker()
    with _queue_lock:
        _write_queue.append(fn)


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
    # Read secrets eagerly so the background thread doesn't need Streamlit context
    token = st.secrets["github"]["token"]
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }

def _repo():
    return st.secrets["github"]["repo"]

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


# ══════════════════════════════════════════════════════════════════════════════
# LOW-LEVEL GITHUB FILE I/O  (always synchronous — called by worker or directly)
# ══════════════════════════════════════════════════════════════════════════════

def _read_file(path: str, headers: dict, repo: str):
    """Returns (parsed_content, sha) or (None, None) if not found."""
    url = f"{GITHUB_API}/repos/{repo}/contents/{path}"
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code == 404:
        return None, None
    r.raise_for_status()
    data = r.json()
    content = json.loads(base64.b64decode(data["content"]).decode())
    return content, data["sha"]

def _write_file(path: str, payload: dict, commit_msg: str,
                headers: dict, repo: str, sha: str = None):
    """Creates or updates a file. sha required for updates."""
    encoded = base64.b64encode(json.dumps(payload, indent=2).encode()).decode()
    url  = f"{GITHUB_API}/repos/{repo}/contents/{path}"
    body = {"message": commit_msg, "content": encoded}
    if sha:
        body["sha"] = sha
    r = requests.put(url, headers=headers, json=body, timeout=15)
    r.raise_for_status()


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT LOGGING  — fire-and-forget background write
# ══════════════════════════════════════════════════════════════════════════════

LOG_PATH = "logs.json"

def append_log(actor: str, action: str, detail: str = ""):
    """Queue a log entry to be written in the background. Never blocks."""
    entry = {
        "timestamp": _now(),
        "actor":     actor,
        "action":    action,
        "detail":    detail,
    }
    # Snapshot secrets now (main thread) so background thread doesn't need them
    try:
        hdrs = _headers()
        repo = _repo()
    except Exception:
        return

    def _do_log():
        try:
            content, sha = _read_file(LOG_PATH, hdrs, repo)
            logs = content.get("logs", []) if content else []
            logs.append(entry)
            if len(logs) > 2000:
                logs = logs[-2000:]
            _write_file(
                LOG_PATH,
                {"logs": logs},
                f"PCAP log: {actor} — {action}",
                hdrs, repo, sha,
            )
        except Exception:
            pass

    _enqueue(_do_log)


def load_logs() -> list:
    """Synchronous read — returns all log entries newest first."""
    try:
        content, _ = _read_file(LOG_PATH, _headers(), _repo())
        logs = content.get("logs", []) if content else []
        return list(reversed(logs))
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN STORE  (admins.json — synchronous, low frequency)
# ══════════════════════════════════════════════════════════════════════════════

ADMINS_PATH = "admins.json"

def load_admins() -> list:
    content, _ = _read_file(ADMINS_PATH, _headers(), _repo())
    return content.get("admins", []) if content else []

def _save_admins_sync(admins_list: list):
    hdrs = _headers(); repo = _repo()
    content, sha = _read_file(ADMINS_PATH, hdrs, repo)
    _write_file(
        ADMINS_PATH,
        {"admins": admins_list},
        f"PCAP admin update [{_now()}]",
        hdrs, repo, sha,
    )

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_admin(username: str, password: str):
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
        "username":      username,
        "password_hash": hash_password(password),
        "phone":         phone,
        "created_by":    created_by,
        "created_at":    _now(),
    })
    _save_admins_sync(admins)
    append_log(created_by, "CREATE_ADMIN",
               f"Created admin: {username} | Phone: {phone}")
    return True, ""

def update_admin_credentials(username: str, new_username: str,
                              new_password: str, new_phone: str):
    admins = load_admins()
    for a in admins:
        if (a["username"].lower() == new_username.lower()
                and a["username"].lower() != username.lower()):
            return False, "New username is already taken."
    for i, a in enumerate(admins):
        if a["username"].lower() == username.lower():
            admins[i]["username"]      = new_username
            admins[i]["password_hash"] = hash_password(new_password)
            admins[i]["phone"]         = new_phone
            _save_admins_sync(admins)
            append_log(username, "UPDATE_OWN_CREDENTIALS",
                       f"Username → '{new_username}', phone → '{new_phone}'")
            return True, ""
    return False, "Admin not found."

def bootstrap_needed() -> bool:
    return len(load_admins()) == 0


# ══════════════════════════════════════════════════════════════════════════════
# STUDENT STORE  (students.json — background writes)
# ══════════════════════════════════════════════════════════════════════════════

STUDENTS_PATH = "students.json"

def load_students() -> list:
    """Synchronous read on startup."""
    try:
        content, _ = _read_file(STUDENTS_PATH, _headers(), _repo())
        return content.get("students", []) if content else []
    except Exception:
        return []

def save_students(students_list: list, actor: str = "system", action_note: str = "update"):
    """
    Background write — returns immediately, GitHub update happens async.
    The UI already has the correct state in session_state; this just persists it.
    """
    try:
        hdrs = _headers()
        repo = _repo()
    except Exception:
        return

    # Snapshot the list so it can't mutate between enqueue and execution
    snapshot = list(students_list)

    def _do_write():
        try:
            content, sha = _read_file(STUDENTS_PATH, hdrs, repo)
            _write_file(
                STUDENTS_PATH,
                {"students": snapshot},
                f"PCAP students {action_note} by {actor} [{_now()}]",
                hdrs, repo, sha,
            )
        except Exception:
            pass

    _enqueue(_do_write)

def students_to_df(students_list: list):
    import pandas as pd
    if not students_list:
        return None
    df = pd.DataFrame(students_list)
    for c in ["Olevel", "School_Fees", "Jamb"]:
        if c in df.columns:
            df[c] = df[c].map(
                lambda x: x is True or str(x).lower() in ("true", "1", "yes")
            )
    return df

def df_to_students(df) -> list:
    records = []
    for _, row in df.iterrows():
        records.append({
            "SN":            int(row["SN"]),
            "Name":          str(row["Name"]),
            "Matric_Number": str(row["Matric_Number"]),
            "Jamb_Reg":      str(row["Jamb_Reg"]),
            "Department":    str(row["Department"]),
            "Olevel":        row["Olevel"] is True,
            "School_Fees":   row["School_Fees"] is True,
            "Jamb":          row["Jamb"] is True,
        })
    return records


# ══════════════════════════════════════════════════════════════════════════════
# BACKUP  (backups/students_backup_TIMESTAMP.json — background write)
# ══════════════════════════════════════════════════════════════════════════════

def backup_students(students_list: list, actor: str) -> str:
    """Queues a background backup write. Returns the filename immediately."""
    stamp    = _now_stamp()
    filename = f"backups/students_backup_{stamp}.json"
    payload  = {
        "backed_up_at":  _now(),
        "backed_up_by":  actor,
        "student_count": len(students_list),
        "students":      students_list,
    }
    try:
        hdrs = _headers()
        repo = _repo()
    except Exception:
        return filename

    snapshot = dict(payload)

    def _do_backup():
        try:
            _write_file(filename, snapshot,
                        f"PCAP backup by {actor} [{_now()}]",
                        hdrs, repo, sha=None)
        except Exception:
            pass

    _enqueue(_do_backup)
    append_log(actor, "BACKUP_CREATED",
               f"Backup queued: {filename} ({len(students_list)} records)")
    return filename

def clear_all_students(actor: str) -> str:
    """
    Backs up current records (background) then synchronously wipes students.json.
    The wipe itself is synchronous so the caller knows it's done immediately.
    Returns the backup filename.
    """
    current  = load_students()
    backup_file = backup_students(current, actor)

    # Wipe is synchronous — we need this done before returning to the UI
    hdrs = _headers(); repo = _repo()
    content, sha = _read_file(STUDENTS_PATH, hdrs, repo)
    _write_file(
        STUDENTS_PATH,
        {"students": []},
        f"PCAP CLEAR ALL by {actor} [{_now()}]",
        hdrs, repo, sha,
    )
    append_log(actor, "CLEAR_ALL_STUDENTS",
               f"Deleted {len(current)} records. Backup: {backup_file}")
    return backup_file
