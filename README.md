# Aligner - Camunda BPMN Checker & Sync Tool

**Aligner** is a powerful visual utility and CLI designed to compare, validate, and synchronize BPMN process models across different Camunda 7 engine environments and local workspaces. 

Whether you are trying to find configuration drift securely between production and staging Camunda setups, or you want to easily validate and deploy local BPMN definitions to a target server, Aligner provides both a command-line interface (CLI) and a modern, intuitive web dashboard.

## ✨ Features

- **Folder vs. Server:** Compare your local BPMN files (stored within a structured technical directory) against deployed definitions on a Camunda server. 
- **Server vs. Server:** Comprehensively compare definitions between two different Camunda 7 engines (e.g., Staging vs. Production) and easily identify matching files, missing files, and content drift.
- **Sync & Deploy:** Prepare process syncs directly from the dashboard and rapidly deploy grouped process definitions to destination environments.
- **Visual BPMN Comparisons:** When a difference is detected between Source and Target servers, the web dashboard utilizes `bpmn-js` to render the diagrams allowing visual configuration validation.
- **Application Context Mapping:** Interactively map specific folders and project segments to their respective Engine Context Paths (`mapping.json`) right from the configuration tab.
- **Dual Interface:** Run simple, direct terminal commands, or spin up the rich web UI (`python main.py ui`).

## 🛠 Installation

1. Ensure you have Python 3.8+ installed. Navigate to the project directory:
   ```bash
   cd camunda_bpmn_checker/camunda_bpmn_checker
   ```

2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   
   # For Windows:
   venv\Scripts\activate
   # For macOS/Linux:
   source venv/bin/activate 
   ```

3. Install the dependencies via `pip`:
   ```bash
   pip install -r requirements.txt
   ```

## ⚙ Configuration

Aligner utilizes environment variables to connect to your Camunda servers natively. Create a `.env` file in the same directory as `main.py` and assign the following variables (adjust paths and URLs matching your environments):

```ini
# Default Base Node URLs
CAMUNDA_BASE_URL=http://localhost:8080

# Primary REST API Endpoints
SOURCE_CAMUNDA_REST_URL=http://localhost:8080/engine-rest
TARGET_CAMUNDA_REST_URL=http://localhost:8081/engine-rest

# Workspace Settings
GIT_REPO_PATH=.
TECHNICAL_FOLDER_PATH=C:\Users\Vidmay\Documents\projects\camunda_bpmn_checker\Technical Folder
```

## 🎯 Usage

### 🌐 Web Dashboard (Recommended)
To launch the interactive dashboard, run:
```bash
python main.py ui
```
This sets up a robust local web server running on port `5000` and will attempt to open it automatically in your default internet browser. Navigate through the internal tabs to perform Server-Checks or Deployments visually.

### 💻 CLI Commands
Alternatively, you can skip the UI to work strictly from the terminal:

- **Check Alignment:** Validates deployed process definitions against the active Git representation:
  ```bash
  python main.py check
  ```
- **Sync Environments:** Prepares and downloads payloads from a Source Engine and triggers structured deployments into the Target engine:
  ```bash
  python main.py sync
  ```
- **Compare Server Nodes:** Lists exact differences (modifications and non-existent deployments) natively between the Source and Target engines configured in your `.env`.
  ```bash
  python main.py compare-servers
  ```

---
*Built with Python, Flask, bpmn-js, and Vanilla CSS/JS.*
