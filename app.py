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
    Veteran_Status=('Veteran Status', 'first'),
    Disability_Status=('Disability Status', 'first'),
    Gender=('Gender Identity', 'first')
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
st.caption("Automatically summarizes 4 interviewer scores into an average, submission tracker, and decision guide.")

# Sidebar
selected_names = st.sidebar.multiselect("Select Candidates", grouped['Candidate Name'].unique(),
                                        default=grouped['Candidate Name'].unique())

filtered = grouped[grouped['Candidate Name'].isin(selected_names)]

# Summary Table
st.subheader("📋 Candidate Interview Summary")
st.dataframe(filtered[['Candidate Name', 'Avg_Interview_Score', 'Scorecards_Submitted', 'Decision']],
             use_container_width=True)

# Bar Chart
st.subheader("📊 Average Interview Scores")
fig = px.bar(filtered, x="Candidate Name", y="Avg_Interview_Score", color="Candidate Name",
             text_auto=True, title="Avg Interview Score per Candidate")
fig.update_layout(showlegend=False)
st.plotly_chart(fig, use_container_width=True)

# Details
st.subheader("🧠 Candidate Info")
for _, row in filtered.iterrows():
    with st.expander(f"🧾 {row['Candidate Name']}"):
        st.markdown(f"**Department:** {row['Department']}")
        st.markdown(f"**Veteran Status:** {row['Veteran_Status']}")
        st.markdown(f"**Disability Status:** {row['Disability_Status']}")
        st.markdown(f"**Gender Identity:** {row['Gender']}")
        st.markdown(f"**Interview Count:** {row['Total_Interviews']} / 4")
        st.markdown(f"**Scorecards Submitted:** {row['Scorecards_Submitted']} / 4")
        st.markdown(f"**Decision:** {row['Decision']}")
