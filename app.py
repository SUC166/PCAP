import streamlit as st
import pandas as pd

st.set_page_config(page_title="FUTO PCAP", page_icon="🎓", layout="centered")

CSS = (
    "<style>"
    "@import url(https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap);"
    "html,body,[class*=css]{font-family:Inter,sans-serif}"
    ".hdr{background:linear-gradient(135deg,#006633,#009933 60%,#00cc44);border-radius:16px;padding:2rem 2.5rem;text-align:center;margin-bottom:2rem;box-shadow:0 8px 32px rgba(0,102,51,.18)}"
    ".hdr h1{color:#fff;font-size:2rem;font-weight:700;margin:0;letter-spacing:1px}"
    ".hdr p{color:#d4f5d4;font-size:.95rem;margin:.4rem 0 0}"
    ".ok-card{background:#f0faf4;border-left:5px solid #006633;border-radius:10px;padding:1.2rem 1.5rem;margin-bottom:.5rem}"
    ".ok-card h3{color:#006633;margin:0 0 .5rem;font-size:1.1rem}"
    ".ok-card p{margin:.2rem 0;color:#333;font-size:.92rem}"
    ".badge{background:#006633;color:#fff;border-radius:20px;padding:3px 14px;font-size:.8rem;font-weight:600}"
    ".err-card{background:#fff5f5;border-left:5px solid #c00;border-radius:10px;padding:1.2rem 1.5rem;margin-bottom:.5rem}"
    ".err-card h4{color:#c00;margin:0 0 .4rem}"
    ".err-card p{margin:.2rem 0;color:#555;font-size:.91rem}"
    ".info{background:#fffbe6;border-left:5px solid #f0a500;border-radius:10px;padding:1rem 1.4rem;margin-bottom:1rem}"
    ".notice{background:linear-gradient(90deg,#006633,#009933);color:#fff;border-radius:10px;padding:1rem 1.4rem;text-align:center;font-weight:600;font-size:1rem;margin-top:.5rem;margin-bottom:1.5rem}"
    ".stButton>button{background:#006633;color:#fff;border-radius:8px;border:none;padding:.5rem 2rem;font-weight:600;font-size:1rem;width:100%}"
    ".stButton>button:hover{background:#009933}"
    "</style>"
)

st.markdown(CSS, unsafe_allow_html=True)
st.markdown(
    "<div class=hdr><h1>&#127891; FUTO PCAP</h1>"
    "<p>Federal University of Technology Owerri &nbsp;|&nbsp; Physical Clearance Assistance Platform</p></div>",
    unsafe_allow_html=True
)

st.markdown("#### &#128194; Upload Clearance Data")
uploaded_file = st.file_uploader(
    "Upload the student clearance CSV file", type=["csv"],
    help="Required columns: Name, Matric_Number, Jamb_Reg, Department, Olevel, School_Fees, Jamb"
)

if uploaded_file is None:
    st.markdown(
        "<div class=info><strong>Expected CSV columns:</strong><br>"
        "<code>Name</code>, <code>Matric_Number</code>, <code>Jamb_Reg</code>, "
        "<code>Department</code>, <code>Olevel</code>, <code>School_Fees</code>, <code>Jamb</code><br><br>"
        "The last three qualifier columns should contain <code>True</code> or <code>False</code>.</div>",
        unsafe_allow_html=True
    )
    st.stop()

try:
    df = pd.read_csv(uploaded_file)
    df.columns = df.columns.str.strip()
    required = {"Name","Matric_Number","Jamb_Reg","Department","Olevel","School_Fees","Jamb"}
    missing = required - set(df.columns)
    if missing:
        st.error(f"Missing columns: {chr(39)}{chr(44).join(missing)}{chr(39)}")
        st.stop()
    bmap = {"true":True,"1":True,"yes":True,"false":False,"0":False,"no":False}
    for c in ["Olevel","School_Fees","Jamb"]:
        df[c] = df[c].astype(str).str.strip().str.lower().map(bmap)
    st.success(f"CSV loaded — {len(df)} student records found.")
except Exception as e:
    st.error(f"Error reading CSV: {e}")
    st.stop()

st.divider()
st.markdown("#### &#128269; Check Your Clearance Status")
search_term = st.text_input(
    "Enter your Name, Matric Number, or JAMB Reg Number",
    placeholder="e.g. John Doe  |  FUT/CS/2023/001  |  12345678AB"
)
search_btn = st.button("Check Status")

if search_btn:
    if not search_term.strip():
        st.warning("Please enter your name, matric number, or JAMB reg number.")
    else:
        term = search_term.strip().lower()
        mask = (
            df["Name"].astype(str).str.lower().str.contains(term, na=False) |
            df["Matric_Number"].astype(str).str.lower().str.contains(term, na=False) |
            df["Jamb_Reg"].astype(str).str.lower().str.contains(term, na=False)
        )
        results = df[mask]
        if results.empty:
            st.warning("No record found. Please check your details and try again.")
        else:
            st.markdown(f"**{len(results)} record(s) found:**")
            for _, row in results.iterrows():
                olvl = row["Olevel"] is True
                fees = row["School_Fees"] is True
                jamb = row["Jamb"] is True
                name = row["Name"]
                dept = row["Department"]
                matric = row["Matric_Number"]
                jamb_reg = row["Jamb_Reg"]
                if olvl and fees and jamb:
                    st.markdown(
                        f"<div class=ok-card><h3>{name} <span class=badge>CLEARED</span></h3>"
                        f"<p>Department: <strong>{dept}</strong></p>"
                        f"<p>Matric Number: <strong>{matric}</strong></p>"
                        f"<p>JAMB Reg Number: <strong>{jamb_reg}</strong></p></div>"
                        "<div class=notice>You are CLEARED for Physical Clearance. "
                        "Please be present at the designated venue with all required documents.</div>",
                        unsafe_allow_html=True
                    )
                else:
                    ih = ""
                    if not fees:
                        ih += "<p><strong>School Fees Not Paid</strong> &mdash; Please pay via the university payment portal and allow time for confirmation.</p>"
                    if not jamb:
                        ih += "<p><strong>JAMB Admission Not Confirmed</strong> &mdash; Visit the JAMB portal or admissions office to confirm your admission.</p>"
                    if not olvl:
                        ih += "<p><strong>O Level Results Not Verified</strong> &mdash; Submit your result(s) to the admissions office. Wait a little longer if recently submitted.</p>"
                    st.markdown(
                        f"<div class=err-card><h4>Not Yet Cleared &mdash; {name}</h4>"
                        f"<p>Matric: <strong>{matric}</strong> | JAMB: <strong>{jamb_reg}</strong></p>"
                        "<hr style=border:0;border-top:1px solid #f5c6c6;margin:.6rem 0>"
                        f"<p><strong>Please resolve the following:</strong></p>{ih}"
                        "<p style=color:#888;font-size:.85rem>Resolve the above and check back. Contact admissions if you believe this is an error.</p></div>",
                        unsafe_allow_html=True
                    )

st.divider()
st.markdown(
    "<p style=text-align:center;color:#aaa;font-size:.82rem>"
    "FUTO Physical Clearance Assistance Platform (PCAP) &copy; 2025 &nbsp;|&nbsp; Federal University of Technology Owerri</p>",
    unsafe_allow_html=True
)
