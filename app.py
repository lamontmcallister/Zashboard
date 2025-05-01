
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
st.set_page_config(page_title="Scorecard Dashboard", layout="wide")

page = st.sidebar.selectbox("🔍 Navigate", ["🔰 Landing Page", "🎯 Scorecard Dashboard", "📊 Department Analytics"])

# --------- Scorecard Dashboard ---------
if page == "🎯 Scorecard Dashboard":
    st.title("🎯 Scorecard Dashboard")
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
    st.dataframe(grouped[['Candidate Name', 'Department', 'Avg_Interview_Score', 'Scorecards_Submitted', 'Decision']], use_container_width=True)

    st.subheader("🧠 Candidate Details")
    for i, row in grouped.iterrows():
        with st.expander(f"{row['Candidate Name']} — {row['Decision']}"):
            st.markdown(f"**Department:** {row['Department']}")
            st.markdown(f"**Scorecards Submitted:** {row['Scorecards_Submitted']} / 4")
            st.markdown(f"**Avg Interview Score:** {row['Avg_Interview_Score']}")
            st.markdown("---")
            st.markdown("### Interviewer Scores")
            candidate_rows = df[df['Candidate Name'] == row['Candidate Name']]
            for j, r in candidate_rows.iterrows():
                score = r['Interview Score']
                status = r['Scorecard submitted']
                line = f"- **{r['Internal Interviewer']}** ({r['Interview']})"
                if status == 'yes':
                    st.markdown(f"{line}: ✅ {score}")
                else:
                    st.markdown(f"{line}: ❌ Not Submitted")
                    st.button(f"📩 Send Reminder to {r['Internal Interviewer']}", key=f"reminder-{i}-{j}")

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

    # Enhanced Internal Interviewer Stats
    st.subheader("👥 Internal Interviewer Stats")
    st.caption("Filter by department and search interviewer names to track submission and scoring trends.")

    interviewer_summary = df.groupby(['Internal Interviewer', 'Department']).agg(
        Interviews_Conducted=('Interview', 'count'),
        Scorecards_Submitted=('Scorecard Complete', 'sum'),
        Avg_Interview_Score=('Interview Score', 'mean')
    ).reset_index()

    departments = sorted(df['Department'].dropna().unique())
    selected_dept = st.selectbox("🏢 Filter by Department", ["All"] + departments)

    filtered_summary = interviewer_summary
    if selected_dept != "All":
        filtered_summary = filtered_summary[filtered_summary['Department'] == selected_dept]

    search_term = st.text_input("🔎 Search Interviewer")
    if search_term:
        filtered_summary = filtered_summary[
            filtered_summary['Internal Interviewer'].str.contains(search_term, case=False)
        ]

    styled_interviewers = filtered_summary.style.format({
        'Avg_Interview_Score': '{:.2f}'
    }).set_properties(**{'text-align': 'center'}).set_table_styles([
        {'selector': 'th', 'props': [('font-weight', 'bold'), ('background-color', '#f0f8ff')]}
    ])

    st.dataframe(styled_interviewers, use_container_width=True)
