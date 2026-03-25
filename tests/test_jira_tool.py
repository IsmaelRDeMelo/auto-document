"""Unit tests for jira_tool.py (TDD)."""
import pytest
from unittest.mock import MagicMock, patch
import importlib.util
import pathlib

SCRIPT_PATH = (
    pathlib.Path(__file__).parent.parent
    / ".github" / "skills" / "data-deploy" / "scripts" / "jira_tool.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("jira_tool", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# get_issue_description
# ---------------------------------------------------------------------------
class TestGetIssueDescription:
    def test_returns_description(self):
        mod = _load()
        session = MagicMock()
        session.get.return_value.status_code = 200
        session.get.return_value.json.return_value = {
            "fields": {"description": "Existing ticket description."}
        }
        desc = mod.get_issue_description(session, "https://jira.example.com", "RMS-1025")
        assert desc == "Existing ticket description."

    def test_returns_empty_string_when_no_description(self):
        mod = _load()
        session = MagicMock()
        session.get.return_value.status_code = 200
        session.get.return_value.json.return_value = {"fields": {"description": None}}
        desc = mod.get_issue_description(session, "https://jira.example.com", "RMS-1025")
        assert desc == ""

    def test_raises_on_http_error(self):
        mod = _load()
        session = MagicMock()
        session.get.return_value.status_code = 404
        session.get.return_value.text = "Not Found"
        with pytest.raises(RuntimeError, match="Failed to get Jira issue"):
            mod.get_issue_description(session, "https://jira.example.com", "RMS-9999")


# ---------------------------------------------------------------------------
# url_already_in_description
# ---------------------------------------------------------------------------
class TestUrlAlreadyInDescription:
    def test_returns_true_when_url_present(self):
        mod = _load()
        desc = "See doc: https://sharepoint.com/files/Deploy_RMS-1025.md"
        assert mod.url_already_in_description(desc, "https://sharepoint.com/files/Deploy_RMS-1025.md") is True

    def test_returns_false_when_url_absent(self):
        mod = _load()
        assert mod.url_already_in_description("Some other content.", "https://sharepoint.com/doc.md") is False

    def test_returns_false_for_empty_description(self):
        mod = _load()
        assert mod.url_already_in_description("", "https://example.com/doc.md") is False


# ---------------------------------------------------------------------------
# update_issue_description
# ---------------------------------------------------------------------------
class TestUpdateIssueDescription:
    def test_appends_url_when_not_present(self):
        mod = _load()
        session = MagicMock()
        session.get.return_value.status_code = 200
        session.get.return_value.json.return_value = {
            "fields": {"description": "Original description."}
        }
        session.put.return_value.status_code = 204

        updated = mod.update_issue_description(
            session, "https://jira.example.com", "RMS-1025",
            "https://sharepoint.com/Deploy_RMS-1025.md",
        )
        assert updated is True
        session.put.assert_called_once()

    def test_skips_update_when_url_already_present(self):
        mod = _load()
        existing_url = "https://sharepoint.com/Deploy_RMS-1025.md"
        session = MagicMock()
        session.get.return_value.status_code = 200
        session.get.return_value.json.return_value = {
            "fields": {"description": f"Original. {existing_url}"}
        }

        updated = mod.update_issue_description(
            session, "https://jira.example.com", "RMS-1025", existing_url
        )
        assert updated is False
        session.put.assert_not_called()

    def test_raises_on_put_failure(self):
        mod = _load()
        session = MagicMock()
        session.get.return_value.status_code = 200
        session.get.return_value.json.return_value = {"fields": {"description": "No URL yet."}}
        session.put.return_value.status_code = 500
        session.put.return_value.text = "Internal error"

        with pytest.raises(RuntimeError, match="Failed to update Jira issue"):
            mod.update_issue_description(
                session, "https://jira.example.com", "RMS-1025",
                "https://sharepoint.com/Deploy_RMS-1025.md",
            )


# ---------------------------------------------------------------------------
# run() — full flow entry point
# ---------------------------------------------------------------------------
class TestRun:
    def test_run_calls_update(self, monkeypatch):
        mod = _load()
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_EMAIL", "agent@example.com")
        monkeypatch.setenv("JIRA_TOKEN", "token123")

        with patch.object(mod, "update_issue_description", return_value=True) as mock_update, \
             patch("requests.Session") as mock_session_cls:
            mock_session_cls.return_value = MagicMock()
            mod.run("RMS-1025", "https://sharepoint.com/Deploy_RMS-1025.md")

        mock_update.assert_called_once()
