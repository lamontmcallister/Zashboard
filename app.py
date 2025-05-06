# recruiter_dashboard.py
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ----------------- Page Setup -----------------
st.set_page_config(page_title="Recruiter Platform", layout="wide")

# ----------------- Data Loading -----------------
@st.cache_data(ttl=600)
def load_google_sheet(sheet_url, worksheet_name):
    """Load data from a Google Sheet."""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["google"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(creds_dict), scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url)
    worksheet = sheet.worksheet(worksheet_name)
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

# ----------------- Data Preparation -----------------
def prepare_dataframe(df):
    df['Interview Score'] = pd.to_numeric(df['Interview Score'], errors='coerce')
    df['Scorecard submitted'] = df['Scorecard submitted'].str.strip().str.lower()
    df['Scorecard Complete'] = df['Scorecard submitted'] == 'yes'
    return df

def make_decision(row):
    if row['Scorecards_Submitted'] < 4:
        return "🟡 Waiting for Interviews"
    elif row['Avg_Interview_Score'] <= 3.4:
        return "❌ Auto-Reject"
    elif row['Avg_Interview_Score'] >= 3.5:
        return "✅ HM Review"
    return "⚠️ Needs Discussion"

# ----------------- UI Styling -----------------
st.markdown('''
<style>
    .stButton button {
        border: 1px solid #1e90ff;
        background-color: #ffffff;
        color: #1e90ff;
    }
    th { font-weight: bold; background-color: #f0f8ff; }
    td { text-align: center !important; }
</style>
''', unsafe_allow_html=True)

# ----------------- Load Data -----------------
sheet_url = "https://docs.google.com/spreadsheets/d/1_hypJt1kwUNZE6Xck1VVjrPeYiIJpTDXSAwi4dgXXko"
worksheet_name = "Mixed Raw Candidate Data"
df = prepare_dataframe(load_google_sheet(sheet_url, worksheet_name))
departments = sorted(df['Department'].dropna().unique().tolist())

# ----------------- Tabs -----------------
tab1, tab2, tab3, tab4 = st.tabs([
    "🔰 Landing Page",
    "Scorecard Dashboard",
    "📊 Department Analytics",
    "📈 Success Metrics Overview"
])

# ----------------- Landing Page -----------------
with tab1:
    st.title("🚀 Hiring Decision Engine")
    st.markdown("""BrightHire eliminates the need for debrief meetings — but how do we maintain structure in hiring decisions?

This dashboard is the **Decision Engine** for async, scorecard-driven hiring.  
It can be extended to **integrate with Workday** to automatically sync candidates, scorecards, and hiring decisions — ensuring data consistency from interview to offer.
""")

    st.subheader("💡 Key Use Cases")
    st.markdown("""
    - **Track scorecard submission** in real time  
    - **Benchmark interview performance** to auto-approve or reject  
    - **Replace the debrief** with a structured async summary  
    - **Hold departments accountable** for completion and fairness  
    """)

    st.subheader("📈 What You’ll Find Inside")
    st.markdown("""
    - **Scorecard Dashboard:** Filterable recruiter view with reminders  
    - **Department Analytics:** Completion rates, interviewer stats, time saved  
    - **Success Metrics:** KPIs for hiring velocity and quality  
    """)

    st.success("This dashboard supports BrightHire adoption by making async decisions confident, consistent, and fast.")


# ----------------- Scorecard Dashboard -----------------
with tab2:
    st.title("🎯 Scorecard Dashboard")
    recruiters = sorted(df['Recruiter'].dropna().unique().tolist())

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        selected_recruiter = st.selectbox("👤 Choose Recruiter", recruiters)
    with col2:
        selected_depts = st.multiselect("🏢 Filter by Department", departments, default=departments)
    with col3:
        toggle_status = st.radio("📋 Show Candidates With", ["Complete Scorecards", "Pending Scorecards", "All"], index=0)

    grouped = df.groupby('Candidate Name').agg(
        Avg_Interview_Score=('Interview Score', 'mean'),
        Scorecards_Submitted=('Scorecard submitted', lambda x: sum(x == 'yes')),
        Total_Interviews=('Interview Score', 'count'),
        Department=('Department', 'first'),
        Recruiter=('Recruiter', 'first')
    ).reset_index()

    grouped['Decision'] = grouped.apply(make_decision, axis=1)
    grouped = grouped[(grouped['Recruiter'] == selected_recruiter) &
                      (grouped['Department'].isin(selected_depts))]

    if toggle_status == "Complete Scorecards":
        grouped = grouped[grouped['Scorecards_Submitted'] == 4]
    elif toggle_status == "Pending Scorecards":
        grouped = grouped[grouped['Scorecards_Submitted'] < 4]

    st.subheader(f"📋 Candidate Summary for {selected_recruiter}")
    st.dataframe(grouped[['Candidate Name', 'Department', 'Avg_Interview_Score', 'Scorecards_Submitted', 'Decision']],
                use_container_width=True)

    csv = grouped.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Results", data=csv, file_name="scorecard_summary.csv")

    st.subheader("🧠 Candidate Details")
    for _, row in grouped.iterrows():
        with st.expander(f"{row['Candidate Name']} — {row['Decision']}"):
            st.markdown(f"**Department:** {row['Department']}")
            st.markdown(f"**Scorecards Submitted:** {row['Scorecards_Submitted']} / 4")
            st.markdown("---")
            st.markdown("### Interviewer Scores")

            candidate_rows = df[df['Candidate Name'] == row['Candidate Name']]
            interviewer_dict = {}

            for _, r in candidate_rows.iterrows():
                interviewer = r['Internal Interviewer']
                submitted = str(r['Scorecard submitted']).strip().lower() == 'yes'
                score = r['Interview Score']
                interview_label = r['Interview']
                if interviewer not in interviewer_dict or submitted:
                    interviewer_dict[interviewer] = {
                        'submitted': submitted,
                        'score': score if submitted else None,
                        'interview': interview_label
                    }

            for interviewer, data in interviewer_dict.items():
                line = f"- **{interviewer}** ({data['interview']})"
                if data['submitted']:
                    st.markdown(f"{line}: ✅ {data['score']}")
                else:
                    st.markdown(f"{line}: ❌ Not Submitted")
                    st.button(f"📩 Send Reminder to {interviewer}", key=f"{row['Candidate Name']}-{interviewer}")

# ----------------- Department Analytics -----------------
with tab3:
    st.title("📊 Department Scorecard Analytics")

    dept_summary = df.groupby('Department').agg(
        Total_Interviews=('Interview Score', 'count'),
        Completed=('Scorecard Complete', 'sum'),
        Avg_Score=('Interview Score', 'mean')
    ).reset_index()
    dept_summary['Completion Rate (%)'] = round(100 * dept_summary['Completed'] / dept_summary['Total_Interviews'], 1)

    st.subheader("✅ Scorecard Submission Rate by Department")
    st.dataframe(dept_summary, use_container_width=True)

    st.subheader("⏱️ Estimated Time Saved from Debrief Removal")
    selected_dept = st.selectbox("Select Department", sorted(departments))
    total_candidates = df[df["Department"] == selected_dept]["Candidate Name"].nunique()
    time_saved_hours = total_candidates * 3
    st.metric(label=f"Estimated Time Saved in {selected_dept}", value=f"{time_saved_hours} hours")

    st.subheader("👥 Internal Interviewer Stats")
    selected_depts = st.multiselect("Filter by Department", departments, default=departments)
    name_query = st.text_input("Search by Interviewer Name").strip().lower()

    interviewer_df = df[df["Internal Interviewer"].notna() & df["Department"].isin(selected_depts)]
    if name_query:
        interviewer_df = interviewer_df[interviewer_df["Internal Interviewer"].str.lower().str.contains(name_query)]

    interviewer_summary = interviewer_df.groupby("Internal Interviewer").agg(
        Interviews_Conducted=("Interview", "count"),
        Scorecards_Submitted=("Scorecard Complete", "sum"),
        Avg_Interview_Score=("Interview Score", "mean")
    ).reset_index()

    interviewer_summary['Completion Rate (%)'] = round(100 * interviewer_summary['Scorecards_Submitted'] / interviewer_summary['Interviews_Conducted'] * 1, 1)

    st.dataframe(interviewer_summary, use_container_width=True)

# ----------------- Success Metrics -----------------
with tab4:
    st.title("📈 Success Metrics Overview")
    st.markdown("### Previewing Metrics That Reflect Dashboard Impact")
    st.markdown("""
    | Metric                         | Example Value        | Target      |
    |--------------------------------|----------------------|-------------|
    | Scorecard Completion Rate      | 92%                  | ≥ 90%       |
    | Avg Time-to-Hire               | 7.2 days             | < 10 days   |
    | % Resolved w/o Debrief         | 78%                  | > 70%       |
    | Interview Load per Interviewer | 6.3 interviews       | Balanced    |
    | Offer Acceptance Rate          | 84%                  | > 80%       |
    """, unsafe_allow_html=True)
    st.info("This is a demo view. You can bring these metrics to life as your data maturity grows.")

# ----------------- Entry Point -----------------
if __name__ == "__main__":
    pass



# ----------------- Enhanced Scorecard Dashboard -----------------
import altair as alt

st.title("🧮 Scorecard Dashboard")

# SECTION: Summary Metrics
col1, col2, col3 = st.columns(3)
col1.metric("Avg Score", "3.6")
col2.metric("Total Interviews", "112")
col3.metric("Overdue Scorecards", "4")

st.markdown("---")

# SECTION: Submission Health
st.subheader("📥 Scorecard Submission Health")
submission_health = pd.DataFrame({
    "Candidate": ["Ava Chen", "Lucas Grant", "Maya Singh", "Ethan Brown"],
    "Role": ["PM", "Engineer", "Designer", "Engineer"],
    "Stage": ["Onsite", "Onsite", "Final", "Phone Screen"],
    "Interviewers Assigned": [4, 3, 5, 2],
    "Submitted": [3, 3, 4, 1],
    "Missing": [1, 0, 1, 1]
})
st.dataframe(submission_health.style
    .highlight_between(subset=["Missing"], left=1, right=10, color="#ffe6e6")
    .highlight_between(subset=["Submitted"], left=3, right=10, color="#e6ffea"))

st.markdown("---")

# SECTION: Average Scores by Candidate
st.subheader("📊 Average Interview Scores")
average_scores = pd.DataFrame({
    "Candidate": ["Ava Chen", "Lucas Grant", "Maya Singh", "Ethan Brown"],
    "Avg Score": [3.8, 4.2, 2.9, 3.5],
    "# of Scorecards": [3, 3, 4, 1],
    "Stage": ["Onsite", "Onsite", "Final", "Phone Screen"]
})
score_chart = alt.Chart(average_scores).mark_bar(color="#1f77b4").encode(
    x=alt.X("Avg Score:Q", scale=alt.Scale(domain=[0, 5]), title="Avg Score"),
    y=alt.Y("Candidate:N", sort="-x"),
    tooltip=["Candidate", "Avg Score", "# of Scorecards"]
).properties(width=600, height=300)
labels = alt.Chart(average_scores).mark_text(
    align="left",
    baseline="middle",
    dx=3
).encode(
    x="Avg Score",
    y="Candidate",
    text="Avg Score"
)
st.altair_chart(score_chart + labels, use_container_width=True)

st.markdown("---")

# SECTION: Overdue Scorecards Chart
st.subheader("⏱️ Overdue Scorecards by Candidate")
overdue_data = submission_health[submission_health["Missing"] > 0]
overdue_chart = alt.Chart(overdue_data).mark_bar(color="#d62728").encode(
    x=alt.X("Missing:Q", title="Missing Scorecards"),
    y=alt.Y("Candidate:N", sort="-x"),
    tooltip=["Candidate", "Missing"]
).properties(width=500)
st.altair_chart(overdue_chart, use_container_width=True)
