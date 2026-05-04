from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import os
import sqlite3
import re
from openai import OpenAI


# OpenRouter Client Setup

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)


# Function: Convert Question → SQL

def get_sql_query(question, prompt):
    response = client.chat.completions.create(
        model="openai/gpt-3.5-turbo",   # you can change model
        messages=[
            {"role": "system", "content": prompt[0]},
            {"role": "user", "content": question}
        ],
        temperature=0
    )
    return response.choices[0].message.content.strip()



# Clean SQL (remove extra text)

def clean_sql(response):
    response = re.sub(r"```sql|```", "", response)
    return response.strip()



# Execute SQL Query

def read_sql_query(sql, db):
    try:
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception as e:
        return f"SQL Error: {e}"



# Prompt for LLM

prompt = [
    """
    You are an expert in converting English questions to SQL query!
    The SQL database has the name STUDENT and has the following columns - NAME, CLASS, SECTION.

    Rules:
    - Return ONLY SQL query
    - No explanation
    - No ``` or extra text

    Examples:
    Example 1:
    Input: How many entries of records are present?
    Output: SELECT COUNT(*) FROM STUDENT;

    Example 2:
    Input: Tell me all the students studying in Data Science class?
    Output: SELECT * FROM STUDENT WHERE CLASS="Data Science";
    """
]


# Streamlit UI

st.set_page_config(page_title="SQL AI Assistant")
st.header("💬 AI Text-to-SQL App")

question = st.text_input("Ask your question:", key="input")

submit = st.button("Generate & Run SQL")


# Main Logic

if submit and question:

    # Step 1: Generate SQL
    raw_sql = get_sql_query(question, prompt)
    sql_query = clean_sql(raw_sql)

    st.subheader("🧠 Generated SQL:")
    st.code(sql_query, language="sql")

    # Step 2: Execute SQL
    result = read_sql_query(sql_query, "student.db")

    st.subheader("📊 Query Result:")

    if isinstance(result, str):
        st.error(result)
    else:
        for row in result:
            st.write(row)