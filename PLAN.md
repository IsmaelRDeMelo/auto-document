# PLAN.md — Autonomous Data Engineering Deploy Agent

## Goal

Automate the Code Review → Deploy Document → SharePoint + Jira update workflow
using **GitHub Copilot Enterprise** (or Snowflake Cortex) as the reasoning engine,
triggered on every Pull Request via **GitHub Actions**.

No standalone backend. The agent lives entirely inside the repository as a **GitHub Skill**.

---

## Directory Structure

```
project-7/
├── .github/
│   ├── skills/data-deploy/
│   │   ├── SKILL.md               # Agent system prompt + tool definitions
│   │   ├── template_deploy.md     # Deploy document template (filled by agent)
│   │   └── scripts/
│   │       ├── sharepoint_tool.py # MSAL + Microsoft Graph API — upload/update file
│   │       └── jira_tool.py       # Atlassian REST API — idempotent description update
│   │
│   └── workflows/
│       └── agent-deploy-doc.yml   # Trigger: PR open/sync → run the agent
│
├── tests/
│   ├── test_sharepoint_tool.py
│   ├── test_jira_tool.py
│   └── fixtures/
│       └── sample_diff.txt        # Mock git diff for local testing
│
├── .env.example                   # Placeholder env vars — never real secrets
└── pytest.ini                     # --cov-fail-under=90
```

---

## Flow (inside GitHub Actions)

```
PR opened/updated
       │
       ▼
1. Extract Jira ID   ← parse branch name with regex (e.g. feature/RMS-1025-*)
       │
       ▼
2. Read git diff     ← git diff origin/main...HEAD
       │
       ▼
3. Classify & Validate
   ├── Snowflake migrations  → check DROP/UNDROP, naming conventions
   └── dbt models            → check schema.yml entries, not_null/unique tests
       │
       ▼
4. Copilot Agent fills template_deploy.md with findings
       │
       ▼
5. sharepoint_tool.py  → upload/update Deploy_RMS-1025.md (idempotent)
       │
       ▼
6. jira_tool.py        → append SharePoint URL to ticket description (idempotent)
```

---

## Phases & Tasks

### Phase 1 — Skill Definition
| # | Task | File |
|---|------|------|
| 1.1 | Write `SKILL.md` — system prompt, tool list, validation rules | `skills/data-deploy/SKILL.md` |
| 1.2 | Write `template_deploy.md` — sections: Summary, Changes, Risk, Rollback | `skills/data-deploy/template_deploy.md` |

### Phase 2 — Helper Scripts
| # | Task | File |
|---|------|------|
| 2.1 | `sharepoint_tool.py` — MSAL auth, search by name, upload or update, return URL | `scripts/sharepoint_tool.py` |
| 2.2 | `jira_tool.py` — GET description, regex-check for URL, idempotent PATCH | `scripts/jira_tool.py` |

### Phase 3 — GitHub Actions Workflow
| # | Task | File |
|---|------|------|
| 3.1 | `agent-deploy-doc.yml` — checkout, parse branch, run `gh copilot` or call Cortex API, invoke scripts | `workflows/agent-deploy-doc.yml` |
| 3.2 | Inject secrets: `JIRA_TOKEN`, `MS_GRAPH_CLIENT_SECRET`, `SNOWFLAKE_ACCOUNT` | GitHub Repo Secrets |

### Phase 4 — Tests (TDD, ≥ 90% coverage)
| # | Task | File |
|---|------|------|
| 4.1 | `test_sharepoint_tool.py` — mock MSAL + Graph API calls | `tests/` |
| 4.2 | `test_jira_tool.py` — mock Atlassian REST, test idempotency logic | `tests/` |
| 4.3 | `pytest.ini` with coverage gate | root |

---

## Key Rules

| Concern | Rule |
|---------|------|
| **Idempotency — SharePoint** | Search file by `Deploy_{JIRA_ID}.md` before writing; update if found |
| **Idempotency — Jira** | Regex-search description for the SharePoint URL; skip append if already present |
| **Security** | All secrets via env vars; never logged; `.env.example` committed, `.env` gitignored |
| **Robustness** | Missing Jira ID or LLM failure → `sys.exit(1)` to fail the CI job |
| **Coverage** | `pytest --cov=.github/skills/data-deploy/scripts --cov-fail-under=90` |

---

## GitHub Actions Workflow (Summary)

```yaml
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  agent-deploy-doc:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install msal requests python-dotenv pytest pytest-cov pytest-mock
      - run: pytest tests/ --cov=.github/skills/data-deploy/scripts --cov-fail-under=90
      - name: Run Deploy Agent
        run: python .github/skills/data-deploy/scripts/orchestrate.py
        env:
          JIRA_TOKEN:             ${{ secrets.JIRA_TOKEN }}
          MS_GRAPH_CLIENT_SECRET: ${{ secrets.MS_GRAPH_CLIENT_SECRET }}
          SNOWFLAKE_ACCOUNT:      ${{ secrets.SNOWFLAKE_ACCOUNT }}
          GITHUB_TOKEN:           ${{ secrets.GITHUB_TOKEN }}
```

---

## Local Development

```bash
# 1. Copy and fill in mocks
cp .env.example .env
# Set MOCK_BRANCH, MOCK_DIFF_PATH, and API tokens

# 2. Run tests
pytest tests/ --cov=.github/skills/data-deploy/scripts --cov-fail-under=90

# 3. Simulate the full flow locally
python .github/skills/data-deploy/scripts/orchestrate.py
```
