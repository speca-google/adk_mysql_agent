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

# tools.py
import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import datetime # Import required for handling date/time objects

# Load environment variables from the .env file
load_dotenv()

# --- MySQL Connection Details (from .env) ---
MYSQL_HOST = os.environ.get("MYSQL_HOST")
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE")
MYSQL_USER = os.environ.get("MYSQL_USER")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD")


def _serialize_rows(rows: list) -> list:
    """
    Internal helper to iterate through rows and convert non-serializable
    types (like date/datetime) to strings in ISO format.
    """
    serialized_rows = []
    for row in rows:
        serialized_row = {}
        for key, value in row.items():
            if isinstance(value, (datetime.datetime, datetime.date)):
                serialized_row[key] = value.isoformat()
            else:
                serialized_row[key] = value
        serialized_rows.append(serialized_row)
    return serialized_rows


def _json_to_markdown_table(data_list: list) -> str:
    """
    Internal helper to convert a list of dictionaries into a Markdown formatted table.
    """
    if not data_list:
        return "No results found."

    # Use the keys from the first dictionary as headers
    headers = data_list[0].keys()
    header_row = "| " + " | ".join(map(str, headers)) + " |"
    separator_row = "| " + " | ".join(["---"] * len(headers)) + " |"
    
    # Create data rows
    data_rows = []
    for row_dict in data_list:
        # Ensure values are retrieved in the same order as headers
        row_values = [str(row_dict.get(header, '')) for header in headers]
        data_rows.append("| " + " | ".join(row_values) + " |")
        
    return "\n".join([header_row, separator_row] + data_rows)


def query_mysql(sql_query: str) -> dict:
    """
    Executes a raw SQL query against the MySQL database and formats the entire
    result set into a single Markdown table.

    Args:
        sql_query (str): The complete and valid SQL query string to execute.

    Returns:
        dict: A dictionary containing a 'results_markdown' key with the data
              as a Markdown table string on success, or an 'error' key on failure.
    """
    if not all([MYSQL_HOST, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD]):
        return {"error": "MySQL connection details are not fully configured in the environment."}

    connection = None
    cursor = None
    try:
        connection = mysql.connector.connect(
            host=MYSQL_HOST, database=MYSQL_DATABASE, user=MYSQL_USER, password=MYSQL_PASSWORD
        )

        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            cursor.execute(sql_query)
            result = cursor.fetchall()
            
            # First, serialize the data to handle dates/datetimes correctly.
            serialized_result = _serialize_rows(result)
            
            # Then, convert the entire result set into a single Markdown table string.
            markdown_output = _json_to_markdown_table(serialized_result)
            
            # Return the final formatted string in the response dictionary.
            return {"results_markdown": markdown_output}

    except Error as e:
        return {
            "error": "Failed to execute SQL query in MySQL.",
            "details": f"MySQL Error: {e}", "sql_sent": sql_query
        }
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()