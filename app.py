import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --------- Google Sheets Setup ---------
def load_google_sheet(sheet_url, worksheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["google"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(creds_dict), scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url)
    worksheet = sheet.worksheet(worksheet_name)
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

# --------- Load Data ---------
sheet_url = "https://docs.google.com/spreadsheets/d/1_hypJt1kwUNZE6Xck1VVjrPeYiIJpTDXSAwi4dgXXko"
worksheet_name = "Mixed Raw Candidate Data"
df = load_google_sheet(sheet_url, worksheet_name)

# --------- Clean & Prep ---------
df['Interview Score'] = pd.to_numeric(df['Interview Score'], errors='coerce')
df['Scorecard submitted'] = df['Scorecard submitted'].str.strip().str.lower()
df['Scorecard Complete'] = df['Scorecard submitted'] == 'yes'

# --------- Streamlit UI ---------
st.set_page_config(page_title="Recruiter Dashboard", layout="wide")

st.markdown(
    '''
    <style>
        body {
            background-color: #ffffff;
            color: #1a1a1a;
        }
        .stButton button {
            border: 1px solid #1e90ff;
            background-color: #ffffff;
            color: #1e90ff;
        }
    </style>
    ''',
    unsafe_allow_html=True
)

page = st.sidebar.selectbox("🔍 Navigate", ["Recruiter Dashboard", "Department Analytics"])

# ---------------- Recruiter Dashboard ----------------
if page == "Recruiter Dashboard":
    st.title("🎯 Recruiter Interview Dashboard")
    recruiters = sorted(df['Recruiter'].dropna().unique().tolist())
    selected_recruiter = st.sidebar.selectbox("👤 Choose Recruiter", recruiters)
    toggle_status = st.sidebar.radio("📋 Show Candidates With:", ["All", "Complete Scorecards", "Pending Scorecards"])

    grouped = df.groupby('Candidate Name').agg(
        Avg_Interview_Score=('Interview Score', 'mean'),
        Scorecards_Submitted=('Scorecard submitted', lambda x: sum(x == 'yes')),
        Total_Interviews=('Interview Score', 'count'),
        Department=('Department', 'first'),
        Recruiter=('Recruiter', 'first')
    ).reset_index()

    def make_decision(row):
        if row['Scorecards_Submitted'] < 4:
            return "🟡 Waiting for Interviews"
        elif row['Avg_Interview_Score'] <= 3.4:
            return "❌ Auto-Reject"
        elif row['Avg_Interview_Score'] >= 3.5:
            return "✅ HM Review"
        return "⚠️ Needs Discussion"

    grouped['Decision'] = grouped.apply(make_decision, axis=1)
    grouped = grouped[grouped['Recruiter'] == selected_recruiter]

    if toggle_status == "Complete Scorecards":
        grouped = grouped[grouped['Scorecards_Submitted'] == 4]
    elif toggle_status == "Pending Scorecards":
        grouped = grouped[grouped['Scorecards_Submitted'] < 4]

    st.subheader(f"📋 Candidate Summary for {selected_recruiter}")
    st.dataframe(grouped[['Candidate Name', 'Department', 'Avg_Interview_Score', 'Scorecards_Submitted', 'Decision']],
                 use_container_width=True)

    st.subheader("🧠 Candidate Details")
    for _, row in grouped.iterrows():
        with st.expander(f"{row['Candidate Name']} — {row['Decision']}"):
            st.markdown(f"**Department:** {row['Department']}")
            st.markdown(f"**Scorecards Submitted:** {row['Scorecards_Submitted']} / 4")
            st.markdown("---")
            st.markdown("### Interviewer Scores")
            candidate_rows = df[df['Candidate Name'] == row['Candidate Name']]
            for _, r in candidate_rows.iterrows():
                score = r['Interview Score']
                status = r['Scorecard submitted']
                line = f"- **{r['Internal Interviewer']}** ({r['Interview']})"
                if status == 'yes':
                    st.markdown(f"{line}: ✅ {score}")
                else:
                    st.markdown(f"{line}: ❌ Not Submitted")
                    st.button(f"📩 Send Reminder to {r['Internal Interviewer']}", key=f"{r['Candidate Name']}-{r['Internal Interviewer']}")

# ---------------- Department Analytics ----------------
elif page == "Department Analytics":
    st.title("📊 Department Scorecard Analytics")

    dept_summary = df.groupby('Department').agg(
        Total_Interviews=('Interview Score', 'count'),
        Completed=('Scorecard Complete', 'sum'),
        Avg_Score=('Interview Score', 'mean')
    ).reset_index()
    dept_summary['Completion Rate (%)'] = round(100 * dept_summary['Completed'] / dept_summary['Total_Interviews'], 1)

    st.subheader("✅ Scorecard Submission Rate by Department")
    st.dataframe(dept_summary[['Department', 'Total_Interviews', 'Completed', 'Completion Rate (%)', 'Avg_Score']],
                 use_container_width=True)

    st.subheader("👥 Internal Interviewer Stats")
    interviewer_summary = df.groupby('Internal Interviewer').agg(
        Interviews_Conducted=('Interview', 'count'),
        Scorecards_Submitted=('Scorecard Complete', 'sum'),
        Avg_Interview_Score=('Interview Score', 'mean')
    ).reset_index()

    st.dataframe(interviewer_summary, use_container_width=True)
