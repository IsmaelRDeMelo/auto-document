"""Unit tests for sharepoint_tool.py (TDD)."""
import pytest
from unittest.mock import MagicMock, patch
import importlib.util
import pathlib

SCRIPT_PATH = (
    pathlib.Path(__file__).parent.parent
    / ".github" / "skills" / "data-deploy" / "scripts" / "sharepoint_tool.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("sharepoint_tool", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# extract_jira_id
# ---------------------------------------------------------------------------
class TestExtractJiraId:
    def test_standard_branch(self):
        assert _load().extract_jira_id("feature/RMS-1025-add-kpi") == "RMS-1025"

    def test_branch_with_multiple_segments(self):
        assert _load().extract_jira_id("feature/RMS-9999-some-long-description") == "RMS-9999"

    def test_no_jira_id_raises(self):
        with pytest.raises(ValueError, match="Could not extract Jira ID"):
            _load().extract_jira_id("feature/no-jira-here")

    def test_empty_branch_raises(self):
        with pytest.raises(ValueError):
            _load().extract_jira_id("")


# ---------------------------------------------------------------------------
# get_access_token
# ---------------------------------------------------------------------------
class TestGetAccessToken:
    def test_returns_token_on_success(self):
        mod = _load()
        mock_app = MagicMock()
        mock_app.acquire_token_for_client.return_value = {"access_token": "tok123"}
        with patch("msal.ConfidentialClientApplication", return_value=mock_app):
            token = mod.get_access_token("tenant", "client_id", "secret")
        assert token == "tok123"

    def test_raises_on_missing_token(self):
        mod = _load()
        mock_app = MagicMock()
        mock_app.acquire_token_for_client.return_value = {"error": "auth_failed"}
        with patch("msal.ConfidentialClientApplication", return_value=mock_app):
            with pytest.raises(RuntimeError, match="Failed to acquire token"):
                mod.get_access_token("tenant", "client_id", "secret")


# ---------------------------------------------------------------------------
# find_existing_file
# ---------------------------------------------------------------------------
class TestFindExistingFile:
    def test_returns_item_id_when_found(self):
        mod = _load()
        mock_session = MagicMock()
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = {
            "value": [{"id": "file-id-abc", "name": "Deploy_RMS-1025.md"}]
        }
        result = mod.find_existing_file(mock_session, "site_id", "drive_id", "Deploy_RMS-1025.md")
        assert result == "file-id-abc"

    def test_returns_none_when_not_found(self):
        mod = _load()
        mock_session = MagicMock()
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = {"value": []}
        result = mod.find_existing_file(mock_session, "site_id", "drive_id", "Deploy_RMS-9999.md")
        assert result is None

    def test_returns_none_on_http_error(self):
        mod = _load()
        mock_session = MagicMock()
        mock_session.get.return_value.status_code = 500
        result = mod.find_existing_file(mock_session, "site_id", "drive_id", "Deploy_RMS-1000.md")
        assert result is None


# ---------------------------------------------------------------------------
# upload_or_update_file
# ---------------------------------------------------------------------------
class TestUploadOrUpdateFile:
    def test_creates_new_file_when_not_exists(self):
        mod = _load()
        mock_session = MagicMock()
        mock_session.put.return_value.status_code = 201
        mock_session.put.return_value.json.return_value = {
            "webUrl": "https://sharepoint.com/files/Deploy_RMS-1025.md"
        }
        with patch.object(mod, "find_existing_file", return_value=None):
            url = mod.upload_or_update_file(
                mock_session, "site_id", "drive_id", "Deploy_RMS-1025.md", "# doc"
            )
        assert url == "https://sharepoint.com/files/Deploy_RMS-1025.md"

    def test_updates_file_when_exists(self):
        mod = _load()
        mock_session = MagicMock()
        mock_session.put.return_value.status_code = 200
        mock_session.put.return_value.json.return_value = {
            "webUrl": "https://sharepoint.com/files/Deploy_RMS-1025.md"
        }
        with patch.object(mod, "find_existing_file", return_value="existing-item-id"):
            url = mod.upload_or_update_file(
                mock_session, "site_id", "drive_id", "Deploy_RMS-1025.md", "# doc"
            )
        assert url == "https://sharepoint.com/files/Deploy_RMS-1025.md"

    def test_raises_on_http_error(self):
        mod = _load()
        mock_session = MagicMock()
        mock_session.put.return_value.status_code = 403
        mock_session.put.return_value.text = "Forbidden"
        with patch.object(mod, "find_existing_file", return_value=None):
            with pytest.raises(RuntimeError, match="Upload failed"):
                mod.upload_or_update_file(
                    mock_session, "site_id", "drive_id", "Deploy_RMS-1025.md", "# doc"
                )


# ---------------------------------------------------------------------------
# run() — full flow entry point
# ---------------------------------------------------------------------------
class TestRun:
    def test_run_returns_sharepoint_url(self, monkeypatch):
        mod = _load()
        monkeypatch.setenv("MS_GRAPH_TENANT_ID", "tid")
        monkeypatch.setenv("MS_GRAPH_CLIENT_ID", "cid")
        monkeypatch.setenv("MS_GRAPH_CLIENT_SECRET", "secret")
        monkeypatch.setenv("SHAREPOINT_SITE_ID", "site")
        monkeypatch.setenv("SHAREPOINT_DRIVE_ID", "drive")

        with patch.object(mod, "get_access_token", return_value="tok"), \
             patch.object(mod, "upload_or_update_file",
                          return_value="https://sharepoint.com/Deploy_RMS-1025.md"), \
             patch("requests.Session") as mock_session_cls:
            mock_session_cls.return_value = MagicMock()
            url = mod.run("feature/RMS-1025-test", "# content")

        assert url == "https://sharepoint.com/Deploy_RMS-1025.md"

    def test_run_raises_on_invalid_branch(self, monkeypatch):
        mod = _load()
        with pytest.raises(ValueError, match="Could not extract Jira ID"):
            mod.run("feature/no-ticket", "# content")
