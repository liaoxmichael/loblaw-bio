import pandas as pd
import sqlite3

CELL_COUNT_CSV = "cell-count.csv"
DB_PATH = "sample_data.sqlite"
CELL_TYPES = ['b_cell', 'cd8_t_cell', 'cd4_t_cell', 'nk_cell', 'monocyte']


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
            project_id TEXT,
            condition TEXT,
            age INTEGER,
            sex TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(project_id)
            )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS treatments (
            treatment_id TEXT PRIMARY KEY
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS samples (
            sample_id TEXT PRIMARY KEY,
            subject_id TEXT NOT NULL,
            treatment_id TEXT,
            time_from_treatment_start INTEGER,
            response TEXT,
            sample_type TEXT,
            FOREIGN KEY (subject_id) REFERENCES subjects(subject_id),
            FOREIGN KEY (treatment_id) REFERENCES treatments(treatment_id)
        )
    ''')

    cursor.execute('''
            CREATE TABLE IF NOT EXISTS cell_counts (
                sample_id TEXT NOT NULL,
                cell_type TEXT,
                count INTEGER,
                PRIMARY KEY (sample_id, cell_type),
                FOREIGN KEY (sample_id) REFERENCES samples(sample_id)
            )
    ''')

    conn.commit()
    conn.close()


def load_data_from_csv(file_path):
    df = pd.read_csv(file_path)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for project_id in df['project'].unique():
        cursor.execute('INSERT OR IGNORE INTO projects (project_id) VALUES (?)', (project_id,))

    subjects = df[['subject', 'project', 'condition', 'age', 'sex']].drop_duplicates()
    for _, row in subjects.iterrows():
        cursor.execute('''
            INSERT OR IGNORE INTO subjects (subject_id, project_id, condition, age, sex)
            VALUES (?, ?, ?, ?, ?)
        ''', (row['subject'], row['project'], row['condition'], row['age'], row['sex']))

    for treatment_id in df['treatment'].unique():
        cursor.execute('INSERT OR IGNORE INTO treatments (treatment_id) VALUES (?)', (treatment_id,))

    samples = df[['sample', 'subject', 'treatment',
                  'time_from_treatment_start', 'response', 'sample_type']].drop_duplicates()
    for _, row in samples.iterrows():
        cursor.execute('''
            INSERT OR IGNORE INTO samples (sample_id, subject_id, treatment_id, time_from_treatment_start, response, sample_type)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (row['sample'], row['subject'], row['treatment'], row['time_from_treatment_start'], row['response'], row['sample_type']))

    for _, row in df.iterrows():
        for cell_type in CELL_TYPES:
            cursor.execute('''
                INSERT OR IGNORE INTO cell_counts (sample_id, cell_type, count)
                VALUES (?, ?, ?)
            ''', (row['sample'], cell_type, row[cell_type]))

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db(DB_PATH)
    load_data_from_csv(CELL_COUNT_CSV)
    print(f"Database initialized at {DB_PATH} and data loaded from {CELL_COUNT_CSV}.")
