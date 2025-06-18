# recruiter_dashboard.py
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px

# ----------------- Page Setup -----------------
st.set_page_config(page_title="Recruiter Platform", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
html, body, [class*="css"]  {
    font-family: 'Inter', sans-serif !important;
    font-size: 16px;
    line-height: 1.6;
    color: #1e1e1e;
}
h1, h2, h3 { font-weight: 600 !important; }
th { font-weight: bold; background-color: #f0f8ff; }
td { text-align: center !important; }
</style>
""", unsafe_allow_html=True)

# ----------------- Data Loading -----------------
@st.cache_data(ttl=600)
def load_google_sheet(sheet_url, worksheet_name):
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
    df['Time to Submit Scorecard (HRs)'] = pd.to_numeric(df['Time to Submit Scorecard (HRs)'], errors='coerce')
    df['On Time (%)'] = df['Time to Submit Scorecard (HRs)'].apply(lambda x: 100 if x <= 24 else 0)
    return df

def make_decision(row):
    if row['Scorecards_Submitted'] < 4:
        return "🟡 Waiting for Interviews"
    elif row['Avg_Interview_Score'] <= 3.4:
        return "🔴 Needs Recruiter Review"
    elif row['Avg_Interview_Score'] >= 3.5:
        return "🟢 Strong — HM Review"
    return "⚠️ Needs Discussion"

# ----------------- Load Data -----------------
sheet_url = "https://docs.google.com/spreadsheets/d/1_hypJt1kwUNZE6Xck1VVjrPeYiIJpTDXSAwi4dgXXko"
worksheet_name = "Mixed Raw Candidate Data"

try:
    df = prepare_dataframe(load_google_sheet(sheet_url, worksheet_name))
except Exception as e:
    st.error(f"❌ Failed to load data from Google Sheet: {e}")
    st.stop()

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
    st.markdown("## The Interview Signal Dashboard")
    st.markdown("""
BrightHire captures the conversation. This dashboard captures what matters next.

Designed to complement live debriefs not replace them. This tool transforms interviewer scorecards into decision-ready insights. It surfaces patterns, flags risks, and helps teams stay calibrated.

✅ Accelerates hiring decisions  
✅ Reinforces scorecard quality and accountability  
✅ Keeps interviewers and hiring managers aligned  
""")
    st.success("✅ Supports data-driven hiring alongside live debriefs.")

# ----------------- Scorecard Dashboard -----------------
with tab2:
    st.title("🎯 Scorecard Dashboard")
    with st.expander("❓ How to Use This Dashboard"):
        st.markdown("""
        1. **Choose a Recruiter** to view their active candidates  
        2. Filter by **Scorecard Status** and **Department**  
        3. Review scores, decisions, and click to see interview details  
        4. Use **reminder buttons** to nudge missing interviewers  
        5. Export candidate data with **Download Results**
        """)
    recruiters = sorted(df['Recruiter'].dropna().unique().tolist())

    top_col1, top_col2 = st.columns([1, 1])
    with top_col1:
        selected_recruiter = st.selectbox("👤 Choose Recruiter", recruiters)
    with top_col2:
        toggle_status = st.radio("📋 Show Candidates With", ["Complete Scorecards", "Pending Scorecards", "All"], index=0)

    selected_depts = st.multiselect("### 🏢 Filter by Department", departments, default=departments)

    grouped = df.groupby('Candidate Name').agg(
        Avg_Interview_Score=('Interview Score', 'mean'),
        Scorecards_Submitted=('Scorecard submitted', lambda x: sum(x == 'yes')),
        Total_Interviews=('Interview Score', 'count'),
        Department=('Department', 'first'),
        Recruiter=('Recruiter', 'first')
    ).reset_index()

    grouped['Decision'] = grouped.apply(make_decision, axis=1)
    grouped = grouped[(grouped['Recruiter'] == selected_recruiter) & (grouped['Department'].isin(selected_depts))]

    if toggle_status == "Complete Scorecards":
        grouped = grouped[grouped['Scorecards_Submitted'] == 4]
    elif toggle_status == "Pending Scorecards":
        grouped = grouped[grouped['Scorecards_Submitted'] < 4]

    st.subheader(f"📋 Candidate Summary for {selected_recruiter}")
    st.dataframe(grouped[['Candidate Name', 'Department', 'Avg_Interview_Score', 'Scorecards_Submitted', 'Decision']], use_container_width=True)

    st.subheader("🧠 Candidate Details")
    for _, row in grouped.iterrows():
        with st.expander(f"{row['Candidate Name']} — {row['Decision']}"):
            st.markdown(f"**Department:** {row['Department']}")
            st.markdown(f"**Scorecards Submitted:** {row['Scorecards_Submitted']} / 4")
            st.markdown("---")
            st.markdown("### Interviewer Scores")

            candidate_rows = df[df['Candidate Name'] == row['Candidate Name']]
            for _, r in candidate_rows.iterrows():
                submitted = str(r['Scorecard submitted']).strip().lower() == 'yes'
                score = r['Interview Score']
                interviewer = r['Internal Interviewer']
                interview_label = r['Interview']
                if submitted:
                    st.markdown(f"- **{interviewer}** ({interview_label}): ✅ {score}")
                else:
                    st.markdown(f"- **{interviewer}** ({interview_label}): ❌ Not Submitted")
                    st.button(f"📩 Send Reminder to {interviewer}", key=f"{row['Candidate Name']}-{interviewer}")

# ----------------- Department Analytics -----------------
with tab3:
    st.title("📊 Department Scorecard Analytics")
    with st.expander("❓ How to Use This Dashboard"):
        st.markdown("""
        1. View **completion rates by department**  
        2. Analyze **avg time to submit** (flagged in red if slow)  
        3. Drill into **interviewer behavior** using filters  
        4. Use the **Needs Coaching** column to identify who needs support
        """)

    dept_summary = df.groupby('Department').agg(
        Total_Interviews=('Interview Score', 'count'),
        Completed=('Scorecard Complete', 'sum'),
        Avg_Score=('Interview Score', 'mean')
    ).reset_index()
    dept_summary['Completion Rate (%)'] = round(100 * dept_summary['Completed'] / dept_summary['Total_Interviews'], 1)

    avg_time_submit = df.groupby('Department')['Time to Submit Scorecard (HRs)'].mean().reset_index()
    avg_time_submit.columns = ['Department', 'Avg Time to Submit (HRs)']
    dept_summary = pd.merge(dept_summary, avg_time_submit, on='Department', how='left')

    st.subheader("✅ Scorecard Submission Rate by Department")
    fig = px.bar(
        dept_summary,
        y='Department',
        x='Completion Rate (%)',
        orientation='h',
        title='Scorecard Completion Rate by Department',
        color='Department',
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig.update_layout(yaxis_title='Department', xaxis_title='Completion Rate (%)')
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("⏱ Average Time to Submit by Department")

    def highlight_avg_time(val):
        color = '#c6f6d5' if val <= 24 else '#fed7d7'
        return f'background-color: {color}; text-align: center'

    st.dataframe(
        dept_summary[['Department', 'Avg Time to Submit (HRs)']]
        .style
        .applymap(highlight_avg_time, subset=['Avg Time to Submit (HRs)'])
        .format({'Avg Time to Submit (HRs)': '{:.1f}'}),
        use_container_width=True
    )

    st.subheader("👥 Internal Interviewer Stats")
    selected_depts_interviewers = st.multiselect("Filter by Department", departments, default=departments, key="interviewers-dept-filter")
    name_query = st.text_input("Search by Interviewer Name", key="interviewers-name-filter").strip().lower()

    interviewer_df = df[df["Internal Interviewer"].notna() & df["Department"].isin(selected_depts_interviewers)]
    if name_query:
        interviewer_df = interviewer_df[interviewer_df["Internal Interviewer"].str.lower().str.contains(name_query)]

    interviewer_summary = interviewer_df.groupby("Internal Interviewer").agg(
        Interviews_Conducted=("Interview", "count"),
        Scorecards_Submitted=("Scorecard Complete", "sum"),
        Avg_Interview_Score=("Interview Score", "mean"),
        Avg_Submission_Time_Hours=('Time to Submit Scorecard (HRs)', 'mean'),
        On_Time_Submissions=('On Time (%)', 'mean')
    ).reset_index()
    interviewer_summary['Completion Rate (%)'] = round(
        100 * interviewer_summary['Scorecards_Submitted'] / interviewer_summary['Interviews_Conducted'], 1
    )
    interviewer_summary['Needs Coaching'] = interviewer_summary.apply(
        lambda row: '✅' if row['Completion Rate (%)'] >= 75 and row['Avg_Submission_Time_Hours'] <= 24 else '⚠️', axis=1
    )

    def color_completion(val):
        return f'background-color: {"#c6f6d5" if val >= 90 else "#fed7d7"}; text-align: center'

    def color_coaching(val):
        return f'background-color: {"#c6f6d5" if val == "✅" else "#ffe4e1"}; text-align: center'

    st.dataframe(
        interviewer_summary.style
        .applymap(color_completion, subset=['Completion Rate (%)'])
        .applymap(color_coaching, subset=['Needs Coaching'])
        .format({
            'Avg_Interview_Score': '{:.2f}',
            'Avg_Submission_Time_Hours': '{:.1f}',
            'On_Time_Submissions': '{:.0f}%'
        })
        .set_properties(**{'text-align': 'center'}),
        use_container_width=True
    )

# ----------------- Success Metrics -----------------
with tab4:
    st.title("📈 Success Metrics Overview")
    st.markdown("### Previewing Metrics That Reflect Dashboard Impact")
    st.markdown("""
    | Metric                         | Example Value        | Target      |
    |--------------------------------|----------------------|-------------|
    | Scorecard Completion Rate      | 92%                  | ≥ 90%       |
    | Avg Time-to-Hire               | 7.2 days             | < 10 days   |
    | On Time Scorecard Submission   | 76%                  | > 75%       |
    | Interview Load per Interviewer | 6.3 interviews       | Balanced    |
    | Offer Acceptance Rate          | 84%                  | > 80%       |
    """, unsafe_allow_html=True)
    st.info("This is a demo view. You can bring these metrics to life as your data maturity grows.")

if __name__ == "__main__":
    pass
