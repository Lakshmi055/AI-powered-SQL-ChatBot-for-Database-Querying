import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

# ==============================
# Execute SQL Query
# ==============================

def read_sql_query(sql, db_name):
    conn = None
    cur = None

    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=db_name
        )

        # Dictionary cursor
        cur = conn.cursor(dictionary=True)

        cur.execute(sql)

        rows = cur.fetchall()

        #
        if cur.description:
            columns = [desc[0] for desc in cur.description]
        else:
            columns = []

        return columns, rows

    except Exception as e:
        return f"❌ SQL Error: {str(e)}"

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()