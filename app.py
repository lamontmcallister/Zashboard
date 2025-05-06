import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
st.set_page_config(page_title="Recruiter Platform", layout="wide")
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
departments = sorted(df['Department'].dropna().unique().tolist())
# --------- Prep ---------
df['Interview Score'] = pd.to_numeric(df['Interview Score'], errors='coerce')
df['Scorecard submitted'] = df['Scorecard submitted'].str.strip().str.lower()
df['Scorecard Complete'] = df['Scorecard submitted'] == 'yes'
# --------- Streamlit Setup ---------
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
tab1, tab2, tab3, tab4 = st.tabs(["🔰 Landing Page", "Scorecard Dashboard", "📊 
st.header("📊 Department Analytics")

dept_summary = df.groupby("Department").agg(
    Interviews_Conducted=("Interview", "count"),
    Scorecards_Submitted=("Scorecard Complete", "sum"),
    Avg_Interview_Score=("Interview Score", "mean")
).reset_index()

dept_summary["Completion Rate (%)"] = (
    dept_summary["Scorecards_Submitted"] / dept_summary["Interviews_Conducted"] * 100
).round(1)

def highlight_dept_completion(val):
    return "color: green;" if val >= 90 else "color: red;"

styled_dept = dept_summary.style.format({
    "Avg_Interview_Score": "{:.2f}",
    "Completion Rate (%)": "{:.1f}%"
}).applymap(
    highlight_dept_completion, subset=["Completion Rate (%)"]
).set_properties(**{"text-align": "center"}).set_table_styles([
    {"selector": "th", "props": [("font-weight", "bold"), ("background-color", "#f0f8ff")]}
])

st.dataframe(styled_dept, use_container_width=True)
 'Decision']],
                    use_container_width=True)
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

# --------- Department Analytics ---------
with tab3:
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
        st.subheader("⏱️ Estimated Time Saved from Debrief Removal")
        dept_choices = df["Department"].dropna().unique().tolist()
        selected_dept = st.selectbox("Select Department", sorted(dept_choices))
        dept_df = df[df["Department"] == selected_dept]
        total_candidates = dept_df["Candidate Name"].nunique()
        time_saved_hours = total_candidates * 3  # 6 people x 30 mins = 3 hours per candidate
        st.metric(label=f"Estimated Time Saved in {selected_dept}", value=f"{time_saved_hours} hours")
        st.subheader("👥 
st.header("Internal Interviewer Stats")
dept_options = df["Department"].dropna().unique().tolist()
selected_depts = st.multiselect("Filter by Department", dept_options, default=dept_options)
name_query = st.text_input("Search by Interviewer Name").strip().lower()

interviewer_df = df[df["Internal Interviewer"].notna()]
interviewer_df = interviewer_df[interviewer_df["Department"].isin(selected_depts)]
if name_query:
    interviewer_df = interviewer_df[interviewer_df["Internal Interviewer"].str.lower().str.contains(name_query)]

interviewer_summary = interviewer_df.groupby("Internal Interviewer").agg(
    Interviews_Conducted=("Interview", "count"),
    Scorecards_Submitted=("Scorecard Complete", "sum"),
    Avg_Interview_Score=("Interview Score", "mean")
).reset_index()

interviewer_summary["Completion Rate (%)"] = (
    interviewer_summary["Scorecards_Submitted"] / interviewer_summary["Interviews_Conducted"] * 100
).round(1)

def highlight_completion(val):
    return "color: green;" if val >= 90 else "color: red;"

styled_interviewers = interviewer_summary.style.format({
    "Avg_Interview_Score": "{:.2f}",
    "Completion Rate (%)": "{:.1f}%"
}).applymap(
    highlight_completion, subset=["Completion Rate (%)"]
).set_properties(**{"text-align": "center"}).set_table_styles([
    {"selector": "th", "props": [("font-weight", "bold"), ("background-color", "#f0f8ff")]}
])

st.dataframe(styled_interviewers, use_container_width=True)
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
