# Deploy Document — {{ jira_id }}

## 1. Summary
<!-- Agent fills this section: brief description of changes -->
{{ summary }}

## 2. Changes

### Snowflake Migrations
<!-- Agent lists each migration file and its purpose -->
{{ snowflake_changes }}

### dbt Models
<!-- Agent lists each model file and its purpose -->
{{ dbt_changes }}

## 3. Validation Results

| Check | Status | Detail |
|-------|--------|--------|
| No unprotected DROP statements | {{ drop_check }} | {{ drop_detail }} |
| Naming conventions | {{ naming_check }} | {{ naming_detail }} |
| schema.yml entries present | {{ schema_check }} | {{ schema_detail }} |
| not_null / unique tests present | {{ tests_check }} | {{ tests_detail }} |

## 4. Risk Assessment
<!-- Agent fills: Low / Medium / High + justification -->
{{ risk_assessment }}

## 5. Rollback Plan
<!-- Agent fills: how to revert these changes -->
{{ rollback_plan }}

## 6. Sign-off

| Role | Name | Date |
|------|------|------|
| Author | | |
| Reviewer | | |
| Approver | | |

---
*Generated automatically by the Data Deploy Agent on {{ generated_at }}*
*Source PR: {{ pr_url }}*
