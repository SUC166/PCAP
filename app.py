import streamlit as st

st.set_page_config(
    page_title="FUTO PCAP",
    page_icon="\U0001F393",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Shared CSS ─────────────────────────────────────────────────────────────────
SHARED_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif}

.hdr{
    background:linear-gradient(135deg,#006633,#009933 60%,#00cc44);
    border-radius:16px;padding:2rem 2.5rem;text-align:center;
    margin-bottom:2rem;box-shadow:0 8px 32px rgba(0,102,51,.18)
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
.ftr{text-align:center;color:#aaa;font-size:.8rem;margin-top:2rem}
</style>
"""

import pandas as pd
import re

# ── Session state init ─────────────────────────────────────────────────────────
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False
if "admin_user" not in st.session_state:
    st.session_state.admin_user = None
if "csv_df" not in st.session_state:
    st.session_state.csv_df = None
if "view" not in st.session_state:
    st.session_state.view = "student"   # "student" | "admin_login" | "admin_panel"

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(SHARED_CSS, unsafe_allow_html=True)
st.markdown(
    "<div class='hdr'><h1>\U0001F393 FUTO PCAP</h1>"
    "<p>Federal University of Technology Owerri &nbsp;|&nbsp; "
    "Physical Clearance Assistance Platform</p></div>",
    unsafe_allow_html=True,
)

# ── Top nav ────────────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns([4, 1, 1])
with c2:
    if st.session_state.view == "student":
        if st.button("Admin \U0001F512"):
            st.session_state.view = "admin_login"
            st.rerun()
    elif st.session_state.view in ("admin_login", "admin_panel"):
        if st.button("\U00002190 Student"):
            st.session_state.view = "student"
            st.rerun()
with c3:
    if st.session_state.admin_logged_in:
        if st.button("Logout"):
            st.session_state.admin_logged_in = False
            st.session_state.admin_user = None
            st.session_state.view = "student"
            st.rerun()

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# STUDENT VIEW
# ══════════════════════════════════════════════════════════════════════════════
def student_view():
    df = st.session_state.csv_df

    if df is None:
        st.markdown(
            "<div class='info-box'>&#128203; No clearance data has been loaded yet. "
            "Please check back later or contact the admissions office.</div>",
            unsafe_allow_html=True,
        )
        st.stop()

    st.markdown("#### \U0001F50D Check Your Clearance Eligibility")
    search_term = st.text_input(
        "Enter your Surname, Matric Number, or JAMB Reg Number",
        placeholder="e.g. Okafor  |  20251515463  |  202550551834BF",
    )
    search_btn = st.button("Check Status")

    if search_btn:
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
                "Please verify your details or contact the admissions office."
            )
            return

        st.markdown(f"**{len(results)} record(s) found:**")
        for _, row in results.iterrows():
            olvl  = row["Olevel"] is True
            fees  = row["School_Fees"] is True
            jamb  = row["Jamb"] is True
            name  = row["Name"]
            dept  = row["Department"]
            mat   = row["Matric_Number"]
            jreg  = row["Jamb_Reg"]
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
                    f"Please proceed to the designated venue with all required original documents. "
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
                        "Submit your original O&rsquo;Level result(s) to the Admissions Office "
                        "for verification. Wait a little longer if recently submitted.</p>"
                    )
                st.markdown(
                    f"<div class='err-card'>"
                    f"<h4>\u274C Not Yet Eligible &mdash; {name}</h4>"
                    f"<p>Matric: <strong>{mat}</strong> &nbsp;|&nbsp; JAMB: <strong>{jreg}</strong></p>"
                    f"<hr style='border:0;border-top:1px solid #f5c6c6;margin:.6rem 0'>"
                    f"<p><strong>Action required:</strong></p>{ih}"
                    f"<p style='color:#888;font-size:.84rem;margin-top:.4rem'>"
                    f"Resolve the above and check again. Contact the Admissions Office "
                    f"if you believe this is an error.</p>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

# ══════════════════════════════════════════════════════════════════════════════
# ADMIN LOGIN VIEW
# ══════════════════════════════════════════════════════════════════════════════
def admin_login_view():
    from github_store import verify_admin, bootstrap_needed, create_admin, hash_password

    st.markdown("#### \U0001F512 Admin Login")

    if bootstrap_needed():
        st.warning(
            "No admins exist yet. "
            "A bootstrap admin account is available for first-time setup:\n\n"
            "**Username:** `pcap_bootstrap`  |  **Password:** `FUTOpcap2025!`\n\n"
            "Please log in and create your real admin account immediately, "
            "then remove or change the bootstrap credentials."
        )

    with st.form("login_form"):
        uname = st.text_input("Username")
        passw = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        # Bootstrap fallback (first-run only)
        if bootstrap_needed() and uname == "pcap_bootstrap" and passw == "FUTOpcap2025!":
            st.session_state.admin_logged_in = True
            st.session_state.admin_user = {"username": "pcap_bootstrap", "phone": ""}
            st.session_state.view = "admin_panel"
            st.rerun()
            return

        admin = verify_admin(uname, passw)
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
        load_admins, create_admin, update_admin_credentials, hash_password
    )
    import re as _re

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

    # ── Tab 1: Upload CSV ───────────────────────────────────────────────────
    with tab1:
        st.markdown("##### Upload / Replace Student Clearance CSV")
        st.markdown(
            "<div class='info-box'>"
            "<strong>Required CSV columns:</strong><br>"
            "<code>Name</code> (Surname Firstname Middlename) &nbsp; "
            "<code>Matric_Number</code> (11 digits) &nbsp; "
            "<code>Jamb_Reg</code> (12 chars ending in 2 letters) &nbsp; "
            "<code>Department</code> &nbsp; "
            "<code>Olevel</code> &nbsp; <code>School_Fees</code> &nbsp; <code>Jamb</code>"
            "</div>",
            unsafe_allow_html=True,
        )
        uploaded = st.file_uploader("Upload CSV", type=["csv"], key="admin_csv")
        if uploaded:
            try:
                df = pd.read_csv(uploaded)
                df.columns = df.columns.str.strip()
                required = {
                    "Name","Matric_Number","Jamb_Reg",
                    "Department","Olevel","School_Fees","Jamb"
                }
                missing = required - set(df.columns)
                if missing:
                    st.error(f"Missing columns: {', '.join(missing)}")
                else:
                    # Validate formats
                    bad_matric = df[~df["Matric_Number"].astype(str).str.match(r"^\d{11}$")]
                    bad_jamb   = df[~df["Jamb_Reg"].astype(str).str.match(r"^\d{10}[A-Za-z]{2}$")]
                    warnings = []
                    if not bad_matric.empty:
                        warnings.append(
                            f"{len(bad_matric)} row(s) have invalid Matric Numbers "
                            f"(must be 11 digits): {bad_matric['Name'].tolist()}"
                        )
                    if not bad_jamb.empty:
                        warnings.append(
                            f"{len(bad_jamb)} row(s) have invalid JAMB Reg Numbers "
                            f"(must be 10 digits + 2 letters): {bad_jamb['Name'].tolist()}"
                        )
                    for w in warnings:
                        st.warning(w)

                    bmap = {
                        "true":True,"1":True,"yes":True,
                        "false":False,"0":False,"no":False
                    }
                    for c in ["Olevel","School_Fees","Jamb"]:
                        df[c] = df[c].astype(str).str.strip().str.lower().map(bmap)

                    st.session_state.csv_df = df
                    st.success(
                        f"CSV loaded successfully — {len(df)} records. "
                        f"Students can now check their eligibility."
                    )
                    st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"Error reading CSV: {e}")

        if st.session_state.csv_df is not None and uploaded is None:
            st.info(
                f"Currently loaded: {len(st.session_state.csv_df)} student records."
            )
            if st.button("View current data"):
                st.dataframe(st.session_state.csv_df, use_container_width=True)

    # ── Tab 2: Create Admin ─────────────────────────────────────────────────
    with tab2:
        st.markdown("##### Create a New Admin Account")
        st.caption(
            "New admin credentials are stored securely in GitHub. "
            "The creation date, time, and your username are recorded automatically."
        )
        with st.form("create_admin_form"):
            new_phone = st.text_input(
                "Phone Number",
                placeholder="+2348118429150",
                help="Include country code, e.g. +234..."
            )
            new_uname = st.text_input("Username")
            new_pass  = st.text_input("Password", type="password")
            new_pass2 = st.text_input("Confirm Password", type="password")
            create_btn = st.form_submit_button("Create Admin")

        if create_btn:
            errors = []
            if not new_phone.strip():
                errors.append("Phone number is required.")
            elif not _re.match(r"^\+\d{7,15}$", new_phone.strip()):
                errors.append("Phone must start with + and contain 7-15 digits.")
            if not new_uname.strip():
                errors.append("Username is required.")
            if len(new_pass) < 8:
                errors.append("Password must be at least 8 characters.")
            if new_pass != new_pass2:
                errors.append("Passwords do not match.")
            if errors:
                for e in errors:
                    st.error(e)
            else:
                ok, reason = create_admin(
                    new_uname.strip(), new_pass,
                    new_phone.strip(), admin["username"]
                )
                if ok:
                    st.success(
                        f"Admin account **{new_uname.strip()}** created successfully! "
                        f"Creation recorded in GitHub."
                    )
                else:
                    st.error(f"Failed to create admin: {reason}")

        st.markdown("---")
        st.markdown("##### Existing Admins")
        admins = load_admins()
        if admins:
            rows = []
            for a in admins:
                rows.append({
                    "Username": a["username"],
                    "Phone": a.get("phone",""),
                    "Created By": a.get("created_by","—"),
                    "Created At (UTC)": a.get("created_at","—"),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
        else:
            st.info("No admins yet in GitHub store.")

    # ── Tab 3: My Account ───────────────────────────────────────────────────
    with tab3:
        st.markdown("##### Update Your Own Credentials")
        st.caption(
            "You can only modify your own account. "
            "Changing your username will require you to log in again."
        )
        with st.form("update_self_form"):
            upd_phone = st.text_input(
                "New Phone Number",
                value=admin.get("phone",""),
                placeholder="+2348118429150"
            )
            upd_uname = st.text_input(
                "New Username",
                value=admin["username"]
            )
            upd_pass  = st.text_input("New Password", type="password")
            upd_pass2 = st.text_input("Confirm New Password", type="password")
            upd_btn   = st.form_submit_button("Save Changes")

        if upd_btn:
            errors = []
            if not upd_phone.strip():
                errors.append("Phone number is required.")
            elif not _re.match(r"^\+\d{7,15}$", upd_phone.strip()):
                errors.append("Phone must start with + and contain 7-15 digits.")
            if not upd_uname.strip():
                errors.append("Username cannot be empty.")
            if len(upd_pass) < 8:
                errors.append("Password must be at least 8 characters.")
            if upd_pass != upd_pass2:
                errors.append("Passwords do not match.")
            if errors:
                for e in errors:
                    st.error(e)
            else:
                ok, reason = update_admin_credentials(
                    admin["username"],
                    upd_uname.strip(),
                    upd_pass,
                    upd_phone.strip()
                )
                if ok:
                    st.success(
                        "Credentials updated! Please log in again with your new details."
                    )
                    st.session_state.admin_logged_in = False
                    st.session_state.admin_user = None
                    st.session_state.view = "admin_login"
                    st.rerun()
                else:
                    st.error(f"Update failed: {reason}")

# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════
v = st.session_state.view

if v == "student":
    student_view()
elif v == "admin_login":
    admin_login_view()
elif v == "admin_panel":
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
