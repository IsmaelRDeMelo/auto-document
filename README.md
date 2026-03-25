# auto-document

Autonomous Data Engineering Deploy Agent — automates deploy documentation on every Pull Request.

## How it works

1. A Pull Request is opened or updated against `main`.
2. GitHub Actions runs the agent workflow.
3. **GitHub Copilot Enterprise** reads the `git diff`, validates Snowflake / dbt changes, and fills `template_deploy.md`.
4. `sharepoint_tool.py` uploads the document to SharePoint (idempotent).
5. `jira_tool.py` appends the SharePoint URL to the Jira ticket description (idempotent).

## Project structure

```
.github/
  skills/data-deploy/
    SKILL.md               # Agent system prompt + tool definitions
    template_deploy.md     # Deploy document template
    scripts/
      sharepoint_tool.py   # Microsoft Graph API integration
      jira_tool.py         # Atlassian REST API integration
  workflows/
    agent-deploy-doc.yml   # CI trigger

tests/
  test_sharepoint_tool.py
  test_jira_tool.py
  fixtures/
    sample_diff.txt
```

## Local development

```bash
cp .env.example .env       # fill in your tokens
pip install -r requirements.txt
pytest tests/ --cov=.github/skills/data-deploy/scripts --cov-fail-under=90
```

## Secrets required (GitHub → Settings → Secrets)

| Secret | Purpose |
|--------|---------|
| `JIRA_TOKEN` | Atlassian API token |
| `MS_GRAPH_CLIENT_SECRET` | Azure AD client secret for Graph API |
| `MS_GRAPH_CLIENT_ID` | Azure AD application (client) ID |
| `MS_GRAPH_TENANT_ID` | Azure AD tenant ID |
| `SNOWFLAKE_ACCOUNT` | Snowflake account identifier |
