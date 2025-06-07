import pathlib
import subprocess
import streamlit as st
import sys
from st_aggrid import AgGrid, GridOptionsBuilder
import seaborn as sns
import matplotlib.pyplot as plt
import scipy.stats as stats
import pandas as pd


sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

from scripts.utils import query_df, get_connection, run_sql, CELL_TYPES, BASE_DIR  # noqa: E402

# dynamically build the table w/ all cell types
sql_cell_types = [
    f"MAX(CASE WHEN cell_counts.cell_type = '{cell_type}' THEN cell_counts.count ELSE NULL END) AS {cell_type}"
    for cell_type in CELL_TYPES]

sql_query_samples = f'''
    SELECT
        projects.project_id,
        subjects.subject_id,
        subjects.condition,
        subjects.age,
        subjects.sex,
        treatments.treatment_id,
        samples.response,
        samples.sample_id,
        samples.sample_type,
        samples.time_from_treatment_start,
        {",\n".join(sql_cell_types)}
    FROM
        projects
    JOIN subjects ON projects.project_id = subjects.project_id
    JOIN samples ON subjects.subject_id = samples.subject_id
    LEFT JOIN treatments ON samples.treatment_id = treatments.treatment_id
    LEFT JOIN cell_counts ON samples.sample_id = cell_counts.sample_id
    GROUP BY
        samples.sample_id
    ORDER BY
        projects.project_id ASC
'''

sql_query_frequencies = '''
        SELECT
            cell_counts.sample_id,
            cell_counts.cell_type AS population,
            cell_counts.count,
            totals.total_count,
            100.0 * cell_counts.count / totals.total_count AS relative_frequency
        FROM
            cell_counts
        JOIN (
            SELECT sample_id,
                   SUM(count) AS total_count
            FROM cell_counts
            GROUP BY sample_id
        ) totals ON cell_counts.sample_id = totals.sample_id
    '''

sql_query_rich_frequencies = '''
        SELECT
            samples.sample_id,
            samples.subject_id,
            subjects.condition,
            subjects.age,
            subjects.sex,
            samples.treatment_id,
            samples.response,
            samples.sample_type,
            samples.time_from_treatment_start,
            projects.project_id,
            cell_counts.cell_type AS population,
            cell_counts.count AS count,
            total.total_count,
            100.0 * cell_counts.count / total.total_count AS relative_frequency
        FROM
            samples
        JOIN subjects ON samples.subject_id = subjects.subject_id
        JOIN projects ON subjects.project_id = projects.project_id
        LEFT JOIN treatments ON samples.treatment_id = treatments.treatment_id
        JOIN cell_counts ON samples.sample_id = cell_counts.sample_id
        JOIN (
            SELECT
                sample_id,
                SUM(count) AS total_count
            FROM
                cell_counts
            GROUP BY
                sample_id
        ) AS total ON samples.sample_id = total.sample_id
        ORDER BY
            samples.sample_id ASC, cell_counts.cell_type ASC
'''


def show_add_sample_form():
    with st.expander("**Add new sample**", expanded=False):
        with st.form("add_sample_form"):
            subjects_df = query_df("SELECT subject_id FROM subjects ORDER BY subject_id ASC")
            subjects_options = subjects_df['subject_id'].tolist()

            treatments_df = query_df("SELECT treatment_id FROM treatments ORDER BY treatment_id ASC")
            treatments_options = treatments_df['treatment_id'].dropna().tolist()

            sample_id = st.text_input("Sample ID")

            subject_id = st.selectbox("Subject", subjects_options) if subjects_options else st.warning(
                "No subjects available. Please add a subject first.")

            treatment_id = st.selectbox("Treatment", treatments_options)

            time_from_treatment_start = st.number_input("Time from treatment start", min_value=0)

            response = st.text_input("Response")
            sample_type = st.text_input("Sample type")

            st.markdown("#### Cell Counts")

            # dynamic cell count entry rows
            cell_count_inputs = []
            selected_cell_types = set()
            for i in range(st.session_state.cell_count_rows):
                available_cell_types = set(CELL_TYPES) - selected_cell_types
                cols = st.columns(2)
                cell_type = cols[0].selectbox(
                    f"Cell Type {i+1}",
                    options=available_cell_types,
                    key=f"cell_type_{i}"
                )
                selected_cell_types.add(cell_type)
                count = cols[1].number_input(f"Count {i+1}", min_value=0, key=f"cell_count_{i}")
                cell_count_inputs.append((cell_type, count))

            if st.session_state.cell_count_rows < len(CELL_TYPES) and st.form_submit_button("Add another cell count", icon="➕"):
                st.session_state.cell_count_rows += 1
                st.rerun()

            if st.form_submit_button("Submit entry", icon="➕"):
                errors = []
                if not sample_id:
                    errors.append("Sample ID is required.")
                if not subjects_options:
                    errors.append("You must add a subject first.")
                if response not in ('y', 'n'):
                    errors.append("Response is limited to y/n!")

                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    try:
                        insert_sample_sql = """
                            INSERT INTO samples (
                                sample_id,
                                subject_id,
                                treatment_id,
                                time_from_treatment_start,
                                response,
                                sample_type
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        """
                        params = (
                            sample_id,
                            subject_id,
                            treatment_id,
                            time_from_treatment_start,
                            response,
                            sample_type
                        )
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute(insert_sample_sql, params)

                        for cell_type, count in cell_count_inputs:
                            insert_cell_counts_sql = """
                                INSERT INTO cell_counts (sample_id, cell_type, count)
                                VALUES (?, ?, ?)
                            """
                            cursor.execute(insert_cell_counts_sql, (sample_id, cell_type, count))

                        conn.commit()
                        conn.close()

                        st.session_state.add_success = True
                        st.rerun()

                    except Exception as e:
                        st.error(f"Failed to add entry: {e}")

            if st.session_state.add_success:
                st.success("Added new entry successfully!")
                st.session_state.add_success = False


def show_add_project_form():
    with st.expander("**Add new project**", expanded=False):
        with st.form("add_project_form"):
            project_id = st.text_input("Project ID")

            if st.form_submit_button("Submit entry", icon="➕"):
                if not project_id:
                    st.error("Project ID is required.")
                else:
                    try:
                        insert_sql = "INSERT INTO projects (project_id) VALUES (?)"
                        run_sql(insert_sql, (project_id,))
                        st.session_state.add_success = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to add entry: {e}")

            if st.session_state.add_success:
                st.success("Added new entry successfully!")
                st.session_state.add_success = False


def show_add_subject_form():
    with st.expander("**Add new subject**", expanded=False):
        with st.form("add_subject_form"):
            projects_df = query_df("SELECT project_id FROM projects ORDER BY project_id ASC")
            project_options = projects_df['project_id'].tolist()

            subject_id = st.text_input("Subject ID")
            project_id = st.selectbox("Project", project_options) if project_options else st.warning(
                "No projects available. Please add a project first.")
            condition = st.text_input("Condition")
            age = st.number_input("Age", min_value=0)
            sex = st.selectbox("Sex", ["M", "F"])

            if st.form_submit_button("Submit entry", icon="➕"):
                errors = []
                if not subject_id:
                    errors.append("Subject ID is required.")
                if not project_options:
                    errors.append("You must add a project first.")

                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    try:
                        insert_sql = """
                            INSERT INTO subjects (subject_id, project_id, condition, age, sex)
                            VALUES (?, ?, ?, ?, ?)
                        """
                        params = (subject_id, project_id, condition, age, sex)
                        run_sql(insert_sql, params)
                        st.session_state.add_success = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to add entry: {e}")

            if st.session_state.add_success:
                st.success("Added new entry successfully!")
                st.session_state.add_success = False


def show_add_treatment_form():
    with st.expander("**Add new treatment**", expanded=False):
        with st.form("add_treatment_form"):
            treatment_id = st.text_input("Treatment ID")

            if st.form_submit_button("Submit entry", icon="➕"):
                if not treatment_id:
                    st.error("Treatment ID is required.")
                else:
                    try:
                        insert_sql = "INSERT INTO treatments (treatment_id) VALUES (?)"
                        run_sql(insert_sql, (treatment_id,))
                        st.session_state.add_success = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to add entry: {e}")

            if st.session_state.add_success:
                st.success("Added new entry successfully!")
                st.session_state.add_success = False


# a config to modularize code and allow hotswapping of tables without repeated code
PAGE_CONFIG = {
    "Samples": {
        "sql_query": sql_query_samples,
        "form_func": show_add_sample_form,
        "table_name": "samples",
        "id_field": "sample_id"
    },
    "Projects": {
        "sql_query": "SELECT * FROM projects ORDER BY project_id ASC",
        "form_func": show_add_project_form,
        "table_name": "projects",
        "id_field": "project_id"
    },
    "Subjects": {
        "sql_query": "SELECT * FROM subjects ORDER BY subject_id ASC",
        "form_func": show_add_subject_form,
        "table_name": "subjects",
        "id_field": "subject_id"
    },
    "Treatments": {
        "sql_query": "SELECT * FROM treatments ORDER BY treatment_id ASC",
        "form_func": show_add_treatment_form,
        "table_name": "treatments",
        "id_field": "treatment_id"
    }
}

# used to preserve row deletion success message after rerun
if 'delete_success' not in st.session_state:
    st.session_state.delete_success = False

# used to preserve add entry success message after rerun
if 'add_success' not in st.session_state:
    st.session_state.add_success = False

# use session_state to keep track of how many cell types the user wants to input
if 'cell_count_rows' not in st.session_state:
    st.session_state.cell_count_rows = 1

# sidebar
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Choose table to view / add to:",
    ["Samples", "Projects", "Subjects", "Treatments"]
)

if st.sidebar.button("Reload", help="Reload data from CSV", icon="🔄"):
    try:
        result = subprocess.run(
            [sys.executable, BASE_DIR / "scripts" / "load_data.py"],
            capture_output=True,
            text=True,
            check=True
        )
        st.success("Reloaded successfully!")
    except subprocess.CalledProcessError as e:
        st.error(f"Failed to run load_data.py:\n{e.stderr}")

# body text
st.title("Loblaw Bio Analytics Dashboard")
st.write("If you'd like to add new entries to other tables, please use the sidebar. Analysis can be found farther down the Samples page.")

config = PAGE_CONFIG[page]
st.header(page)

# pull up add entry form
if config["form_func"]:
    config["form_func"]()

df = query_df(config["sql_query"])

# using AgGrid for an interactive table!
gb = GridOptionsBuilder.from_dataframe(df)
if config['form_func']:  # ignore checkboxes if it's a table w/o CRUD
    gb.configure_selection('multiple', use_checkbox=True, groupSelectsChildren=True)

gb.configure_default_column(filter=True, autoSize=True, resizable=True)
gb.configure_grid_options(autoSizeStrategy={'type': 'fitCellContents'})

gridOptions = gb.build()

grid_response = AgGrid(
    df,
    gridOptions=gridOptions,
    update_on="SelectionChanged",
    theme="streamlit"
)

df_filtered = grid_response['data']
st.write(f"{df_filtered.shape[0]} rows showing")

# delete button logic
if config['form_func']:  # again, ignore deleting if no CRUD
    selected_rows = grid_response['selected_rows']

    if selected_rows is not None and not selected_rows.empty:
        st.write(f"Selected {len(selected_rows)} row(s).")

        if st.button("Delete selected rows", icon="🗑️"):
            ids_to_delete = selected_rows[config['id_field']].tolist()
            try:
                placeholders = ",".join("?" for _ in ids_to_delete)
                delete_sql = f"DELETE FROM {config['table_name']} WHERE {config['id_field']} IN ({placeholders})"
                run_sql(delete_sql, ids_to_delete)
                st.success(f"Deleted {len(ids_to_delete)} rows successfully.")
                st.session_state.delete_success = True
                st.rerun()
            except Exception as e:
                st.error(f"Failed to delete rows: {e}")
    else:
        st.info("Select rows to delete.")
        if st.session_state.delete_success:
            st.success("Deleted rows successfully!")
            st.session_state.delete_success = False

if page == "Samples":
    with st.expander("**Filtered Stats**"):
        num_samples = df_filtered['sample_id'].nunique()
        num_subjects = df_filtered['subject_id'].nunique()
        num_responders = (df_filtered['response'] == 'y').sum()
        num_nonresponders = (df_filtered['response'] == 'n').sum()
        num_males = (df_filtered['sex'] == 'M').sum()
        num_females = (df_filtered['sex'] == 'F').sum()
        projects_breakdown = df_filtered.groupby(
            'project_id')['sample_id'].nunique().rename("total_samples").reset_index()

        st.write(f"- Number of samples: {num_samples}")
        st.write(f"- Number of subjects: {num_subjects}")
        st.write(f"- Samples from responders (y): {num_responders}")
        st.write(f"- Samples from non-responders (n): {num_nonresponders}")
        st.write(f"- Samples from male subjects: {num_males}")
        st.write(f"- Samples from female subjects: {num_females}")

    with st.expander("**Samples Per Project**"):
        st.dataframe(projects_breakdown)

    st.markdown("### Relative Frequencies")
    st.write("The following visualizations are tied to this table. Any filtering you do will update the visualizations below.")
    df_freq = query_df(sql_query_rich_frequencies)
    gb_freq = GridOptionsBuilder.from_dataframe(df_freq)
    gb_freq.configure_default_column(filter=True, autoSize=True, resizable=True)
    gb_freq.configure_grid_options(autoSizeStrategy={'type': 'fitCellContents'})
    gridOptions_freq = gb_freq.build()

    grid_response_freq = AgGrid(
        df_freq,
        gridOptions=gridOptions_freq,
        update_on="SelectionChanged",
        theme="streamlit"
    )

    df_filtered_freq = grid_response_freq['data']

    with st.expander("**Box Plot**"):
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.boxplot(
            data=df_filtered_freq[df_filtered_freq['response'].isin(['y', 'n'])],
            x='population',
            y='relative_frequency',
            hue='response',
            ax=ax
        )
        ax.set_ylabel("Relative Frequency (%)")
        ax.set_xlabel("Cell Population")
        ax.set_title("Relative Frequencies: Responders vs Non-Responders")
        st.pyplot(fig)

    stat_results = []
    for cell_type in df_filtered_freq['population'].unique():
        df_cell_type = df_filtered_freq[df_filtered_freq['population'] == cell_type]
        responders = df_cell_type[df_cell_type['response'] == 'y']['relative_frequency']
        nonresponders = df_cell_type[df_cell_type['response'] == 'n']['relative_frequency']
        if len(responders) > 0 and len(nonresponders) > 0:
            u_stat, p_val = stats.mannwhitneyu(responders, nonresponders)
            stat_results.append({
                'Population': cell_type,
                'p-value': p_val,
                '# Responders': len(responders),
                '# Non-Responders': len(nonresponders)
            })

    stat_df = pd.DataFrame(stat_results).sort_values('p-value')
    st.dataframe(stat_df.style.format({'p-value': '{:.4f}'}))
