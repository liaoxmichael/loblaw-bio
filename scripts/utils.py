from pathlib import Path
import sqlite3
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "sample_data.sqlite"
CELL_COUNT_CSV = BASE_DIR / "data" / "cell-count.csv"
CELL_TYPES = ['b_cell', 'cd8_t_cell', 'cd4_t_cell', 'nk_cell', 'monocyte']


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def query_df(query):
    conn = get_connection()
    cursor = conn.execute(query)
    return pd.DataFrame(cursor.fetchall(), columns=[desc[0] for desc in cursor.description])


def run_sql(query, params=None):
    """
    Run a SQL query with optional parameters.
    Commits if query modifies data.
    Returns fetched rows for SELECT.
    """
    if params is None:
        params = ()

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(query, params)

        if query.strip().upper().startswith("SELECT"):
            results = cur.fetchall()
            return [dict(row) for row in results]
        else:
            conn.commit()
            return None
