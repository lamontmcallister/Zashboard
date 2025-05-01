import streamlit as st

import pandas as pd
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

# --------- Prep ---------
df['Interview Score'] = pd.to_numeric(df['Interview Score'], errors='coerce')
df['Scorecard submitted'] = df['Scorecard submitted'].str.strip().str.lower()
df['Scorecard Complete'] = df['Scorecard submitted'] == 'yes'

# --------- Streamlit Setup ---------
st.set_page_config(page_title="Recruiter Platform", layout="wide")

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
        th {
            font-weight: bold;
            background-color: #f0f8ff;
        }
        td {
            text-align: center !important;
        }
        .dataframe {
            border: 1px solid #ddd;
            border-radius: 4px;
        }
    </style>
    ''',
    unsafe_allow_html=True
)

# --------- Navigation ---------
page = st.sidebar.selectbox("🔍 Navigate", ["🔰 Landing Page", "Scorecard Dashboard", "📊 Department Analytics"])

# --------- Landing Page ---------
if page == "🔰 Landing Page":
    st.title("Welcome to the Recruiter Decision Dashboard")
    st.markdown("This platform helps you evaluate candidates based on interviewer feedback, scorecard submissions, and department-level analytics — all in one view.")

    st.subheader("✨ Why This Matters")
    st.markdown("""
- Ensure fair, consistent hiring decisions  
- Track scorecard submission and identify bottlenecks  
- Empower recruiters with structured decision support
""")

    st.subheader("🧭 How to Use This Tool")
    st.markdown("""
1. Head to the **Recruiter Dashboard** tab  
2. Select a recruiter and optionally filter by department or scorecard status  
3. Review candidate decisions and send reminder nudges  
4. Use **Department Analytics** to track overall submission and scoring health
""")

    st.success("Tip: Click any candidate name in the dashboard to view interview details!")

# Remaining pages not included for brevity (Recruiter Dashboard, Analytics)...


# --------- Recruiter Dashboard ---------
elif page == "Scorecard Dashboard":
    st.title("🎯 Recruiter Interview Dashboard")
    st.caption("Filter by recruiter and department. View candidate scorecards and send reminders.")

    recruiters = sorted(df['Recruiter'].dropna().unique().tolist())
    selected_recruiter = st.sidebar.selectbox("👤 Choose Recruiter", recruiters)
    departments = sorted(df['Department'].dropna().unique().tolist())
    selected_depts = st.sidebar.multiselect("🏢 Filter by Department", departments, default=departments)
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
    grouped = grouped[
        (grouped['Recruiter'] == selected_recruiter) &
        (grouped['Department'].isin(selected_depts))
    ]

    if toggle_status == "Complete Scorecards":
        grouped = grouped[grouped['Scorecards_Submitted'] == 4]
    elif toggle_status == "Pending Scorecards":
        grouped = grouped[grouped['Scorecards_Submitted'] < 4]

    st.subheader(f"📋 Candidate Summary for {selected_recruiter}")
    st.markdown("Use this table to track where each candidate stands based on scorecard completion and average interview scores.")
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

# --------- Department Analytics ---------
elif page == "📊 Department Analytics":
    st.title("📊 Department Scorecard Analytics")
    st.caption("This view shows how well departments and interviewers are keeping up with scorecard submissions.")

    dept_summary = df.groupby('Department').agg(
        Total_Interviews=('Interview Score', 'count'),
        Completed=('Scorecard Complete', 'sum'),
        Avg_Score=('Interview Score', 'mean')
    ).reset_index()
    dept_summary['Completion Rate (%)'] = round(100 * dept_summary['Completed'] / dept_summary['Total_Interviews'], 1)

    def highlight_completion(val):
        color = 'green' if val >= 90 else 'red'
        return f'color: {color}; font-weight: bold'

    styled_dept = dept_summary.style.format({
        'Avg_Score': '{:.2f}',
        'Completion Rate (%)': '{:.1f}%'
    }).applymap(highlight_completion, subset=['Completion Rate (%)'])       .set_properties(**{'text-align': 'center'})       .set_table_styles([
          {'selector': 'th', 'props': [('font-weight', 'bold'), ('background-color', '#f0f8ff')]}
      ])

    st.subheader("✅ Scorecard Submission Rate by Department")
    st.dataframe(styled_dept, use_container_width=True)

    st.subheader("👥 Internal Interviewer Stats")
    # --- Filters for Internal Interviewer Stats ---
    dept_options = df['Department'].dropna().unique().tolist()
    selected_depts = st.multiselect("Filter by Department", dept_options, default=dept_options)

    name_query = st.text_input("Search by Interviewer Name").strip().lower()

    internal_df = df[df['Internal Interviewer'].notna()]
    internal_df = internal_df[internal_df['Department'].isin(selected_depts)]

    if name_query:
        internal_df = internal_df[internal_df['Internal Interviewer'].str.lower().str.contains(name_query)]

    st.caption("Track interviewers' submission behavior and scoring trends.")
    interviewer_summary = df.groupby('Internal Interviewer').agg(
        Interviews_Conducted=('Interview', 'count'),
        Scorecards_Submitted=('Scorecard Complete', 'sum'),
        Avg_Interview_Score=('Interview Score', 'mean')
    ).reset_index()

    styled_interviewers = interviewer_summary.style.format({
        'Avg_Interview_Score': '{:.2f}'
    }).set_properties(**{'text-align': 'center'})       .set_table_styles([
          {'selector': 'th', 'props': [('font-weight', 'bold'), ('background-color', '#f0f8ff')]}
      ])

    st.dataframe(styled_interviewers, use_container_width=True)
