import pandas as pd
import sqlite3

CELL_COUNT_CSV = "cell_count.csv"
DB_PATH = "sample_data.sqlite"


def init_db(db_path):
    """Initialize the SQLite database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            project_id TEXT PRIMARY KEY
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            subject_id TEXT PRIMARY KEY,
            project_id TEXT FOREIGN KEY REFERENCES projects(project_id),
            condition TEXT,
            age INTEGER,
            sex TEXT)
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS treatments (
            treatment_id TEXT PRIMARY KEY
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS samples (
            sample_id TEXT PRIMARY KEY,
            subject_id TEXT FOREIGN KEY REFERENCES subjects(subject_id) NOT NULL,
            treatment_id TEXT FOREIGN KEY REFERENCES treatments(treatment_id),
            time_from_treatment_start INTEGER,
            response TEXT,
            sample_type TEXT,
    ''')

    cursor.execute('''
            CREATE TABLE IF NOT EXISTS cell_counts (
                sample_id TEXT FOREIGN KEY REFERENCES samples(sample_id) NOT NULL,
                cell_type TEXT,
                count INTEGER,
                PRIMARY KEY (sample_id, cell_type)
            )
    ''')

    conn.commit()
    conn.close()


def load_data_from_csv(file_path):
    pd.read_csv(file_path)


if __name__ == "__main__":
    init_db(DB_PATH)
    load_data_from_csv(CELL_COUNT_CSV)
    print(f"Database initialized at {DB_PATH} and data loaded from {CELL_COUNT_CSV}.")
