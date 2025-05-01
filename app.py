
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Scorecard Dashboard", layout="wide")

# --------- Data Load ---------
@st.cache_data
def load_data():
    # Replace this with your actual data source or Supabase pull
    return pd.read_csv("scorecard_data.csv")  # Placeholder

df = load_data()

# --------- Page Navigation ---------
page = st.sidebar.radio("🔍 Select Page", ["🔰 Landing Page", "🎯 Scorecard Dashboard", "📊 Department Analytics"])

# --------- Landing Page ---------
if page == "🔰 Landing Page":
    st.title("Welcome to the Scorecard Dashboard")
    st.subheader("✨ Why Use This Dashboard?")
    st.markdown('''
    - Centralize candidate scorecard data  
    - Quickly identify who has completed their interviews  
    - Spot missing scorecards and nudge interviewers  
    - Analyze trends in department and interviewer performance  
    ''')

    st.subheader("🧭 How to Use")
    st.markdown('''
    1. Navigate to **Scorecard Dashboard** to see candidates under your care  
    2. Use filters to narrow by recruiter, department, or scorecard status  
    3. Expand each candidate to review interview-level data and send reminders  
    4. Visit **Department Analytics** to review departmental scorecard submission trends  
    ''')

    st.success("You're just a click away from cleaner scorecard ops 🚀")

# --------- Scorecard Dashboard ---------
elif page == "🎯 Scorecard Dashboard":
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
        elif row['Avg_Interview_Score'] >= 4.0:
            return "🟢 Move Forward"
        else:
            return "🔴 Do Not Move Forward"

    grouped['Decision'] = grouped.apply(make_decision, axis=1)

    # Filter by selected recruiter and department
    grouped = grouped[(grouped['Recruiter'] == selected_recruiter) & (grouped['Department'].isin(selected_depts))]

    if toggle_status == "Complete Scorecards":
        grouped = grouped[grouped['Scorecards_Submitted'] == grouped['Total_Interviews']]
    elif toggle_status == "Pending Scorecards":
        grouped = grouped[grouped['Scorecards_Submitted'] < grouped['Total_Interviews']]

    st.dataframe(grouped.style.format({"Avg_Interview_Score": "{:.2f}"}), use_container_width=True)

# --------- Department Analytics ---------
elif page == "📊 Department Analytics":
    st.title("📊 Department Scorecard Analytics")
    dept_summary = df.groupby('Department').agg(
        Total_Candidates=('Candidate Name', 'nunique'),
        Avg_Score=('Interview Score', 'mean'),
        Completion_Rate=('Scorecard submitted', lambda x: round(sum(x == 'yes') / len(x) * 100, 1))
    ).reset_index()

    st.dataframe(dept_summary.style.format({"Avg_Score": "{:.2f}", "Completion_Rate": "{:.1f}%"}), use_container_width=True)
