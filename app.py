from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import os
import re
import pandas as pd
from openai import OpenAI

from db_utils import read_sql_query
from db_schema import get_db_schema, format_schema, get_relationships, get_databases
from pdf_generator import generate_pdf

# ==============================
# OpenRouter Setup
# ==============================

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

# ==============================
# Chat Memory
# ==============================

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ==============================
# UI SETTINGS
# ==============================

st.set_page_config(page_title="AI SQL Assistant")
st.header("💬 AI Text-to-SQL")

# ==============================
# DATABASE SELECTION 
# ==============================

db_list = [db for db in get_databases() if db not in (
    "information_schema", "mysql", "performance_schema", "sys"
)]

db_choice = st.selectbox("📂Select Database", db_list)



# ==============================
# LOAD SCHEMA (AFTER DB SELECT)
# ==============================

schema = get_db_schema(db_choice)
schema_text = format_schema(schema)
relationship_text = get_relationships(db_choice)

# ==============================
# PROMPT
# ==============================

prompt = f"""
You are a STRICT SQL generator.

Current Database: {db_choice}

IMPORTANT
-Only use tables from this database
-Do Not assume tables from other database
-For showing tables,use : SHOW TABLES
-Do Not use other database names

{schema_text}

{relationship_text}

Rules:
- Return ONLY SQL
- No explanation
- No markdown
- Use JOIN when needed
- Use aliases
"""

# ==============================
# FUNCTIONS
# ==============================

def get_sql_query(question, history):
    messages = [{"role": "system", "content": prompt}]

    for msg in history:
        if msg["role"] in ["user", "assistant"]:
            messages.append(msg)

    messages.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model="openai/gpt-3.5-turbo",
        messages=messages,
        temperature=0
    )

    return response.choices[0].message.content.strip()


def clean_sql(response):
    return re.sub(r"```sql|```", "", response).strip()


def get_selected_chats(chat_history, indices):
    selected = []
    for i in indices:
        selected.extend(chat_history[i:i+3])
    return selected


# ==============================
# SIDEBAR
# ==============================

selected_indices = []

with st.sidebar:
    st.header("💬 Chat History")

    if st.button("🧹 Clear Chat"):
        st.session_state.chat_history = []
        st.rerun()

    st.markdown("---")
    # st.markdown(" Tables in DB")
    # for table in schema.keys():
    #     st.write(f" -{table}")
    # st.markdown("--")

    for i in range(len(st.session_state.chat_history) - 3, -1, -3):
        try:
            user_q = st.session_state.chat_history[i]["content"]
            sql_q = st.session_state.chat_history[i+1]["content"]

            if st.checkbox("↩ Select", key=f"select_{i}"):
                selected_indices.append(i)

            st.markdown(f"**You:** {user_q}")
            st.markdown(f"**SQL:** `{sql_q}`")
            st.markdown("---")

        except:
            continue

# ==============================
# PDF DOWNLOAD
# ==============================

if st.button("📄 Download Selected Chats as PDF"):

    if not selected_indices:
        st.warning("⚠️ Please select at least one chat")

    else:
        with st.spinner("Generating PDF..."):
            selected_data = get_selected_chats(
                st.session_state.chat_history,
                selected_indices
            )
            pdf_buffer = generate_pdf(selected_data)

        st.success("✅ PDF ready!")
        st.balloons()

        st.download_button(
            label="⬇️ Download PDF",
            data=pdf_buffer,
            file_name="selected_chat_report.pdf",
            mime="application/pdf"
        )

# ==============================
# INPUT
# ==============================

question = st.text_input("Ask your question:")
submit = st.button("Generate SQL")

# ==============================
# MAIN LOGIC
# ==============================

if submit and question:

    raw_sql = get_sql_query(question, st.session_state.chat_history)
    sql_query = clean_sql(raw_sql)

    st.subheader("🧠 Generated SQL")
    st.code(sql_query, language="sql")

    # Validation
    
    valid_tables = [t.lower() for t in schema.keys()]
    sql_lower = sql_query.lower()

    # Extract tables from FROM and JOIN
    tables_in_query = re.findall(
        r'(?:from|join)\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        sql_lower
    )

    # Allow system queries like SHOW, DESCRIBE
    if not sql_lower.startswith(("show", "describe")):

        for table in tables_in_query:
            if table not in valid_tables:
                st.error(f"❌ Table '{table}' not found in selected database")
                st.stop()

    if not sql_query.lower().startswith(("select", "with", "show", "describe")):
        st.error("❌ Invalid SQL")
        st.stop()

    if any(word in sql_query.lower() for word in ["drop", "delete", "update", "insert"]):
        st.error("❌ Unsafe query blocked")
        st.stop()

    st.success("✅ Safe Query")

    # Execute
    result = read_sql_query(sql_query, db_choice)

    if isinstance(result, str):
        st.warning("⚠️ Query failed. Trying to fix...")

        fix_prompt = f"""
        Fix this SQL query:
        {sql_query}
        Error: {result}
        Return only SQL.
        """

        fixed_sql = clean_sql(get_sql_query(fix_prompt, []))
        st.code(fixed_sql, language="sql")

        result = read_sql_query(fixed_sql, db_choice)

    # Display
    st.subheader("📊 Result")

    if isinstance(result, str):
        st.error(result)
        columns, rows = [], []
    else:
        columns, rows = result

        if rows:
            df = pd.DataFrame(rows, columns=columns)
            st.dataframe(df)
        else:
            st.warning("No data found")

    # Explanation
    explanation = client.chat.completions.create(
        model="openai/gpt-3.5-turbo",
        messages=[{"role": "user", "content": f"Explain this SQL in 2 lines:\n{sql_query}"}]
    )

    st.info("💡 " + explanation.choices[0].message.content)

    # Save Chat
    st.session_state.chat_history.append({"role": "user", "content": question})
    st.session_state.chat_history.append({"role": "assistant", "content": sql_query})
    st.session_state.chat_history.append({
        "role": "result",
        "columns": columns,
        "rows": rows
    })