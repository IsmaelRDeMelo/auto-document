---
name: data-deploy-doc
description: >
  Automates deploy documentation for Snowflake and dbt Pull Requests.
  Use this skill when a pull request includes changes to SQL migration files
  or dbt models and requires a deploy document to be generated, uploaded to
  SharePoint, and linked back to the corresponding Jira ticket.
---

## When to use this skill

Activate this skill whenever a pull request:
- Has a branch name matching the pattern `feature/<JIRA-ID>-*` (for example, `feature/RMS-1025-add-kpi`)
- Contains changes to files under `migrations/` or `models/`

---

## Steps

### 1. Extract the Jira ID

Parse the branch name using the pattern `[A-Z]+-\d+` to extract the Jira Issue ID.

**Example:** `feature/RMS-1025-add-kpi` → `RMS-1025`

If no Jira ID can be found, stop and report the error clearly. Do not proceed.

---

### 2. Read and classify the diff

Read the full git diff between this branch and `main`:

```bash
git diff origin/main...HEAD
```

Classify each changed file:
- Files under `migrations/*.sql` → **Snowflake DDL Migration**
- Files under `models/**/*.sql` or `models/**/*.yml` → **dbt Model / Schema**

---

### 3. Validate

#### Snowflake validations
- Flag any `DROP` statement that is not immediately followed by an `UNDROP` or a comment justifying irreversibility.
- Flag any object names that do not follow the `SCHEMA.OBJECT_NAME` uppercase convention.

#### dbt validations
- Flag any new `.sql` model file that does not have a corresponding entry in a `schema.yml` file.
- Flag any `schema.yml` entry where key columns are missing `not_null` or `unique` tests.

---

### 4. Fill the deploy document

Use the template at `.github/skills/data-deploy/template_deploy.md` to generate the deploy document.

Replace all `{{ placeholder }}` fields with your findings from the steps above:
- `{{ jira_id }}` → the extracted Jira ID
- `{{ summary }}` → a brief technical summary of all changes
- `{{ snowflake_changes }}` → list of Snowflake migration files and their purpose
- `{{ dbt_changes }}` → list of dbt model files and their purpose
- `{{ drop_check }}`, `{{ naming_check }}`, `{{ schema_check }}`, `{{ tests_check }}` → `PASS` or `FAIL`
- `{{ risk_assessment }}` → `Low`, `Medium`, or `High` with a one-sentence justification
- `{{ rollback_plan }}` → how to safely revert these changes
- `{{ generated_at }}` → current UTC timestamp
- `{{ pr_url }}` → the URL of this pull request

Save the filled document locally as `/tmp/deploy_doc.md`.

---

### 5. Upload to SharePoint

Run the SharePoint upload script:

```bash
python .github/skills/data-deploy/scripts/sharepoint_tool.py \
  "$BRANCH_NAME" /tmp/deploy_doc.md
```

The script will:
- Authenticate using MSAL with `MS_GRAPH_TENANT_ID`, `MS_GRAPH_CLIENT_ID`, and `MS_GRAPH_CLIENT_SECRET`
- Search for an existing file named `Deploy_<JIRA_ID>.md` in the SharePoint drive
- Create or update the file (idempotent)
- Print the SharePoint web URL to stdout

Capture the printed URL — you will need it in the next step.

---

### 6. Update the Jira ticket

Run the Jira update script:

```bash
python .github/skills/data-deploy/scripts/jira_tool.py \
  "<JIRA_ID>" "<SHAREPOINT_URL>"
```

The script will:
- Authenticate using `JIRA_BASE_URL`, `JIRA_EMAIL`, and `JIRA_TOKEN`
- Fetch the current ticket description
- Append the SharePoint URL only if it is not already present (idempotent)

---

## Error handling

- If any script exits with a non-zero code, stop and surface the error output. Do not proceed to the next step.
- Never print or log the values of any environment variables.
