"""Tests for AdfStateManager."""

from unittest.mock import MagicMock

import pytest

from sia_scraper.core.adf_state_manager import AdfState, AdfStateManager
from sia_scraper.core.exceptions import SiaSessionException


class TestAdfStateManagerInit:
    """Tests for AdfStateManager initialization."""

    def test_init_creates_empty_state(self):
        manager = AdfStateManager()
        assert manager.view_state is None
        assert manager.window_id is None
        assert manager.page_id is None
        assert not manager.has_state

    def test_params_empty_when_not_initialized(self):
        manager = AdfStateManager()
        assert manager.params == {}


class TestAdfStateManagerState:
    """Tests for AdfStateManager state handling."""

    def test_has_state_false_when_partial(self):
        manager = AdfStateManager()
        manager._view_state = "test"
        assert not manager.has_state

    def test_has_state_true_when_complete(self):
        manager = AdfStateManager()
        manager._view_state = "test"
        manager._window_id = "window123"
        manager._page_id = "0"
        assert manager.has_state


class TestAdfStateManagerInitialize:
    """Tests for AdfStateManager.initialize_from_html."""

    def test_initialize_from_html_valid(self):
        html = b"""
        <html>
        <input type="hidden" name="javax.faces.ViewState" value="viewstate123" />
        <input type="hidden" name="Adf-Window-Id" value="window456" />
        </html>
        """
        manager = AdfStateManager()
        manager.initialize_from_html(html)

        assert manager.view_state == "viewstate123"
        assert manager.window_id == "window456"
        assert manager.page_id == "0"
        assert manager.has_state

    def test_initialize_from_html_missing_viewstate_raises(self):
        html = b'<html><input type="hidden" name="Adf-Window-Id" value="window456" /></html>'
        manager = AdfStateManager()

        with pytest.raises(SiaSessionException.SessionNotSet):
            manager.initialize_from_html(html)

    def test_initialize_from_html_missing_window_id_raises(self):
        html = b'<html><input type="hidden" name="javax.faces.ViewState" value="viewstate123" /></html>'
        manager = AdfStateManager()

        with pytest.raises(SiaSessionException.SessionNotSet):
            manager.initialize_from_html(html)


class TestAdfStateManagerSync:
    """Tests for ViewState synchronization."""

    def test_sync_from_response_updates_viewstate(self):
        mock_response = MagicMock()
        mock_response.text = '<input type="hidden" name="javax.faces.ViewState" value="newvs">'
        mock_response.content = None  # Force text attribute to be used

        manager = AdfStateManager()
        manager._view_state = "oldvs"
        manager._window_id = "win"
        manager._page_id = "0"

        manager.sync_from_response(mock_response)

        assert manager.view_state == "newvs"

    def test_sync_from_response_preserves_on_missing(self):
        mock_response = MagicMock()
        mock_response.text = "<html>no viewstate here</html>"

        manager = AdfStateManager()
        manager._view_state = "oldvs"
        manager._window_id = "win"
        manager._page_id = "0"

        manager.sync_from_response(mock_response)

        assert manager.view_state == "oldvs"

    def test_sync_from_html_updates_viewstate(self):
        html = b'<input type="hidden" name="javax.faces.ViewState" value="htmlvs">'
        manager = AdfStateManager()
        manager._view_state = "oldvs"
        manager._window_id = "win"
        manager._page_id = "0"

        manager.sync_from_html(html)

        assert manager.view_state == "htmlvs"


class TestAdfStateManagerSnapshot:
    """Tests for get_state_snapshot."""

    def test_snapshot_returns_adf_state(self):
        manager = AdfStateManager()
        manager._view_state = "vs"
        manager._window_id = "wid"
        manager._page_id = "0"

        snapshot = manager.get_state_snapshot()

        assert isinstance(snapshot, AdfState)
        assert snapshot.view_state == "vs"
        assert snapshot.window_id == "wid"
        assert snapshot.page_id == "0"

    def test_snapshot_raises_when_not_initialized(self):
        manager = AdfStateManager()

        with pytest.raises(SiaSessionException.SessionNotSet):
            manager.get_state_snapshot()


class TestAdfStateManagerRestore:
    """Tests for restore_from_session_data."""

    def test_restore_from_dict(self):
        session_data = {
            "javax_faces_ViewState": "restored_vs",
            "params": {"Adf-Window-Id": "restored_wid", "Adf-Page-Id": "1"},
        }
        manager = AdfStateManager()
        manager.restore_from_session_data(session_data)

        assert manager.view_state == "restored_vs"
        assert manager.window_id == "restored_wid"
        assert manager.page_id == "1"


class TestAdfStateManagerBuildRequestDict:
    """Tests for build_request_dict."""

    def test_build_request_dict_returns_dict(self):
        manager = AdfStateManager()
        manager._view_state = "vs123"
        manager._window_id = "wid456"
        manager._page_id = "0"

        result = manager.build_request_dict()

        assert result["javax.faces.ViewState"] == "vs123"
        assert result["Adf-Window-Id"] == "wid456"
        assert result["Adf-Page-Id"] == "0"
        assert result["org.apache.myfaces.trinidad.faces.FORM"] == "f1"

    def test_build_request_dict_raises_when_not_initialized(self):
        manager = AdfStateManager()

        with pytest.raises(SiaSessionException.SessionNotSet):
            manager.build_request_dict()


class TestAdfState:
    """Tests for AdfState dataclass."""

    def test_adf_state_is_frozen(self):
        state = AdfState(view_state="vs", window_id="wid", page_id="0")
        with pytest.raises(AttributeError):  # noqa: B017
            state.view_state = "new"  # type: ignore[assignment]

    def test_adf_state_allows_none_values(self):
        state = AdfState(view_state=None, window_id=None, page_id=None)
        assert state.view_state is None
