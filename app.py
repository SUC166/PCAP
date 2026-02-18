import streamlit as st
import pandas as pd
import re

st.set_page_config(
    page_title="FUTO PCAP",
    page_icon="\U0001F393",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif}

.hdr{
    background:linear-gradient(135deg,#006633,#009933 60%,#00cc44);
    border-radius:16px;padding:2rem 2.5rem;text-align:center;
    margin-bottom:1.5rem;box-shadow:0 8px 32px rgba(0,102,51,.18)
}
.hdr h1{color:#fff;font-size:2rem;font-weight:700;margin:0;letter-spacing:1px}
.hdr p{color:#d4f5d4;font-size:.95rem;margin:.4rem 0 0}

.ok-card{
    background:#f0faf4;border-left:5px solid #006633;border-radius:10px;
    padding:1.2rem 1.5rem;margin-bottom:.5rem;
    box-shadow:0 2px 8px rgba(0,102,51,.08)
}
.ok-card h3{color:#006633;margin:0 0 .5rem;font-size:1.1rem}
.ok-card p{margin:.2rem 0;color:#333;font-size:.92rem}

.badge-eligible{
    background:#006633;color:#fff;border-radius:20px;
    padding:3px 16px;font-size:.8rem;font-weight:600
}
.err-card{
    background:#fff5f5;border-left:5px solid #c00;border-radius:10px;
    padding:1.2rem 1.5rem;margin-bottom:.5rem
}
.err-card h4{color:#c00;margin:0 0 .4rem}
.err-card p{margin:.2rem 0;color:#555;font-size:.91rem}

.info-box{
    background:#fffbe6;border-left:5px solid #f0a500;
    border-radius:10px;padding:1rem 1.4rem;margin-bottom:1rem
}
.setup-box{
    background:#f0f4ff;border-left:5px solid #3355cc;
    border-radius:10px;padding:1.2rem 1.6rem;margin-bottom:1rem
}
.setup-box h4{color:#3355cc;margin:0 0 .6rem}
.setup-box code{background:#dde4ff;padding:2px 6px;border-radius:4px;font-size:.9rem}
.setup-box pre{background:#dde4ff;padding:.8rem;border-radius:6px;font-size:.82rem;overflow-x:auto}

.notice{
    background:linear-gradient(90deg,#006633,#009933);color:#fff;
    border-radius:10px;padding:1rem 1.4rem;text-align:center;
    font-weight:600;font-size:1rem;margin-top:.5rem;margin-bottom:1.5rem;
    letter-spacing:.3px
}
.stButton>button{
    background:#006633;color:#fff;border-radius:8px;border:none;
    padding:.5rem 2rem;font-weight:600;font-size:1rem;width:100%
}
.stButton>button:hover{background:#009933}
.ftr{text-align:center;color:#aaa;font-size:.8rem;margin-top:2.5rem}
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────
for k, v in {
    "admin_logged_in": False,
    "admin_user": None,
    "csv_df": None,
    "view": "student",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    "<div class='hdr'><h1>\U0001F393 FUTO PCAP</h1>"
    "<p>Federal University of Technology Owerri &nbsp;|&nbsp; "
    "Physical Clearance Assistance Platform</p></div>",
    unsafe_allow_html=True,
)

# ── Top nav ────────────────────────────────────────────────────────────────────
nav_l, nav_m, nav_r = st.columns([4, 1, 1])
with nav_m:
    if st.session_state.view == "student":
        if st.button("\U0001F512 Admin"):
            st.session_state.view = "admin_login"
            st.rerun()
    else:
        if st.button("\u2190 Student"):
            st.session_state.view = "student"
            st.rerun()
with nav_r:
    if st.session_state.admin_logged_in:
        if st.button("Logout"):
            st.session_state.admin_logged_in = False
            st.session_state.admin_user = None
            st.session_state.view = "student"
            st.rerun()

st.divider()


# ══════════════════════════════════════════════════════════════════════════════
# SETUP GUIDE — shown when secrets are not yet configured
# ══════════════════════════════════════════════════════════════════════════════
def setup_guide():
    st.markdown("""
<div class="setup-box">
<h4>⚙️ Setup Required — GitHub Secrets Not Configured</h4>
<p>PCAP stores admin credentials securely in a private GitHub repository.
You need to add your GitHub token and repo to Streamlit secrets before the admin panel will work.</p>

<p><strong>Step 1 — Create a private GitHub repo</strong><br>
Go to <a href="https://github.com/new" target="_blank">github.com/new</a>,
name it <code>pcap-data</code>, set it to <strong>Private</strong>, and create it empty.</p>

<p><strong>Step 2 — Generate a GitHub Personal Access Token</strong><br>
Go to <a href="https://github.com/settings/tokens" target="_blank">GitHub → Settings → Developer Settings → Personal Access Tokens → Fine-grained tokens</a><br>
Grant it <strong>Contents: Read and Write</strong> on your <code>pcap-data</code> repo only.</p>

<p><strong>Step 3 — Add secrets to Streamlit Cloud</strong><br>
In your Streamlit Cloud dashboard → your app → <strong>Settings → Secrets</strong>, paste:</p>

<pre>[github]
token = "ghp_your_token_here"
repo  = "your_github_username/pcap-data"
admins_path = "admins.json"</pre>

<p>Save and reboot the app. The Admin login will then work.</p>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# STUDENT VIEW
# ══════════════════════════════════════════════════════════════════════════════
def student_view():
    df = st.session_state.csv_df
    if df is None:
        st.markdown(
            "<div class='info-box'>&#128203; No clearance data has been loaded yet. "
            "Please check back later or contact the Admissions Office.</div>",
            unsafe_allow_html=True,
        )
        return

    st.markdown("#### \U0001F50D Check Your Clearance Eligibility")
    st.caption(
        "Search by your Surname, full name, 11-digit Matric Number, "
        "or 12-character JAMB Reg Number."
    )
    search_term = st.text_input(
        "Search",
        placeholder="e.g. Okafor  |  20251515463  |  202550551834BF",
        label_visibility="collapsed",
    )
    search_btn = st.button("Check Status")

    if not search_btn:
        return
    if not search_term.strip():
        st.warning("Please enter a search term.")
        return

    term = search_term.strip().lower()
    mask = (
        df["Name"].astype(str).str.lower().str.contains(term, na=False)
        | df["Matric_Number"].astype(str).str.lower().str.contains(term, na=False)
        | df["Jamb_Reg"].astype(str).str.lower().str.contains(term, na=False)
    )
    results = df[mask]

    if results.empty:
        st.warning(
            "No record found matching your search. "
            "Please verify your details or contact the Admissions Office."
        )
        return

    st.markdown(f"**{len(results)} record(s) found:**")
    for _, row in results.iterrows():
        olvl  = row["Olevel"] is True
        fees  = row["School_Fees"] is True
        jamb  = row["Jamb"] is True
        name  = str(row["Name"])
        dept  = str(row["Department"])
        mat   = str(row["Matric_Number"])
        jreg  = str(row["Jamb_Reg"])
        valid = olvl and fees and jamb

        if valid:
            st.markdown(
                f"<div class='ok-card'>"
                f"<h3>{name} &nbsp;<span class='badge-eligible'>ELIGIBLE</span></h3>"
                f"<p>\U0001F393 Department: <strong>{dept}</strong></p>"
                f"<p>\U0001F194 Matric Number: <strong>{mat}</strong></p>"
                f"<p>\U0001F4DD JAMB Reg: <strong>{jreg}</strong></p>"
                f"</div>"
                f"<div class='notice'>"
                f"\U0001F3EB You are ELIGIBLE for Physical Clearance. "
                f"Please proceed to the designated clearance venue with all original documents. "
                f"Your record will be verified on arrival."
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            ih = ""
            if not fees:
                ih += (
                    "<p><strong>\U0001F4B3 School Fees Not Paid</strong> &mdash; "
                    "Pay your school fees via the university payment portal "
                    "and allow 24&ndash;48 hours for confirmation.</p>"
                )
            if not jamb:
                ih += (
                    "<p><strong>\U0001F4CB JAMB Admission Not Confirmed</strong> &mdash; "
                    "Visit <em>jamb.gov.ng</em> or the Admissions Office "
                    "to confirm your admission status.</p>"
                )
            if not olvl:
                ih += (
                    "<p><strong>\U0001F4DA O&rsquo;Level Results Not Verified</strong> &mdash; "
                    "Submit your original result(s) to the Admissions Office. "
                    "Wait a little longer if recently submitted.</p>"
                )
            st.markdown(
                f"<div class='err-card'>"
                f"<h4>\u274C Not Yet Eligible &mdash; {name}</h4>"
                f"<p>Matric: <strong>{mat}</strong> &nbsp;|&nbsp; JAMB: <strong>{jreg}</strong></p>"
                f"<hr style='border:0;border-top:1px solid #f5c6c6;margin:.6rem 0'>"
                f"<p><strong>Action required:</strong></p>{ih}"
                f"<p style='color:#888;font-size:.84rem;margin-top:.4rem'>"
                f"Resolve the above and check again. "
                f"Contact the Admissions Office if you believe this is an error.</p>"
                f"</div>",
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN LOGIN VIEW
# ══════════════════════════════════════════════════════════════════════════════
def admin_login_view():
    from github_store import secrets_configured, verify_admin, bootstrap_needed, load_admins

    st.markdown("#### \U0001F512 Admin Login")

    # Gate: secrets not set up yet
    if not secrets_configured():
        setup_guide()
        return

    # Check GitHub connectivity and load admin state
    try:
        is_bootstrap = bootstrap_needed()
    except Exception as e:
        st.error(
            f"Could not connect to GitHub to load admin list. "
            f"Check your token and repo name in secrets.\n\n`{e}`"
        )
        return

    if is_bootstrap:
        st.info(
            "**First-time setup:** No admins exist yet. Use the bootstrap credentials below "
            "to log in and create your permanent admin account.\n\n"
            "**Username:** `pcap_bootstrap`  \n"
            "**Password:** `FUTOpcap2025!`\n\n"
            "> Create your real account immediately after logging in."
        )

    with st.form("login_form", clear_on_submit=False):
        uname = st.text_input("Username")
        passw = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)

    if not submitted:
        return

    if not uname.strip() or not passw:
        st.error("Please enter both username and password.")
        return

    # Bootstrap fallback (only when no admins in GitHub)
    if is_bootstrap and uname.strip() == "pcap_bootstrap" and passw == "FUTOpcap2025!":
        st.session_state.admin_logged_in = True
        st.session_state.admin_user = {"username": "pcap_bootstrap", "phone": ""}
        st.session_state.view = "admin_panel"
        st.rerun()
        return

    try:
        admin = verify_admin(uname.strip(), passw)
    except Exception as e:
        st.error(f"Error verifying credentials: `{e}`")
        return

    if admin:
        st.session_state.admin_logged_in = True
        st.session_state.admin_user = admin
        st.session_state.view = "admin_panel"
        st.rerun()
    else:
        st.error("Invalid username or password.")


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN PANEL VIEW
# ══════════════════════════════════════════════════════════════════════════════
def admin_panel_view():
    from github_store import (
        secrets_configured, load_admins, create_admin, update_admin_credentials
    )

    if not secrets_configured():
        setup_guide()
        return

    admin = st.session_state.admin_user
    st.markdown(
        f"#### \U0001F6E1\uFE0F Admin Panel &nbsp;"
        f"<span style='font-size:.85rem;color:#555;font-weight:400'>"
        f"Logged in as <strong>{admin['username']}</strong></span>",
        unsafe_allow_html=True,
    )

    tab1, tab2, tab3 = st.tabs([
        "\U0001F4C2 Clearance Data",
        "\U0001F468\u200D\U0001F4BB Create Admin",
        "\U0001F510 My Account",
    ])

    # ── Tab 1: Upload CSV ──────────────────────────────────────────────────
    with tab1:
        st.markdown("##### Upload / Replace Student Clearance CSV")
        st.markdown(
            "<div class='info-box'>"
            "<strong>Required CSV columns:</strong><br>"
            "<code>Name</code> (Surname Firstname Middlename) &nbsp;|&nbsp; "
            "<code>Matric_Number</code> (11 digits) &nbsp;|&nbsp; "
            "<code>Jamb_Reg</code> (10 digits + 2 letters, e.g. <code>202550551834BF</code>) &nbsp;|&nbsp; "
            "<code>Department</code> &nbsp;|&nbsp; "
            "<code>Olevel</code> &nbsp;|&nbsp; <code>School_Fees</code> &nbsp;|&nbsp; <code>Jamb</code>"
            "</div>",
            unsafe_allow_html=True,
        )
        uploaded = st.file_uploader("Upload CSV", type=["csv"], key="admin_csv")
        if uploaded:
            try:
                df = pd.read_csv(uploaded)
                df.columns = df.columns.str.strip()
                required = {
                    "Name", "Matric_Number", "Jamb_Reg",
                    "Department", "Olevel", "School_Fees", "Jamb"
                }
                missing = required - set(df.columns)
                if missing:
                    st.error(f"Missing columns: {', '.join(sorted(missing))}")
                else:
                    bad_matric = df[
                        ~df["Matric_Number"].astype(str).str.match(r"^\d{11}$")
                    ]
                    bad_jamb = df[
                        ~df["Jamb_Reg"].astype(str).str.match(r"^\d{10}[A-Za-z]{2}$")
                    ]
                    if not bad_matric.empty:
                        st.warning(
                            f"\u26A0\uFE0F {len(bad_matric)} row(s) have invalid Matric Numbers "
                            f"(must be exactly 11 digits). Check: "
                            f"{bad_matric['Name'].tolist()}"
                        )
                    if not bad_jamb.empty:
                        st.warning(
                            f"\u26A0\uFE0F {len(bad_jamb)} row(s) have invalid JAMB Reg Numbers "
                            f"(must be 10 digits followed by 2 letters). Check: "
                            f"{bad_jamb['Name'].tolist()}"
                        )

                    bmap = {
                        "true": True, "1": True, "yes": True,
                        "false": False, "0": False, "no": False
                    }
                    for c in ["Olevel", "School_Fees", "Jamb"]:
                        df[c] = df[c].astype(str).str.strip().str.lower().map(bmap)

                    st.session_state.csv_df = df
                    eligible = df[
                        (df["Olevel"] == True) &
                        (df["School_Fees"] == True) &
                        (df["Jamb"] == True)
                    ]
                    st.success(
                        f"\u2705 CSV loaded — {len(df)} total records, "
                        f"{len(eligible)} eligible for clearance."
                    )
                    st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"Error reading CSV: {e}")

        if st.session_state.csv_df is not None and not uploaded:
            df_cur = st.session_state.csv_df
            eligible_count = len(df_cur[
                (df_cur["Olevel"] == True) &
                (df_cur["School_Fees"] == True) &
                (df_cur["Jamb"] == True)
            ])
            st.info(
                f"Currently loaded: **{len(df_cur)} records** | "
                f"**{eligible_count} eligible**"
            )
            with st.expander("View current data"):
                st.dataframe(df_cur, use_container_width=True)

    # ── Tab 2: Create Admin ────────────────────────────────────────────────
    with tab2:
        st.markdown("##### Create a New Admin Account")
        st.caption(
            "The new admin's phone number, username, creation time, "
            "and your username are all saved to GitHub automatically."
        )

        with st.form("create_admin_form", clear_on_submit=True):
            new_phone = st.text_input(
                "Phone Number",
                placeholder="+2348118429150",
                help="Must include country code (e.g. +234...)"
            )
            new_uname = st.text_input("Username")
            new_pass  = st.text_input("Password", type="password")
            new_pass2 = st.text_input("Confirm Password", type="password")
            create_btn = st.form_submit_button("Create Admin", use_container_width=True)

        if create_btn:
            errors = []
            if not new_phone.strip():
                errors.append("Phone number is required.")
            elif not re.match(r"^\+\d{7,15}$", new_phone.strip()):
                errors.append("Phone must start with + followed by 7–15 digits, e.g. +2348118429150")
            if not new_uname.strip():
                errors.append("Username is required.")
            elif len(new_uname.strip()) < 3:
                errors.append("Username must be at least 3 characters.")
            if len(new_pass) < 8:
                errors.append("Password must be at least 8 characters.")
            if new_pass != new_pass2:
                errors.append("Passwords do not match.")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                try:
                    ok, reason = create_admin(
                        new_uname.strip(), new_pass,
                        new_phone.strip(), admin["username"]
                    )
                    if ok:
                        st.success(
                            f"\u2705 Admin **{new_uname.strip()}** created successfully! "
                            f"Entry saved to GitHub with timestamp."
                        )
                    else:
                        st.error(f"Could not create admin: {reason}")
                except Exception as e:
                    st.error(f"GitHub error: {e}")

        st.markdown("---")
        st.markdown("##### Existing Admins")
        try:
            admins = load_admins()
            if admins:
                rows = [
                    {
                        "Username": a["username"],
                        "Phone": a.get("phone", ""),
                        "Created By": a.get("created_by", "—"),
                        "Created At (UTC)": a.get("created_at", "—"),
                    }
                    for a in admins
                ]
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
            else:
                st.info("No admins in GitHub store yet.")
        except Exception as e:
            st.error(f"Could not load admin list: {e}")

    # ── Tab 3: My Account ──────────────────────────────────────────────────
    with tab3:
        st.markdown("##### Update Your Own Credentials")
        st.caption(
            "\u26A0\uFE0F You can only modify your own account. "
            "After saving, you will be logged out and must log in again with the new details."
        )

        with st.form("update_self_form"):
            upd_phone = st.text_input(
                "Phone Number",
                value=admin.get("phone", ""),
                placeholder="+2348118429150"
            )
            upd_uname = st.text_input(
                "Username",
                value=admin.get("username", "")
            )
            upd_pass  = st.text_input("New Password", type="password")
            upd_pass2 = st.text_input("Confirm New Password", type="password")
            upd_btn   = st.form_submit_button("Save Changes", use_container_width=True)

        if upd_btn:
            errors = []
            if not upd_phone.strip():
                errors.append("Phone number is required.")
            elif not re.match(r"^\+\d{7,15}$", upd_phone.strip()):
                errors.append("Phone must start with + followed by 7–15 digits.")
            if not upd_uname.strip():
                errors.append("Username cannot be empty.")
            elif len(upd_uname.strip()) < 3:
                errors.append("Username must be at least 3 characters.")
            if len(upd_pass) < 8:
                errors.append("Password must be at least 8 characters.")
            if upd_pass != upd_pass2:
                errors.append("Passwords do not match.")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                try:
                    ok, reason = update_admin_credentials(
                        admin["username"],
                        upd_uname.strip(),
                        upd_pass,
                        upd_phone.strip()
                    )
                    if ok:
                        st.success("Credentials updated! Logging you out now...")
                        st.session_state.admin_logged_in = False
                        st.session_state.admin_user = None
                        st.session_state.view = "admin_login"
                        st.rerun()
                    else:
                        st.error(f"Update failed: {reason}")
                except Exception as e:
                    st.error(f"GitHub error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════
view = st.session_state.view

if view == "student":
    student_view()
elif view == "admin_login":
    admin_login_view()
elif view == "admin_panel":
    if not st.session_state.admin_logged_in:
        st.session_state.view = "admin_login"
        st.rerun()
    else:
        admin_panel_view()

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(
    "<div class='ftr'>FUTO Physical Clearance Assistance Platform (PCAP) "
    "&copy; 2025 &nbsp;|&nbsp; Federal University of Technology Owerri</div>",
    unsafe_allow_html=True,
)
