
import streamlit as st
import pandas as pd
import os
import plotly.express as px
import google.generativeai as genai

# Configure the API key
genai.configure(api_key="apikey")

# Initialize the chat
model = genai.GenerativeModel("gemini-2.0-flash")
chat = model.start_chat()

# File paths
CSV_FILE = "budget_log.csv"
AI_BUDGET_FILE = "ai_budget_log.csv"

# Function to interact with AI for budget insights
def generate_budget_analysis(df, salary):
    instruction = """You are a financial advisor. Given the user's spending data, generate:

1. A **realistic budget breakdown** while following the **Needs-Wants-Savings** framework:
  
   Strictly format the budget breakdown like this:

   Food: XX%  
   Transport: XX%  
   Rent: XX%  
   Shopping: XX%    
   Savings: XX% 
   Others: XX% 

2. **Actionable Steps to Stick to This Budget (1-liner points):**  
   - **For every category that is being reduced or increased, provide specific, actionable steps for the user to achieve the change.**  
   - **Do NOT simply state the adjustment; explain how the user can implement it.**  
   - **Ensure total reduction aligns with best financial practices.** 

3. **Ensure the total percentage adds up to 100%** while subtly adjusting allocations to fit financial best practices. **Include the 'Others' category in the breakdown.**

4. **Do not add extra information or analysis beyond what is requested.**
"""
    df["Date"] = pd.to_datetime(df["Date"])  # Convert Date column to datetime
    category_totals = df.groupby("Category")["% of Salary Spent"].sum().to_dict()

    response = chat.send_message(f"{instruction}\n\nUser Salary: ₹{salary}\nExpenses: {category_totals}")
    return response.text, category_totals

# Load data function
def load_data():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    else:
        return pd.DataFrame(columns=["Date", "Category", "Amount", "Note", "% of Salary Spent"])

# Save AI budget data
def save_ai_budget(df):
    df.to_csv(AI_BUDGET_FILE, index=False)

# Streamlit UI
st.title("💰 AI-Powered Budget Tracker")

if "salary" not in st.session_state:
    st.session_state.salary = None

# Ask for salary
salary = st.number_input("Enter your monthly salary:", min_value=0.0, format="%.2f")

if st.button("Save Salary"):
    if salary > 0:
        st.session_state.salary = salary
        st.success(f"Your salary of ₹{salary:.2f} has been saved.")
    else:
        st.error("Please enter a valid salary.")

df = load_data()
total_spent = df["Amount"].sum() if not df.empty else 0

if not df.empty and st.session_state.salary:
    if st.button("Generate AI Budget Analysis"):
        analysis, category_totals = generate_budget_analysis(df, st.session_state.salary)
        
        st.subheader("📜 Your Old Budget (Past Spending)")
        old_budget_df = pd.DataFrame(list(category_totals.items()), columns=["Category", "Percentage_Old"])
        st.dataframe(old_budget_df)

        st.subheader("🧠 AI-Generated Budget Plan & Insights")
        st.write(analysis)

        # Extract AI-generated budget
        budget_lines = analysis.split("\n")
        budget_data = {}
        for line in budget_lines:
            if ":" in line:
                parts = line.split(":")
                if len(parts) == 2:
                    category = parts[0].strip()
                    percent = parts[1].strip().replace("%", "")
                    try:
                        budget_data[category] = float(percent)
                    except ValueError:
                        pass  

        if budget_data:
            ai_budget_df = pd.DataFrame(list(budget_data.items()), columns=["Category", "Percentage_AI"])
            
            ai_budget_df.to_csv("ai_budget_log.csv", index=False)
            st.subheader("📊 Spending vs. AI Budget Comparison")
            category_sums = df.groupby("Category")["Amount"].sum().reset_index()
            category_sums["Percentage_Actual"] = (category_sums["Amount"] / st.session_state.salary) * 100

            comparison_df = pd.merge(category_sums, ai_budget_df, on="Category", how="outer").fillna(0)
            fig_comparison = px.bar(
                comparison_df, x="Category", y=["Percentage_Actual", "Percentage_AI"],
                barmode="group", title="Actual Spending vs. AI-Recommended Budget"
            )
            st.plotly_chart(fig_comparison)

            if st.button("Set as New Budget"):
                ai_budget_df.to_csv(AI_BUDGET_FILE, index=False)
                st.success("AI Budget has been saved successfully!")
