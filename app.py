import streamlit as st
import pandas as pd
import re
import io

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
.del-btn button{background:#c00 !important}
.del-btn button:hover{background:#990000 !important}
.ftr{text-align:center;color:#aaa;font-size:.8rem;margin-top:2.5rem}
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
DEPARTMENTS = [
    "Agribusiness", "Agricultural Economics", "Agricultural Extension",
    "Agricultural and Bioresources Engineering", "Animal Science and Technology",
    "Architecture", "Biochemistry", "Biology", "Biotechnology",
    "Computer Engineering", "Computer Science", "Cyber Security",
    "Chemical Engineering", "Chemistry", "Civil Engineering",
    "Crop Science and Technology", "Dental Technology",
    "Electrical (Power Systems) Engineering", "Electronics Engineering",
    "Entrepreneurship and Innovation", "Environmental Health Science",
    "Environmental Management", "Forensic Science",
    "Fisheries and Aquaculture Technology", "Food Science and Technology",
    "Forestry and Wildlife Technology", "Geology", "Human Anatomy",
    "Human Physiology", "Information Technology",
    "Logistics and Transport Technology", "Maritime Technology and Logistics",
    "Material and Metallurgical Engineering", "Mathematics",
    "Mechanical Engineering", "Mechatronics Engineering", "Microbiology",
    "Optometry", "Petroleum Engineering", "Polymer and Textile Engineering",
    "Project Management Technology", "Prosthetics and Orthotics",
    "Public Health Technology", "Quantity Surveying",
    "Science Laboratory Technology", "Soil Science and Technology",
    "Software Engineering", "Statistics", "Surveying and Geoinformatics",
    "Telecommunications Engineering", "Urban and Regional Planning",
]

CSV_COLS = ["SN", "Name", "Matric_Number", "Jamb_Reg", "Department",
            "Olevel", "School_Fees", "Jamb"]

BOOL_MAP = {"true": True, "1": True, "yes": True,
            "false": False, "0": False, "no": False}

# ── Session state ──────────────────────────────────────────────────────────────
for k, v in {
    "admin_logged_in": False,
    "admin_user": None,
    "csv_df": None,
    "view": "student",
    "edit_sn": None,       # SN of row being edited
    "confirm_del": None,   # SN of row pending delete confirmation
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Helper: ensure df has SN column and is clean ───────────────────────────────
def normalise_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "SN" not in df.columns:
        df.insert(0, "SN", range(1, len(df) + 1))
    for c in ["Olevel", "School_Fees", "Jamb"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip().str.lower().map(BOOL_MAP)
    df["SN"] = pd.to_numeric(df["SN"], errors="coerce").fillna(0).astype(int)
    return df

def next_sn(df: pd.DataFrame) -> int:
    if df is None or df.empty or "SN" not in df.columns:
        return 1
    return int(df["SN"].max()) + 1

def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    "<div class='hdr'><h1>\U0001F393 FUTO PCAP</h1>"
    "<p>Federal University of Technology Owerri &nbsp;|&nbsp; "
    "Physical Clearance Assistance Platform</p></div>",
    unsafe_allow_html=True,
)

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
# SETUP GUIDE
# ══════════════════════════════════════════════════════════════════════════════
def setup_guide():
    st.markdown("""
<div class="setup-box">
<h4>⚙️ Setup Required — GitHub Secrets Not Configured</h4>
<p>Go to your Streamlit Cloud dashboard → app → <strong>Settings → Secrets</strong> and paste:</p>
<pre>[github]
token = "ghp_your_token_here"
repo  = "your_github_username/pcap-data"
admins_path = "admins.json"</pre>
<p>Save and reboot the app.</p>
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
    st.caption("Search by Surname, full name, 11-digit Matric Number, or 12-character JAMB Reg Number.")
    search_term = st.text_input("Search", placeholder="e.g. Okafor  |  20251515463  |  202550551834BF",
                                label_visibility="collapsed")
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
        st.warning("No record found. Please verify your details or contact the Admissions Office.")
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
                ih += ("<p><strong>\U0001F4B3 School Fees Not Paid</strong> &mdash; "
                       "Pay via the university payment portal and allow 24&ndash;48 hours for confirmation.</p>")
            if not jamb:
                ih += ("<p><strong>\U0001F4CB JAMB Admission Not Confirmed</strong> &mdash; "
                       "Visit <em>jamb.gov.ng</em> or the Admissions Office to confirm your admission.</p>")
            if not olvl:
                ih += ("<p><strong>\U0001F4DA O&rsquo;Level Results Not Verified</strong> &mdash; "
                       "Submit your original result(s) to the Admissions Office. "
                       "Wait a little longer if recently submitted.</p>")
            st.markdown(
                f"<div class='err-card'>"
                f"<h4>\u274C Not Yet Eligible &mdash; {name}</h4>"
                f"<p>Matric: <strong>{mat}</strong> &nbsp;|&nbsp; JAMB: <strong>{jreg}</strong></p>"
                f"<hr style='border:0;border-top:1px solid #f5c6c6;margin:.6rem 0'>"
                f"<p><strong>Action required:</strong></p>{ih}"
                f"<p style='color:#888;font-size:.84rem;margin-top:.4rem'>"
                f"Resolve the above and check again. Contact the Admissions Office if you believe this is an error.</p>"
                f"</div>",
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN LOGIN VIEW
# ══════════════════════════════════════════════════════════════════════════════
def admin_login_view():
    from github_store import secrets_configured, verify_admin, bootstrap_needed

    st.markdown("#### \U0001F512 Admin Login")
    if not secrets_configured():
        setup_guide()
        return

    try:
        is_bootstrap = bootstrap_needed()
    except Exception as e:
        st.error(f"Could not connect to GitHub. Check your token and repo.\n\n`{e}`")
        return

    if is_bootstrap:
        st.info(
            "**First-time setup:** No admins exist yet.\n\n"
            "**Username:** `pcap_bootstrap`  \n**Password:** `FUTOpcap2025!`\n\n"
            "> Create your permanent account immediately after logging in."
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
    from github_store import secrets_configured, load_admins, create_admin, update_admin_credentials

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

    tab1, tab2, tab3, tab4 = st.tabs([
        "\U0001F4CB Student Records",
        "\U0001F4C2 Import CSV",
        "\U0001F468\u200D\U0001F4BB Manage Admins",
        "\U0001F510 My Account",
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — STUDENT RECORDS (Add / Search / Edit / Delete)
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        df = st.session_state.csv_df

        # ── Stats bar ──────────────────────────────────────────────────────
        if df is not None and not df.empty:
            eligible = df[(df["Olevel"]==True)&(df["School_Fees"]==True)&(df["Jamb"]==True)]
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Students", len(df))
            c2.metric("Eligible", len(eligible))
            c3.metric("Pending", len(df) - len(eligible))
            st.divider()

        # ── Search bar ─────────────────────────────────────────────────────
        st.markdown("##### \U0001F50D Search Students")
        srch = st.text_input("Search by name, matric, JAMB reg, department, or S/N",
                              key="admin_search", placeholder="Type anything...")

        if df is not None and not df.empty and srch.strip():
            t = srch.strip().lower()
            mask = pd.Series([False]*len(df), index=df.index)
            for col in ["SN","Name","Matric_Number","Jamb_Reg","Department"]:
                if col in df.columns:
                    mask |= df[col].astype(str).str.lower().str.contains(t, na=False)
            found = df[mask]
            if found.empty:
                st.warning("No students match your search.")
            else:
                st.caption(f"{len(found)} result(s) found")
                _render_student_table(found)
        elif df is not None and not df.empty:
            st.caption(f"Showing all {len(df)} records")
            _render_student_table(df)
        else:
            st.info("No student records loaded yet. Add a student below or import a CSV.")

        st.divider()

        # ── Add new student ────────────────────────────────────────────────
        st.markdown("##### \U0001F4CB Add New Student")
        with st.form("add_student_form", clear_on_submit=True):
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                a_surname  = st.text_input("Surname *")
            with fc2:
                a_first    = st.text_input("First Name *")
            with fc3:
                a_middle   = st.text_input("Middle Name")

            fa1, fa2 = st.columns(2)
            with fa1:
                a_matric = st.text_input("Matric Number *", placeholder="20251515463",
                                         help="Exactly 11 digits")
            with fa2:
                a_jamb   = st.text_input("JAMB Reg Number *", placeholder="202550551834BF",
                                         help="10 digits + 2 letters")

            a_dept = st.selectbox("Department *", DEPARTMENTS)

            fb1, fb2, fb3 = st.columns(3)
            with fb1:
                a_olevel = st.selectbox("O'Level Verified", ["False","True"], key="add_olevel")
            with fb2:
                a_fees   = st.selectbox("School Fees Paid", ["False","True"], key="add_fees")
            with fb3:
                a_jamb_s = st.selectbox("JAMB Confirmed", ["False","True"], key="add_jamb")

            add_btn = st.form_submit_button("\u2795 Add Student", use_container_width=True)

        if add_btn:
            errs = []
            if not a_surname.strip():  errs.append("Surname is required.")
            if not a_first.strip():    errs.append("First name is required.")
            if not re.match(r"^\d{11}$", a_matric.strip()):
                errs.append("Matric Number must be exactly 11 digits.")
            if not re.match(r"^\d{10}[A-Za-z]{2}$", a_jamb.strip()):
                errs.append("JAMB Reg must be 10 digits followed by 2 letters.")

            # Check duplicates
            if df is not None and not df.empty:
                if a_matric.strip() in df["Matric_Number"].astype(str).values:
                    errs.append(f"Matric Number {a_matric.strip()} already exists.")
                if a_jamb.strip().upper() in df["Jamb_Reg"].astype(str).str.upper().values:
                    errs.append(f"JAMB Reg {a_jamb.strip()} already exists.")

            if errs:
                for e in errs:
                    st.error(e)
            else:
                parts = [a_surname.strip(), a_first.strip()]
                if a_middle.strip():
                    parts.append(a_middle.strip())
                full_name = " ".join(parts)
                new_sn = next_sn(df)
                new_row = {
                    "SN": new_sn,
                    "Name": full_name,
                    "Matric_Number": a_matric.strip(),
                    "Jamb_Reg": a_jamb.strip().upper(),
                    "Department": a_dept,
                    "Olevel": a_olevel == "True",
                    "School_Fees": a_fees == "True",
                    "Jamb": a_jamb_s == "True",
                }
                if df is None or df.empty:
                    st.session_state.csv_df = pd.DataFrame([new_row])
                else:
                    st.session_state.csv_df = pd.concat(
                        [df, pd.DataFrame([new_row])], ignore_index=True
                    )
                st.success(f"\u2705 {full_name} added with S/N {new_sn}.")
                st.rerun()

        # ── Download button ────────────────────────────────────────────────
        if st.session_state.csv_df is not None and not st.session_state.csv_df.empty:
            st.divider()
            csv_bytes = df_to_csv_bytes(st.session_state.csv_df)
            st.download_button(
                label="\U0001F4E5 Download Current CSV",
                data=csv_bytes,
                file_name="pcap_students.csv",
                mime="text/csv",
                use_container_width=True,
            )

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — IMPORT CSV
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("##### Import / Replace from CSV File")
        st.markdown(
            "<div class='info-box'>"
            "<strong>Required columns:</strong> "
            "<code>Name</code>, <code>Matric_Number</code>, <code>Jamb_Reg</code>, "
            "<code>Department</code>, <code>Olevel</code>, <code>School_Fees</code>, <code>Jamb</code>"
            "<br>Optional: <code>SN</code> (will be auto-assigned if missing)"
            "</div>",
            unsafe_allow_html=True,
        )
        uploaded = st.file_uploader("Upload CSV", type=["csv"], key="admin_csv_import")
        if uploaded:
            try:
                raw = pd.read_csv(uploaded)
                raw.columns = raw.columns.str.strip()
                required = {"Name","Matric_Number","Jamb_Reg","Department","Olevel","School_Fees","Jamb"}
                missing = required - set(raw.columns)
                if missing:
                    st.error(f"Missing columns: {', '.join(sorted(missing))}")
                else:
                    bad_m = raw[~raw["Matric_Number"].astype(str).str.match(r"^\d{11}$")]
                    bad_j = raw[~raw["Jamb_Reg"].astype(str).str.match(r"^\d{10}[A-Za-z]{2}$")]
                    if not bad_m.empty:
                        st.warning(f"\u26A0\uFE0F {len(bad_m)} invalid Matric Number(s): {bad_m['Name'].tolist()}")
                    if not bad_j.empty:
                        st.warning(f"\u26A0\uFE0F {len(bad_j)} invalid JAMB Reg(s): {bad_j['Name'].tolist()}")
                    clean = normalise_df(raw)
                    st.session_state.csv_df = clean
                    eligible_n = len(clean[(clean["Olevel"]==True)&(clean["School_Fees"]==True)&(clean["Jamb"]==True)])
                    st.success(f"\u2705 Imported {len(clean)} records — {eligible_n} eligible.")
                    st.dataframe(clean, use_container_width=True)
            except Exception as e:
                st.error(f"Error reading CSV: {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — MANAGE ADMINS
    # ══════════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("##### Create a New Admin Account")
        st.caption("Phone, username, creation time, and your username are saved to GitHub automatically.")

        with st.form("create_admin_form", clear_on_submit=True):
            new_phone = st.text_input("Phone Number", placeholder="+2348118429150",
                                      help="Include country code")
            new_uname = st.text_input("Username")
            new_pass  = st.text_input("Password", type="password")
            new_pass2 = st.text_input("Confirm Password", type="password")
            create_btn = st.form_submit_button("Create Admin", use_container_width=True)

        if create_btn:
            errs = []
            if not new_phone.strip():
                errs.append("Phone number is required.")
            elif not re.match(r"^\+\d{7,15}$", new_phone.strip()):
                errs.append("Phone must start with + followed by 7–15 digits.")
            if not new_uname.strip() or len(new_uname.strip()) < 3:
                errs.append("Username must be at least 3 characters.")
            if len(new_pass) < 8:
                errs.append("Password must be at least 8 characters.")
            if new_pass != new_pass2:
                errs.append("Passwords do not match.")
            if errs:
                for e in errs: st.error(e)
            else:
                try:
                    ok, reason = create_admin(new_uname.strip(), new_pass,
                                              new_phone.strip(), admin["username"])
                    if ok:
                        st.success(f"\u2705 Admin **{new_uname.strip()}** created successfully.")
                    else:
                        st.error(f"Could not create admin: {reason}")
                except Exception as e:
                    st.error(f"GitHub error: {e}")

        st.markdown("---")
        st.markdown("##### Existing Admins")
        try:
            admins_list = load_admins()
            if admins_list:
                st.dataframe(pd.DataFrame([{
                    "Username": a["username"],
                    "Phone": a.get("phone",""),
                    "Created By": a.get("created_by","—"),
                    "Created At (UTC)": a.get("created_at","—"),
                } for a in admins_list]), use_container_width=True)
            else:
                st.info("No admins in GitHub store yet.")
        except Exception as e:
            st.error(f"Could not load admin list: {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4 — MY ACCOUNT
    # ══════════════════════════════════════════════════════════════════════════
    with tab4:
        st.markdown("##### Update Your Own Credentials")
        st.caption("\u26A0\uFE0F You can only modify your own account. You will be logged out after saving.")

        with st.form("update_self_form"):
            upd_phone = st.text_input("Phone Number", value=admin.get("phone",""),
                                      placeholder="+2348118429150")
            upd_uname = st.text_input("Username", value=admin.get("username",""))
            upd_pass  = st.text_input("New Password", type="password")
            upd_pass2 = st.text_input("Confirm New Password", type="password")
            upd_btn   = st.form_submit_button("Save Changes", use_container_width=True)

        if upd_btn:
            errs = []
            if not upd_phone.strip():
                errs.append("Phone number is required.")
            elif not re.match(r"^\+\d{7,15}$", upd_phone.strip()):
                errs.append("Phone must start with + followed by 7–15 digits.")
            if not upd_uname.strip() or len(upd_uname.strip()) < 3:
                errs.append("Username must be at least 3 characters.")
            if len(upd_pass) < 8:
                errs.append("Password must be at least 8 characters.")
            if upd_pass != upd_pass2:
                errs.append("Passwords do not match.")
            if errs:
                for e in errs: st.error(e)
            else:
                try:
                    ok, reason = update_admin_credentials(
                        admin["username"], upd_uname.strip(), upd_pass, upd_phone.strip())
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


# ── Student table renderer (with Edit / Delete inline) ─────────────────────────
def _render_student_table(df: pd.DataFrame):
    """Render a table of students with per-row Edit and Delete buttons."""
    # Header row
    h0,h1,h2,h3,h4,h5,h6,h7,h8,h9 = st.columns([0.6,2.2,1.3,1.4,2,0.7,0.7,0.7,0.7,0.7])
    h0.markdown("**S/N**"); h1.markdown("**Name**"); h2.markdown("**Matric**")
    h3.markdown("**JAMB**"); h4.markdown("**Dept**"); h5.markdown("**O'Lvl**")
    h6.markdown("**Fees**"); h7.markdown("**JAMB✓**"); h8.markdown("**Edit**")
    h9.markdown("**Del**")
    st.markdown("<hr style='margin:.2rem 0'>", unsafe_allow_html=True)

    for idx, row in df.iterrows():
        sn   = int(row["SN"])
        olvl = row["Olevel"] is True
        fees = row["School_Fees"] is True
        jamb = row["Jamb"] is True

        c0,c1,c2,c3,c4,c5,c6,c7,c8,c9 = st.columns([0.6,2.2,1.3,1.4,2,0.7,0.7,0.7,0.7,0.7])
        c0.write(sn)
        c1.write(str(row["Name"]))
        c2.write(str(row["Matric_Number"]))
        c3.write(str(row["Jamb_Reg"]))
        c4.write(str(row["Department"]))
        c5.write("✅" if olvl else "❌")
        c6.write("✅" if fees else "❌")
        c7.write("✅" if jamb else "❌")

        if c8.button("✏️", key=f"edit_{sn}_{idx}", help=f"Edit S/N {sn}"):
            st.session_state.edit_sn = sn
            st.session_state.confirm_del = None
            st.rerun()

        if c9.button("🗑️", key=f"del_{sn}_{idx}", help=f"Delete S/N {sn}"):
            st.session_state.confirm_del = sn
            st.session_state.edit_sn = None
            st.rerun()

    # ── Edit form ──────────────────────────────────────────────────────────
    edit_sn = st.session_state.get("edit_sn")
    if edit_sn is not None:
        full_df = st.session_state.csv_df
        row_mask = full_df["SN"] == edit_sn
        if row_mask.sum() == 0:
            st.session_state.edit_sn = None
        else:
            row = full_df[row_mask].iloc[0]
            name_parts = str(row["Name"]).split(" ", 2)
            e_surname = name_parts[0] if len(name_parts) > 0 else ""
            e_first   = name_parts[1] if len(name_parts) > 1 else ""
            e_middle  = name_parts[2] if len(name_parts) > 2 else ""

            st.markdown(f"---\n##### ✏️ Editing S/N {edit_sn} — {row['Name']}")
            with st.form(f"edit_form_{edit_sn}"):
                ec1, ec2, ec3 = st.columns(3)
                with ec1: e_sur = st.text_input("Surname *", value=e_surname)
                with ec2: e_fst = st.text_input("First Name *", value=e_first)
                with ec3: e_mid = st.text_input("Middle Name", value=e_middle)

                ea1, ea2 = st.columns(2)
                with ea1:
                    e_mat = st.text_input("Matric Number *", value=str(row["Matric_Number"]))
                with ea2:
                    e_jmb = st.text_input("JAMB Reg *", value=str(row["Jamb_Reg"]))

                dept_idx = DEPARTMENTS.index(row["Department"]) if row["Department"] in DEPARTMENTS else 0
                e_dept = st.selectbox("Department *", DEPARTMENTS, index=dept_idx)

                eb1, eb2, eb3 = st.columns(3)
                with eb1:
                    e_olvl = st.selectbox("O'Level Verified", ["True","False"],
                                          index=0 if row["Olevel"] is True else 1)
                with eb2:
                    e_fees = st.selectbox("School Fees Paid", ["True","False"],
                                          index=0 if row["School_Fees"] is True else 1)
                with eb3:
                    e_jamb = st.selectbox("JAMB Confirmed", ["True","False"],
                                          index=0 if row["Jamb"] is True else 1)

                save_col, cancel_col = st.columns(2)
                with save_col:
                    save_btn = st.form_submit_button("💾 Save Changes", use_container_width=True)
                with cancel_col:
                    cancel_btn = st.form_submit_button("✖ Cancel", use_container_width=True)

            if cancel_btn:
                st.session_state.edit_sn = None
                st.rerun()

            if save_btn:
                errs = []
                if not e_sur.strip(): errs.append("Surname is required.")
                if not e_fst.strip(): errs.append("First name is required.")
                if not re.match(r"^\d{11}$", e_mat.strip()):
                    errs.append("Matric Number must be exactly 11 digits.")
                if not re.match(r"^\d{10}[A-Za-z]{2}$", e_jmb.strip()):
                    errs.append("JAMB Reg must be 10 digits + 2 letters.")
                # Duplicate check (excluding current row)
                others = full_df[full_df["SN"] != edit_sn]
                if e_mat.strip() in others["Matric_Number"].astype(str).values:
                    errs.append(f"Matric Number {e_mat.strip()} belongs to another student.")
                if e_jmb.strip().upper() in others["Jamb_Reg"].astype(str).str.upper().values:
                    errs.append(f"JAMB Reg {e_jmb.strip()} belongs to another student.")

                if errs:
                    for e in errs: st.error(e)
                else:
                    parts = [e_sur.strip(), e_fst.strip()]
                    if e_mid.strip(): parts.append(e_mid.strip())
                    full_df.loc[row_mask, "Name"]         = " ".join(parts)
                    full_df.loc[row_mask, "Matric_Number"]= e_mat.strip()
                    full_df.loc[row_mask, "Jamb_Reg"]     = e_jmb.strip().upper()
                    full_df.loc[row_mask, "Department"]   = e_dept
                    full_df.loc[row_mask, "Olevel"]       = e_olvl == "True"
                    full_df.loc[row_mask, "School_Fees"]  = e_fees == "True"
                    full_df.loc[row_mask, "Jamb"]         = e_jamb == "True"
                    st.session_state.csv_df = full_df
                    st.session_state.edit_sn = None
                    st.success(f"✅ S/N {edit_sn} updated successfully.")
                    st.rerun()

    # ── Delete confirmation ────────────────────────────────────────────────
    del_sn = st.session_state.get("confirm_del")
    if del_sn is not None:
        full_df = st.session_state.csv_df
        row_mask = full_df["SN"] == del_sn
        if row_mask.sum() > 0:
            del_name = full_df[row_mask].iloc[0]["Name"]
            st.markdown(f"---")
            st.warning(
                f"⚠️ Are you sure you want to delete **{del_name}** (S/N {del_sn})? "
                f"This cannot be undone."
            )
            dc1, dc2 = st.columns(2)
            with dc1:
                if st.button("🗑️ Yes, Delete", key=f"confirm_del_yes_{del_sn}", use_container_width=True):
                    st.session_state.csv_df = full_df[~row_mask].reset_index(drop=True)
                    st.session_state.confirm_del = None
                    st.success(f"🗑️ {del_name} (S/N {del_sn}) has been removed.")
                    st.rerun()
            with dc2:
                if st.button("✖ Cancel", key=f"confirm_del_no_{del_sn}", use_container_width=True):
                    st.session_state.confirm_del = None
                    st.rerun()


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

st.markdown(
    "<div class='ftr'>FUTO Physical Clearance Assistance Platform (PCAP) "
    "&copy; 2025 &nbsp;|&nbsp; Federal University of Technology Owerri</div>",
    unsafe_allow_html=True,
)
