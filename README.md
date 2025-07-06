# MySQL ADK Agent

This project implements an intelligent agent using the Google Agent Development Kit (ADK). The agent is capable of understanding questions in natural language, converting them into SQL queries, executing the query on a MySQL database, and returning the results.

The key feature of this agent is its use of a "prompt engineering" script that inspects the database schema to create a rich and detailed context, allowing the AI model to generate much more accurate and complex SQL queries.

## Project Structure
```
/adk_mysql_agent/                  # Root project folder
|
├── .venv/                         # Virtual environment directory
|
├── mysql_agent/                   # Python package containing the agent's source code
│   ├── __init__.py                # Makes the directory a Python package
│   ├── .env                       # File to store credentials (not versioned)
│   ├── agent.py                   # Defines the main agent (root agent)
│   ├── config.yaml                # Agent deployment settings
│   ├── generate_mysql_prompt.py   # Script to analyze the DB and generate the context
│   ├── mysql_prompt.txt           # Generated enhanced prompt file
│   ├── prompt.py                  # Stores the prompt template and joins with the context
│   └── tools.py                   # Contains the tool that executes SQL queries
|
├── deploy_agent_engine.ipynb      # Python notebook to step-by-step deploy on Vertex Agent Engine
├── requirements.txt               # File listing Python dependencies
└── README.md                      # This file
```

## Prerequisites

* Python 3.12 or higher
* Access to a MySQL database.

## Installation and Execution Guide

Follow the steps below to set up and run the project.

### 1. Clone the Repository (Optional)

If you are starting on a new machine, clone the repository.

```
git clone git@github.com:speca-google/adk_mysql_agent.git
cd adk_mysql_agent
```

### 2. Create and Activate the Virtual Environment (venv)

It is a good practice to isolate the project's dependencies in a virtual environment.

Create the virtual environment
```
python -m venv .venv
```

Activate the virtual environment
```
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

### 3. Install Dependencies
```
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a file named `.env` inside the `mysql_agent/` directory and fill it with your credentials.

**`mysql_agent/.env` Example:**

```env
# --- Vertex AI Settings ---
# You can leave GOOGLE_GENAI_USE_VERTEXAI as "True" if deploying on GCP
GOOGLE_GENAI_USE_VERTEXAI="True"
GOOGLE_CLOUD_PROJECT="your-gcp-project-id"   # Project ID from GCP (where Agent is going to run)
GOOGLE_CLOUD_LOCATION="us-central1"          # Location where the agent will be deployed
GOOGLE_CLOUD_BUCKET="gs://your-agent-bucket" # Bucket for deployment on Agent Engine

# --- Agent Models ---
# The model used by the main agent to understand user intent and orchestrate tools.
ROOT_AGENT_MODEL="gemini-2.5-flash"
# The model used by the prompt generator script.
LLM_MODEL="gemini-2.5-flash"

# --- MySQL Database Settings ---
MYSQL_HOST="localhost"           # e.g., localhost or a remote IP/hostname
MYSQL_DATABASE="your_database"   # The name of the database to connect to
MYSQL_USER="your_db_user"        # The username for the database
MYSQL_PASSWORD="your_db_password" # The password for the database user
```

### 5. Generate the Database Context

Run the `generate_mysql_prompt.py` script from the project's root directory. It will connect to your MySQL database, collect metadata and samples, and then use Gemini to generate a complete and optimized prompt file.

Make sure your current directory is the project root
```
python mysql_agent/generate_mysql_prompt.py
````

After execution, a new file named `mysql_prompt.txt` will be created in the `mysql_agent/` directory. This file contains the detailed context about your database schema that the agent will use.

### 6. Run the Agent Locally for Testing

Now that everything is configured, you can start the agent using ADK web.
```
adk web
```
The `adk web` command will open a web UI to test your agent. If you get a permission error, don't forget to authenticate your gcloud application-default credentials.
```
gcloud auth application-default login
```

### 7. Deploy this agent on Agent Engine

To deploy this agent, use the Python Notebook `deploy_agent_engine.ipynb`. This file contains a step-by-step guide for deployment.