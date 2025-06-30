# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# generate_mysql_prompt.py
import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel

# Load environment variables from your .env file
load_dotenv()

# --- Configuration ---
# MySQL Connection Details (from .env)
MYSQL_HOST = os.environ.get("MYSQL_HOST")
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE")
MYSQL_USER = os.environ.get("MYSQL_USER")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD")

# Google Cloud AI / Gemini Configuration (from .env)
GCP_PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
GCP_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION")
LLM_MODEL = os.environ.get("LLM_MODEL")

# The output filename for the generated prompt context.
OUTPUT_FILENAME = "mysql_context.txt"

# =======================================================================
# HELPER FUNCTIONS TO FETCH MYSQL METADATA
# =======================================================================

def get_accessible_tables(cursor):
    """Fetches a list of accessible tables for the current database."""
    print("  Fetching table list...")
    # In MySQL, DATABASE() returns the current database name.
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    return [row[0] for row in cursor.fetchall()]

def get_table_schema(cursor, table_name: str):
    """Retrieves the schema (columns and data types) for a specific table."""
    try:
        # DESCRIBE is a safe way to get schema info. Use backticks for safety.
        cursor.execute(f"DESCRIBE `{table_name}`;")
        # Result of DESCRIBE: (Field, Type, Null, Key, Default, Extra)
        return [f"`{col[0]}`: **{col[1].upper()}**" for col in cursor.fetchall()]
    except Error as e:
        print(f"    ❌ Error getting schema for table `{table_name}`: {e}")
        return [f"Error retrieving schema: {e}"]

def get_sample_rows(cursor, table_name: str, limit: int = 3):
    """Gets a few sample rows from the table and formats them as a Markdown table."""
    try:
        # Use backticks and parameterized limit to prevent SQL injection.
        query = f"SELECT * FROM `{table_name}` LIMIT %s;"
        cursor.execute(query, (limit,))
        
        colnames = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        if not rows:
            return f"No sample rows found for table `{table_name}`."

        # Format as a Markdown table
        header = f"| {' | '.join(colnames)} |"
        separator = f"|{'|'.join(['---'] * len(colnames))}|"
        body = "\n".join([f"| {' | '.join(map(str, row))} |" for row in rows])
        
        return f"{header}\n{separator}\n{body}"
    except Error as e:
        print(f"    ❌ Warning: Could not retrieve samples for table `{table_name}`. Error: {e}")
        return f"Could not retrieve samples for table `{table_name}`. Details: {e}"

def get_column_data_analysis(cursor, table_name: str):
    """Performs basic data analysis on table columns for MySQL."""
    analysis_lines = []
    try:
        cursor.execute(f"DESCRIBE `{table_name}`;")
        columns = cursor.fetchall()
    except Error as e:
        print(f"    ❌ Could not describe table `{table_name}` for analysis. Error: {e}")
        return [f"Could not analyze table. Error: {e}"]

    for col_name, data_type, _, _, _, _ in columns:
        safe_col_name = f"`{col_name}`"
        safe_table_name = f"`{table_name}`"

        # Analysis for numeric types
        numeric_types = ['int', 'bigint', 'decimal', 'float', 'double', 'tinyint', 'smallint']
        if any(ntype in data_type.lower() for ntype in numeric_types):
            try:
                query = f"SELECT MIN({safe_col_name}), MAX({safe_col_name}), AVG({safe_col_name}), COUNT(DISTINCT {safe_col_name}) FROM {safe_table_name};"
                cursor.execute(query)
                min_val, max_val, avg_val, distinct_count = cursor.fetchone()
                if all(v is not None for v in [min_val, max_val, avg_val]):
                     analysis_lines.append(f"- **{col_name}**: Numeric. MIN=`{min_val}`, MAX=`{max_val}`, AVG=`{avg_val:.2f}`, Distinct Values=`{distinct_count}`")
            except Error:
                pass  # Ignore columns that can't be aggregated

        # Analysis for text/char types
        text_types = ['char', 'varchar', 'text', 'enum']
        if any(ttype in data_type.lower() for ttype in text_types):
            try:
                cursor.execute(f"SELECT COUNT(DISTINCT {safe_col_name}) FROM {safe_table_name} WHERE {safe_col_name} IS NOT NULL;")
                distinct_count = cursor.fetchone()[0]

                cursor.execute(f"""
                    SELECT {safe_col_name} FROM {safe_table_name} WHERE {safe_col_name} IS NOT NULL
                    GROUP BY {safe_col_name} ORDER BY COUNT(*) DESC LIMIT 5;
                """)
                top_values = ', '.join([f'`{row[0]}`' for row in cursor.fetchall()])
                if distinct_count > 0:
                    analysis_lines.append(f"- **{col_name}**: Text. Distinct Values=`{distinct_count}`. Top values: {top_values}")
            except Error:
                pass # Ignore errors on complex text fields

    return analysis_lines if analysis_lines else ["No specific column analysis was possible."]


# =======================================================================
# FUNCTION TO GENERATE PROMPT WITH GEMINI
# =======================================================================
def generate_enhanced_prompt_with_gemini(database_context: str):
    """Uses Gemini to construct the full, enhanced prompt based on MySQL context."""
    print("\n--- Generating Full Prompt with Gemini ---")
    if not all([GCP_PROJECT_ID, GCP_LOCATION]):
        print("❌ GCP_PROJECT_ID and GCP_LOCATION must be set in your .env file for Gemini.")
        return None

    try:
        vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)
        model = GenerativeModel(LLM_MODEL)
    except Exception as e:
        print(f"❌ Error initializing Vertex AI: {e}")
        return None

    instruction_for_gemini = f"""
You are an expert MySQL developer and a master prompt engineer. Your goal is to construct a complete and highly effective prompt for converting natural language questions into MySQL queries.
You have been provided with a detailed breakdown of a database below under the "DATABASE INFORMATION" section.

Your task is to generate a complete prompt that includes the following, in this exact order:
1.  An "OVERVIEW" section that you will write.
2.  The full "DATABASE INFORMATION" (Schema, Examples, and Analysis) provided to you.
3.  A section of "IMPORTANT MYSQL NOTES" that you will write.
4.  A section with 7 new, complex, and insightful examples of questions and their corresponding MySQL queries. These examples should demonstrate how to join the provided tables.

CRITICAL INSTRUCTIONS:
- Your entire response will be the final content for the prompt. Start your response *directly* with `## OVERVIEW:`. Do not include any preamble or other text.
- **OVERVIEW:** Write a concise, natural language summary describing what this database appears to be used for, based on the table names (proceso, tramite, etapa, tarea) and their schemas. It looks like a workflow or process management system.
- **IMPORTANT MYSQL NOTES:** Create a bulleted list of key MySQL syntax rules. Include notes on using backticks `` for table/column names, using single quotes for strings, the importance of `JOIN` clauses between the tables, using `LIKE` for partial text matches, and date functions if applicable.
- **EXAMPLES:** The examples must follow the exact format: `**Question:** "..."` followed on a new line by `**SQL Query:** "..."`. The SQL query must be a single line. These examples MUST be complex, using `JOIN`s, `GROUP BY`, `WHERE` clauses, and aggregate functions (`COUNT`, `AVG`, etc.) to answer realistic business questions about processes, tasks, and stages.

---
{database_context}
"""

    print("Sending request to Gemini... (This may take a moment)")
    try:
        response = model.generate_content(instruction_for_gemini)
        return response.text
    except Exception as e:
        print(f"❌ An error occurred during the Gemini API call: {e}")
        return None

# =======================================================================
# MAIN ORCHESTRATION FUNCTION
# =======================================================================
def main():
    """
    Connects to MySQL, analyzes its metadata, uses Gemini to build a final prompt,
    and writes it to a text file.
    """
    db_params = {
        'host': MYSQL_HOST, 'database': MYSQL_DATABASE,
        'user': MYSQL_USER, 'password': MYSQL_PASSWORD
    }
    if not all(db_params.values()):
        print("❌ Exiting. Please configure MySQL environment variables in your .env file.")
        return

    print("--- Starting MySQL Database Analysis ---")
    db_context = {"schema": {}, "examples": {}, "analysis": {}}
    connection = None
    try:
        connection = mysql.connector.connect(**db_params)
        cursor = connection.cursor()
        print(f"✅ Successfully connected to MySQL database '{MYSQL_DATABASE}'.")
        
        tables = get_accessible_tables(cursor)
        if not tables:
            print("❌ No tables specified or found. Exiting.")
            return

        for i, table in enumerate(tables):
            print(f"  ({i+1}/{len(tables)}) Processing table: `{table}`")
            db_context["schema"][table] = get_table_schema(cursor, table)
            db_context["examples"][table] = get_sample_rows(cursor, table)
            db_context["analysis"][table] = get_column_data_analysis(cursor, table)

    except Error as e:
        print(f"\n❌ Database Error: {e}")
        return
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            print("\n✅ Database analysis complete. Connection closed.")

    # Assemble all gathered information into a single string for Gemini
    info_lines = ["\n# DATABASE INFORMATION\n"]
    info_lines.append("## Database Schema:")
    for table, schema in db_context["schema"].items():
        info_lines.append(f"\n### Table: `{table}`")
        info_lines.extend([f"- {col}" for col in schema])
    
    info_lines.append("\n---\n## Table Data Samples:")
    for table, example in db_context["examples"].items():
        info_lines.append(f"\n### Samples for table `{table}`:\n{example}")

    info_lines.append("\n---\n## Column Data Analysis:")
    for table, analysis in db_context["analysis"].items():
        if analysis:
            info_lines.append(f"\n### Analysis of Table `{table}`:")
            info_lines.extend(analysis)
    
    database_context_for_gemini = "\n".join(info_lines)

    # Use Gemini to generate the final prompt content
    final_prompt_content = generate_enhanced_prompt_with_gemini(database_context_for_gemini)

    if not final_prompt_content:
        print("\n❌ Prompt generation failed. No file will be written.")
        return

    # Write the result to the output file
    try:
        with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
            f.write(final_prompt_content)
        print(f"\n✅ Success! Prompt saved to: **{OUTPUT_FILENAME}**")
    except IOError as e:
        print(f"\n❌ Error saving file: {e}")

if __name__ == "__main__":
    main()
