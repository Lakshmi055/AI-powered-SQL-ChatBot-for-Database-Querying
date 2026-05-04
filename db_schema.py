import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

# ==============================
# DATABASE CONNECTION (REUSABLE)
# ==============================

def connect_db(db_name=None):
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=db_name if db_name else None
    )

# ==============================
# GET ALL DATABASES
# ==============================

def get_databases():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SHOW DATABASES")
    dbs = [db[0] for db in cursor.fetchall()]

    conn.close()
    return dbs

# ==============================
# GET DATABASE SCHEMA
# ==============================

def get_db_schema(db_name):
    conn = connect_db(db_name)
    cursor = conn.cursor()

    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()

    schema = {}

    for (table_name,) in tables:
        cursor.execute(f"DESCRIBE {table_name}")
        columns = cursor.fetchall()
        schema[table_name] = [col[0] for col in columns]

    conn.close()
    return schema

# ==============================
# FORMAT SCHEMA FOR LLM
# ==============================

def format_schema(schema_dict):
    schema_text = "Database Schema:\n"

    for table, cols in schema_dict.items():
        schema_text += f"{table}({', '.join(cols)})\n"

    return schema_text

# ==============================
# GET RELATIONSHIPS 
# ==============================

def get_relationships(db_name):
    conn = connect_db(db_name)
    cursor = conn.cursor()

    query = f"""
    SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
    WHERE REFERENCED_TABLE_SCHEMA = '{db_name}'
    AND REFERENCED_TABLE_NAME IS NOT NULL;
    """

    cursor.execute(query)
    relations = cursor.fetchall()

    conn.close()

    rel_text = "Relationships:\n"

    for t, c, rt, rc in relations:
        rel_text += f"{t}.{c} = {rt}.{rc}\n"

    return rel_text