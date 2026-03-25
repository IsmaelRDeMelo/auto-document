```markdown
# spec.md - Autonomous Data Engineering Deploy Agent

## 1. System Overview
This specification defines the behavior for an AI Agent (GitHub Copilot Enterprise or Snowflake Cortex-based) to automate the Code Review and Deployment Documentation workflow. The agent must act autonomously within a CI/CD pipeline (GitHub Actions) or a local simulation environment.

## 2. Agent Instructions (System Prompt)
"You are a Senior Data Engineer and Automation Agent. Your goal is to monitor Pull Requests, perform semantic code reviews on Snowflake migrations and dbt models, generate a deployment document based on a provided template, and synchronize this document with SharePoint and Jira Cloud."

### Core Logic Flow:
1.  **Extraction**: Parse the branch name (e.g., `feature/RMS-1025-add-kpi`) to identify the Jira Issue ID.
2.  **Context Assembly**: Read the `git diff` of the PR. Identify if changes are Snowflake Migrations (`/migrations/*.sql`) or dbt models (`/models/**/*.sql`, `*.yml`).
3.  **Validation**:
    * **Snowflake**: Check for `DROP` statements without `UNDROP` or backup, naming conventions, and schema consistency.
    * **dbt**: Ensure new models have corresponding `schema.yml` entries and mandatory tests (`not_null`, `unique`).
4.  **Synthesis**: Fill the `deploy_template.md`. Summarize changes technically: "Alteração de DDL na tabela X", "Adição de lógica de negócio no modelo Y".
5.  **I/O Execution**:
    * Upload/Update the `.md` or `.docx` file in SharePoint using a unique naming convention: `Deploy_RMS-1025.md`.
    * Retrieve the Web URL from SharePoint.
    * Update the Jira Ticket description to include the link, ensuring no duplicate entries exist.

## 3. Skill-Based Architecture (Recommended)
Instead of a complex Multi-Agent framework, use the **Open Agent Skills** pattern.

### Directory Structure:
```text
.github/skills/data-deploy/
├── SKILL.md                 # Agent instructions and tool definitions
├── template_deploy.md        # The Markdown template for the deploy doc
└── scripts/
    ├── sharepoint_tool.py   # Uses MSAL & Microsoft Graph API
    └── jira_tool.py         # Uses Atlassian REST API
```

### Tool Definitions (Required for the Agent):
- `get_diff()`: Returns the output of `git diff origin/main...HEAD`.
- `analyze_snowflake(sql_code)`: Sends SQL to Snowflake Cortex `cortex.complete()` for semantic validation.
- `write_document(data)`: Merges analysis into `template_deploy.md`.
- `sync_external(file_content, jira_id)`: Orchestrates the SharePoint upload and Jira link update.

## 4. Local Development & CI Simulation
To develop this agent without a live GitHub Environment, use the following harness:

### A. Mocking the Environment (`.env`)
```bash
# Credentials for the Agent Tools
JIRA_API_TOKEN="your_token"
MS_GRAPH_CLIENT_SECRET="your_secret"
SNOWFLAKE_ACCOUNT="your_account"

# Context Mocks
MOCK_BRANCH="feature/RMS-1025-new-table"
MOCK_DIFF_PATH="./test/sample_diff.txt"
```

### B. Local Orchestrator (`agent_runner.py`)
```python
import os
import subprocess
from dotenv import load_dotenv

load_dotenv()

def simulate_ci_flow():
    # 1. Extract Jira ID from Mock Branch
    branch = os.getenv("MOCK_BRANCH")
    jira_id = branch.split('/')[-1].split('-')[0] + "-" + branch.split('/')[-1].split('-')[1]
    
    # 2. Load the Diff
    with open(os.getenv("MOCK_DIFF_PATH"), "r") as f:
        diff_content = f.read()

    # 3. Invoke LLM Skill (Simulating Copilot Enterprise API)
    # The LLM receives: diff_content, jira_id, and the content of SKILL.md
    print(f"Agent starting analysis for {jira_id}...")
    
    # Logic for calling scripts/sharepoint_tool.py and scripts/jira_tool.py goes here.
    
if __name__ == "__main__":
    simulate_ci_flow()
```

## 5. Technical Constraints
- **Idempotency**: The Agent must search for an existing file in SharePoint by name. If it exists, update it. In Jira, it must check if the SharePoint URL is already in the description before appending.
- **Robustness**: If the LLM fails to parse the diff or the Jira ID is missing, the process must exit with a non-zero status to fail the CI/CD job.
- **Security**: Never log API tokens. Use environment variables for all sensitive interactions.

## 6. Deployment in GitHub Actions
```yaml
jobs:
  agent-deploy-doc:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Data Agent
        run: |
          # The 'gh' CLI or a python script calls the GCE model
          python .github/skills/data-deploy/scripts/orchestrate.py
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          JIRA_TOKEN: ${{ secrets.JIRA_TOKEN }}
```
```

Seria útil eu detalhar a implementação do script de integração com a **Microsoft Graph API** para o SharePoint ou a lógica de **regex** para evitar a duplicação de links no Jira?