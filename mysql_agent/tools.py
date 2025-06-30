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

# Load environment variables from the .env file
load_dotenv()

# --- MySQL Connection Details (from .env) ---
MYSQL_HOST = os.environ.get("MYSQL_HOST")
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE")
MYSQL_USER = os.environ.get("MYSQL_USER")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD")

def query_mysql(sql_query: str) -> dict:
    """
    Executes a raw SQL query against the MySQL database and returns the results.
    Pagination should be handled directly in the SQL query using LIMIT and OFFSET clauses.

    Args:
        sql_query (str): The complete and valid SQL query string to execute.

    Returns:
        dict: A dictionary containing a 'data' key with a list of rows on success,
              or an 'error' key with a message on failure. Each row is a dictionary
              mapping column names to values.
    """
    # Check if all required environment variables for the database connection are set
    if not all([MYSQL_HOST, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD]):
        return {"error": "MySQL connection details are not fully configured in the environment."}

    connection = None
    cursor = None
    try:
        # Establish the database connection
        connection = mysql.connector.connect(
            host=MYSQL_HOST,
            database=MYSQL_DATABASE,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD
        )

        # Check if the connection was successful
        if connection.is_connected():
            # Create a cursor that returns rows as dictionaries
            cursor = connection.cursor(dictionary=True)
            
            # Execute the provided SQL query
            cursor.execute(sql_query)
            
            # Fetch all the rows from the query result
            result = cursor.fetchall()
            
            # Return the successful response
            return {"data": result}

    except Error as e:
        # Handle potential database errors (e.g., connection, syntax)
        return {
            "error": "Failed to execute SQL query in MySQL.",
            "details": f"MySQL Error: {e}",
            "sql_sent": sql_query
        }
    finally:
        # Ensure the cursor and connection are closed to free up resources
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

# --- Example Usage (optional, for testing) ---
if __name__ == '__main__':
    # Example: Select the first 10 users from a 'users' table
    example_query = "SELECT id, name, email FROM users LIMIT 10;"
    
    # Execute the query
    query_result = query_mysql(example_query)
    
    # Print the result
    if "error" in query_result:
        print(f"An error occurred: {query_result['error']}")
        if "details" in query_result:
            print(f"Details: {query_result['details']}")
    else:
        print("Query executed successfully. Results:")
        import json
        print(json.dumps(query_result.get('data', []), indent=2))
