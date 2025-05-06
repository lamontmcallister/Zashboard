
import streamlit as st
import pandas as pd
import altair as alt
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ✅ MUST be first
st.set_page_config(page_title="Scorecard Dashboard", layout="wide")

# ----------------- Custom Styling -----------------
st.markdown("""
    <style>
        html, body, [class*="css"] {
            font-family: 'Segoe UI', sans-serif;
            background-color: white;
            color: #333333;
        }
        .block-container {
            padding: 2rem;
        }
        h1, h2, h3 {
            font-weight: 700;
        }
    </style>
""", unsafe_allow_html=True)

# ----------------- Load Data -----------------
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

# ----------------- Mock Data for Demo -----------------
dept_df = pd.DataFrame({
    "Department": ["Sales", "HR", "IT"],
    "Completion Rate (%)": [76, 74, 71]
})

# ----------------- Dashboard Layout -----------------

st.title("📊 Department Analytics")

# 🔹 Summary Row
col1, col2, col3 = st.columns(3)
col1.metric("Avg Completion Rate", "74%", "📈")
col2.metric("Interviews Last 30 Days", "112", "🧑‍💼")
col3.metric("Avg Time to Submit", "2.3 days", "⏱️")

st.markdown("---")

# ✅ Completion Rate by Department
st.markdown("### ✅ Completion Rate by Department")

chart = alt.Chart(dept_df).mark_bar(
    cornerRadiusTopLeft=4,
    cornerRadiusTopRight=4,
    color="#1f77b4"
).encode(
    x=alt.X("Completion Rate (%):Q", title="Completion Rate (%)"),
    y=alt.Y("Department:N", sort="-x", title="Department"),
    tooltip=["Department", "Completion Rate (%)"]
).properties(width=600, height=300)

labels = alt.Chart(dept_df).mark_text(
    align='left',
    baseline='middle',
    dx=3
).encode(
    x="Completion Rate (%)",
    y="Department",
    text="Completion Rate (%)"
)

st.altair_chart(chart + labels, use_container_width=True)

# ⏱️ Time Saved Panel
st.markdown("### ⏱️ Estimated Time Saved")
selected_dept = st.selectbox("Select Department", dept_df["Department"])
dept_hours = {"Sales": 92, "HR": 84, "IT": 71}
st.metric(label=f"{selected_dept} Department", value=f"{dept_hours[selected_dept]} hours")

st.markdown("---")

# 🧑‍💼 Internal Interviewer Stats
st.markdown("### 🧑‍💼 Internal Interviewer Stats")
st.write("Use the filters below to view interview activity and submission performance.")

col1, col2 = st.columns([1, 2])
with col1:
    st.selectbox("Filter by Department", ["All", "Sales", "HR", "IT"])
with col2:
    st.text_input("Search by Interviewer Name")

st.markdown("_(Interviewer table would go here)_")

