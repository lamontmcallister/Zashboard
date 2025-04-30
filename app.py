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

# --------- Cleanup ---------
df['Interview Score'] = pd.to_numeric(df['Interview Score'], errors='coerce')
df['Scorecard submitted'] = df['Scorecard submitted'].str.strip().str.lower()
df['Scorecard Complete'] = df['Scorecard submitted'] == 'yes'

# --------- Streamlit Setup ---------
st.set_page_config(page_title="Department Analytics", layout="wide")
st.title("📊 Department Scorecard Analytics")

# --------- Department Table ---------
dept_summary = df.groupby('Department').agg(
    Total_Interviews=('Interview Score', 'count'),
    Completed=('Scorecard Complete', 'sum'),
    Avg_Score=('Interview Score', 'mean')
).reset_index()
dept_summary['Completion Rate (%)'] = round(100 * dept_summary['Completed'] / dept_summary['Total_Interviews'], 1)

# --------- Apply Conditional Formatting ---------
def highlight_completion(val):
    color = 'green' if val >= 90 else 'red'
    return f'color: {color}; font-weight: bold'

styled_dept = dept_summary.style.format({
    'Avg_Score': '{:.2f}',
    'Completion Rate (%)': '{:.1f}%'
}).applymap(highlight_completion, subset=['Completion Rate (%)'])   .set_properties(**{'text-align': 'center'})   .set_table_styles([
      {'selector': 'th', 'props': [('font-weight', 'bold'), ('background-color', '#f0f8ff')]}
  ])

st.subheader("✅ Scorecard Submission Rate by Department")
st.dataframe(styled_dept, use_container_width=True)

# --------- Interviewer Table ---------
st.subheader("👥 Internal Interviewer Stats")
interviewer_summary = df.groupby('Internal Interviewer').agg(
    Interviews_Conducted=('Interview', 'count'),
    Scorecards_Submitted=('Scorecard Complete', 'sum'),
    Avg_Interview_Score=('Interview Score', 'mean')
).reset_index()

styled_interviewers = interviewer_summary.style.format({
    'Avg_Interview_Score': '{:.2f}'
}).set_properties(**{'text-align': 'center'})   .set_table_styles([
      {'selector': 'th', 'props': [('font-weight', 'bold'), ('background-color', '#f0f8ff')]}
  ])

st.dataframe(styled_interviewers, use_container_width=True)
