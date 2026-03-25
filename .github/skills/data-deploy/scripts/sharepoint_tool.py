"""
sharepoint_tool.py — Microsoft Graph API adapter for the Deploy Agent.

Responsibilities:
  - extract_jira_id(branch_name) -> str
  - get_access_token(tenant_id, client_id, client_secret) -> str
  - find_existing_file(session, site_id, drive_id, filename) -> str | None
  - upload_or_update_file(session, site_id, drive_id, filename, content) -> str (webUrl)
"""

import os
import re
import sys
import msal
import requests


# ---------------------------------------------------------------------------
# Jira ID extraction (shared utility used by both tools)
# ---------------------------------------------------------------------------

_JIRA_ID_PATTERN = re.compile(r"([A-Z]+-\d+)", re.IGNORECASE)


def extract_jira_id(branch_name: str) -> str:
    """Extract the Jira Issue ID from a branch name.

    Args:
        branch_name: e.g. 'feature/RMS-1025-add-kpi'

    Returns:
        The Jira ID string, e.g. 'RMS-1025'.

    Raises:
        ValueError: if no Jira ID pattern is found.
    """
    match = _JIRA_ID_PATTERN.search(branch_name)
    if not match:
        raise ValueError(
            f"Could not extract Jira ID from branch name: '{branch_name}'. "
            "Expected pattern like 'PROJECT-1234'."
        )
    return match.group(1).upper()


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

_GRAPH_SCOPES = ["https://graph.microsoft.com/.default"]


def get_access_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    """Obtain an OAuth2 access token from Azure AD using MSAL.

    Raises:
        RuntimeError: if authentication fails.
    """
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=client_secret,
    )
    result = app.acquire_token_for_client(scopes=_GRAPH_SCOPES)
    if "access_token" not in result:
        raise RuntimeError(
            f"Failed to acquire token: {result.get('error')} — {result.get('error_description', '')}"
        )
    return result["access_token"]


# ---------------------------------------------------------------------------
# SharePoint file operations
# ---------------------------------------------------------------------------

def find_existing_file(
    session: requests.Session, site_id: str, drive_id: str, filename: str
) -> str | None:
    """Search for an existing file in the SharePoint drive by name.

    Returns:
        The item ID string if found, or None otherwise.
    """
    url = (
        f"https://graph.microsoft.com/v1.0/sites/{site_id}"
        f"/drives/{drive_id}/root/children"
    )
    resp = session.get(url)
    if resp.status_code != 200:
        return None
    items = resp.json().get("value", [])
    for item in items:
        if item.get("name") == filename:
            return item["id"]
    return None


def upload_or_update_file(
    session: requests.Session,
    site_id: str,
    drive_id: str,
    filename: str,
    content: str,
) -> str:
    """Upload a new file or update an existing one in SharePoint.

    Args:
        session: An authenticated requests.Session.
        site_id: SharePoint site ID.
        drive_id: SharePoint drive ID.
        filename: Target filename (e.g. 'Deploy_RMS-1025.md').
        content: The text content of the file.

    Returns:
        The web URL of the uploaded/updated file.

    Raises:
        RuntimeError: on HTTP error.
    """
    existing_id = find_existing_file(session, site_id, drive_id, filename)

    if existing_id:
        url = (
            f"https://graph.microsoft.com/v1.0/sites/{site_id}"
            f"/drives/{drive_id}/items/{existing_id}/content"
        )
    else:
        url = (
            f"https://graph.microsoft.com/v1.0/sites/{site_id}"
            f"/drives/{drive_id}/root:/{filename}:/content"
        )

    resp = session.put(url, data=content.encode("utf-8"), headers={"Content-Type": "text/plain"})
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Upload failed with status {resp.status_code}: {resp.text}")

    return resp.json()["webUrl"]


# ---------------------------------------------------------------------------
# Entry point (called by orchestrate.py or GitHub Actions step)
# ---------------------------------------------------------------------------

def run(branch_name: str, document_content: str) -> str:
    """Full SharePoint flow: auth → find/create → upload → return URL.

    Returns:
        SharePoint web URL of the deploy document.
    """
    jira_id = extract_jira_id(branch_name)
    filename = f"Deploy_{jira_id}.md"

    token = get_access_token(
        tenant_id=os.environ["MS_GRAPH_TENANT_ID"],
        client_id=os.environ["MS_GRAPH_CLIENT_ID"],
        client_secret=os.environ["MS_GRAPH_CLIENT_SECRET"],
    )

    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {token}"

    url = upload_or_update_file(
        session,
        site_id=os.environ["SHAREPOINT_SITE_ID"],
        drive_id=os.environ["SHAREPOINT_DRIVE_ID"],
        filename=filename,
        content=document_content,
    )
    print(f"[sharepoint_tool] Uploaded '{filename}' → {url}")
    return url


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: sharepoint_tool.py <branch_name> <document_content_file>")
        sys.exit(1)
    branch = sys.argv[1]
    with open(sys.argv[2], encoding="utf-8") as f:
        doc = f.read()
    print(run(branch, doc))
