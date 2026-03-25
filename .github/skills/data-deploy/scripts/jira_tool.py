"""
jira_tool.py — Atlassian REST API adapter for the Deploy Agent.

Responsibilities:
  - get_issue_description(session, base_url, jira_id) -> str
  - url_already_in_description(description, url) -> bool
  - update_issue_description(session, base_url, jira_id, sharepoint_url) -> bool
"""

import os
import sys
import requests


# ---------------------------------------------------------------------------
# Jira REST API helpers
# ---------------------------------------------------------------------------

def get_issue_description(
    session: requests.Session, base_url: str, jira_id: str
) -> str:
    """Retrieve the current description of a Jira issue.

    Args:
        session: An authenticated requests.Session (Basic auth pre-set).
        base_url: e.g. 'https://your-org.atlassian.net'
        jira_id: e.g. 'RMS-1025'

    Returns:
        The description string, or empty string if not set.

    Raises:
        RuntimeError: on HTTP error.
    """
    url = f"{base_url.rstrip('/')}/rest/api/2/issue/{jira_id}"
    resp = session.get(url, params={"fields": "description"})
    if resp.status_code != 200:
        raise RuntimeError(
            f"Failed to get Jira issue {jira_id}: HTTP {resp.status_code} — {resp.text}"
        )
    return resp.json()["fields"].get("description") or ""


def url_already_in_description(description: str, url: str) -> bool:
    """Return True if the SharePoint URL is already present in the description."""
    return url in description


def update_issue_description(
    session: requests.Session,
    base_url: str,
    jira_id: str,
    sharepoint_url: str,
) -> bool:
    """Idempotently append the SharePoint URL to the Jira issue description.

    Returns:
        True if the description was updated, False if the URL was already present.

    Raises:
        RuntimeError: on HTTP PUT failure.
    """
    current_description = get_issue_description(session, base_url, jira_id)

    if url_already_in_description(current_description, sharepoint_url):
        print(f"[jira_tool] URL already present in {jira_id} — skipping update.")
        return False

    separator = "\n\n" if current_description else ""
    new_description = (
        f"{current_description}{separator}"
        f"*Deploy Document:* {sharepoint_url}"
    )

    put_url = f"{base_url.rstrip('/')}/rest/api/2/issue/{jira_id}"
    resp = session.put(
        put_url,
        json={"fields": {"description": new_description}},
        headers={"Content-Type": "application/json"},
    )
    if resp.status_code not in (200, 204):
        raise RuntimeError(
            f"Failed to update Jira issue {jira_id}: HTTP {resp.status_code} — {resp.text}"
        )

    print(f"[jira_tool] Updated {jira_id} with SharePoint URL.")
    return True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(jira_id: str, sharepoint_url: str) -> None:
    """Full Jira flow: auth → get description → idempotent update."""
    base_url = os.environ["JIRA_BASE_URL"]
    email = os.environ["JIRA_EMAIL"]
    token = os.environ["JIRA_TOKEN"]

    session = requests.Session()
    session.auth = (email, token)

    update_issue_description(session, base_url, jira_id, sharepoint_url)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: jira_tool.py <jira_id> <sharepoint_url>")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2])
