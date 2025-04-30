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

# --------- Data Cleanup ---------
df['Interview Score'] = pd.to_numeric(df['Interview Score'], errors='coerce')
df['Scorecard submitted'] = df['Scorecard submitted'].str.strip().str.lower()

# --------- Grouped Candidate Summary ---------
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

# --------- Streamlit UI ---------
st.set_page_config(page_title="Interview Score Summary", layout="wide")
st.title("🎯 Candidate Interview Score Summary")
st.caption("Summarizes 4 interviewer scores into an average, tracks scorecard submissions, and recruiter decision flow.")

# --------- Sidebar Filters ---------
departments = grouped['Department'].dropna().unique().tolist()
recruiters = grouped['Recruiter'].dropna().unique().tolist()

selected_depts = st.sidebar.multiselect("Filter by Department", departments, default=departments)
selected_recruiters = st.sidebar.multiselect("Filter by Recruiter", recruiters, default=recruiters)
only_full_submissions = st.sidebar.checkbox("✅ Only show candidates with all 4 scorecards", value=False)

# Apply filters
filtered = grouped[
    (grouped['Department'].isin(selected_depts)) &
    (grouped['Recruiter'].isin(selected_recruiters))
]

if only_full_submissions:
    filtered = filtered[filtered['Scorecards_Submitted'] == 4]

# --------- Display Tables & Charts ---------
st.subheader("📋 Candidate Interview Summary")
st.dataframe(filtered[['Candidate Name', 'Department', 'Recruiter', 'Avg_Interview_Score', 'Scorecards_Submitted', 'Decision']],
             use_container_width=True)

# Bar Chart
st.subheader("📊 Average Interview Scores")
fig = px.bar(filtered, x="Candidate Name", y="Avg_Interview_Score", color="Candidate Name",
             text_auto=True, title="Avg Interview Score per Candidate")
fig.update_layout(showlegend=False)
st.plotly_chart(fig, use_container_width=True)

# Candidate Detail Expander with per-interviewer breakdown
st.subheader("🧠 Candidate Info")
for _, row in filtered.iterrows():
    with st.expander(f"🧾 {row['Candidate Name']}"):
        st.markdown(f"**Department:** {row['Department']}")
        st.markdown(f"**Recruiter:** {row['Recruiter']}")
        st.markdown(f"**Interview Count:** {row['Total_Interviews']} / 4")
        st.markdown(f"**Scorecards Submitted:** {row['Scorecards_Submitted']} / 4")
        st.markdown(f"**Decision:** {row['Decision']}")
        st.markdown("---")
        st.markdown("### Interviewer Scores")
        candidate_rows = df[df['Candidate Name'] == row['Candidate Name']]
        for _, r in candidate_rows.iterrows():
            st.markdown(f"- **{r['Internal Interviewer']}** ({r['Interview']}): {r['Interview Score']}")
