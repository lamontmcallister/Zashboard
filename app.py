import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title='Skippr Scorecard Dashboard', layout='wide')

# --------- Google Sheets Setup ---------
def load_google_sheet(sheet_url, worksheet_name):
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = st.secrets['google']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(creds_dict), scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url)
    worksheet = sheet.worksheet(worksheet_name)
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

# --------- Load Data ---------
sheet_url = 'https://docs.google.com/spreadsheets/d/1_hypJt1kwUNZE6Xck1VVjrPeYiIJpTDXSAwi4dgXXko'
worksheet_name = 'Mixed Raw Candidate Data'
df = load_google_sheet(sheet_url, worksheet_name)

# --------- Prep ---------
df['Interview Score'] = pd.to_numeric(df['Interview Score'], errors='coerce')
df['Scorecard submitted'] = df['Scorecard submitted'].str.strip().str.lower()
df['Scorecard Complete'] = df['Scorecard submitted'] == 'yes'

# --------- Navigation ---------
tab1, tab2, tab3, tab4 = st.tabs([
    '🔰 Landing Page', 'Scorecard Dashboard', '📊 Department Analytics', '📈 Success Metrics Overview'
])

with tab1:
    st.title('📊 Candidate Selection Dashboard')
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('### 🧭 Overview: Streamlining Candidate Selection')
        st.markdown('''We aim to accelerate time-to-hire and reduce bottlenecks in the candidate selection process by eliminating the need for traditional debrief meetings. Instead, we rely on historical interview data to establish objective hiring benchmarks.''')
    with col2:
        st.markdown('### ✨ Why This Matters')
        st.markdown('''- Ensure fair, consistent hiring decisions  
- Track scorecard submission and identify bottlenecks  
- Empower recruiters with structured decision support''')
    st.markdown('### 🧭 How to Use This Tool')
    st.markdown('''1. Head to the **Scorecard Dashboard** tab  
2. Select a recruiter and optionally filter by department or scorecard status  
3. Review candidate decisions and send reminder nudges  
4. Use **Department Analytics** to track overall submission and scoring health''')

with tab2:
    st.header('🎯 Scorecard Completion Summary')
    recruiter_filter = st.selectbox('Filter by Recruiter:', options=['All'] + sorted(df['Recruiter'].dropna().unique().tolist()))
    filtered_df = df if recruiter_filter == 'All' else df[df['Recruiter'] == recruiter_filter]
    candidate_summary = filtered_df.groupby('Candidate Name').agg(
        Interview_Score=('Interview Score', 'mean'),
        Scorecards_Completed=('Scorecard Complete', 'sum'),
        Scorecards_Expected=('Scorecard Complete', 'count')
    ).reset_index()
    candidate_summary['Completion Rate'] = (candidate_summary['Scorecards_Completed'] / candidate_summary['Scorecards_Expected'] * 100).round(1)
    st.dataframe(candidate_summary)

with tab3:
    st.header('🏢 Department-Level Completion Rates')
    dept_summary = df.groupby('Department').agg(
        Interviews=('Candidate Name', 'count'),
        Avg_Score=('Interview Score', 'mean'),
        Completion_Rate=('Scorecard Complete', 'mean')
    ).reset_index()
    dept_summary['Completion_Rate'] = (dept_summary['Completion_Rate'] * 100).round(1)
    st.dataframe(dept_summary)

with tab4:
    st.header('📈 Success Metrics Overview')
    st.markdown("""
| Metric                          | Value                | Target       |
|--------------------------------|----------------------|--------------|
| Scorecard Completion Rate      | 92%                  | >= 90%       |
| Avg Time-to-Hire               | 7.2 days             | < 10 days    |
| % Resolved w/o Debrief         | 78%                  | > 70%        |
| Interview Load per Interviewer | 6.3 interviews       | Balanced     |
| Offer Acceptance Rate          | 84%                  | > 80%        |
""")
    st.info('This is a demo view. You can bring these metrics to life as your data maturity grows.')
