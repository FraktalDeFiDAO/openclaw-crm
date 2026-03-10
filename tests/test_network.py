"""Unit tests for network.py"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from openclaw_crm.network import (
    add_signal,
    get_pending_signals,
    _get_all_signals,
    _update_signal_status,
    process_signal,
    SIGNAL_HEADERS,
)


class TestAddSignal:
    """Test add_signal function."""

    @patch("openclaw_crm.network.get_spreadsheet_id")
    @patch("openclaw_crm.network.append_sheet")
    def test_add_signal_success(self, mock_append, mock_get_id):
        """Test adding a new signal."""
        mock_get_id.return_value = "test-sheet-id"
        mock_append.return_value = MagicMock(success=True)

        signal = {
            "source_client": "Test Client",
            "channel": "email",
            "signal_text": "Test signal text",
            "mentioned_company": "Test Company",
        }

        result = add_signal(signal)

        mock_get_id.assert_called_once()
        mock_append.assert_called_once()
        assert result["ok"] is True
        assert result["status"] == "new"

    @patch("openclaw_crm.network.get_spreadsheet_id")
    @patch("openclaw_crm.network.append_sheet")
    def test_add_signal_with_timestamp(self, mock_append, mock_get_id):
        """Test adding signal with custom timestamp."""
        mock_get_id.return_value = "test-sheet-id"
        mock_append.return_value = MagicMock(success=True)

        custom_timestamp = "2026-03-10T12:00:00Z"
        signal = {
            "timestamp": custom_timestamp,
            "source_client": "Test Client",
        }

        add_signal(signal)

        # Verify timestamp was used
        call_args = mock_append.call_args
        row_data = call_args[0][1][0]  # Get first row of data
        assert row_data[0] == custom_timestamp


class TestGetPendingSignals:
    """Test get_pending_signals function."""

    @patch("openclaw_crm.network.get_spreadsheet_id")
    @patch("openclaw_crm.network.read_sheet")
    def test_get_pending_signals_none(self, mock_read, mock_get_id):
        """Test when no pending signals exist."""
        mock_get_id.return_value = "test-sheet-id"
        mock_read.return_value = MagicMock(
            success=True,
            data={"values": [["Timestamp", "Status"], ["2026-03-10", "processed"]]}
        )

        signals = get_pending_signals()

        assert len(signals) == 0

    @patch("openclaw_crm.network.get_spreadsheet_id")
    @patch("openclaw_crm.network.read_sheet")
    def test_get_pending_signals_one(self, mock_read, mock_get_id):
        """Test when one pending signal exists."""
        mock_get_id.return_value = "test-sheet-id"
        mock_read.return_value = MagicMock(
            success=True,
            data={
                "values": [
                    ["Timestamp", "Status", "Source Client"],
                    ["2026-03-10", "new", "Test Client"],
                    ["2026-03-09", "processed", "Old Client"],
                ]
            }
        )

        signals = get_pending_signals()

        assert len(signals) == 1
        assert signals[0]["Source Client"] == "Test Client"
        assert signals[0]["Status"] == "new"


class TestGetAllSignals:
    """Test _get_all_signals helper function."""

    @patch("openclaw_crm.network.get_spreadsheet_id")
    @patch("openclaw_crm.network.read_sheet")
    def test_get_all_signals_empty(self, mock_read, mock_get_id):
        """Test when no signals exist."""
        mock_get_id.return_value = "test-sheet-id"
        mock_read.return_value = MagicMock(success=False, data=None)

        rows, headers = _get_all_signals()

        assert rows == []
        assert headers == SIGNAL_HEADERS

    @patch("openclaw_crm.network.get_spreadsheet_id")
    @patch("openclaw_crm.network.read_sheet")
    def test_get_all_signals_data(self, mock_read, mock_get_id):
        """Test when signals exist."""
        mock_get_id.return_value = "test-sheet-id"
        mock_read.return_value = MagicMock(
            success=True,
            data={
                "values": [
                    ["Timestamp", "Source Client"],
                    ["2026-03-10", "Client1"],
                    ["2026-03-09", "Client2"],
                ]
            }
        )

        rows, headers = _get_all_signals()

        assert len(rows) == 2
        assert headers == ["Timestamp", "Source Client"]


class TestUpdateSignalStatus:
    """Test _update_signal_status helper function."""

    @patch("openclaw_crm.network.get_spreadsheet_id")
    @patch("openclaw_crm.network.update_sheet")
    def test_update_status_success(self, mock_update, mock_get_id):
        """Test updating signal status."""
        mock_get_id.return_value = "test-sheet-id"
        mock_update.return_value = MagicMock(success=True)

        result = _update_signal_status(5, "processed")

        mock_get_id.assert_called_once()
        mock_update.assert_called_once()
        assert result is True


class TestProcessSignal:
    """Test process_signal function."""

    @patch("openclaw_crm.network._update_signal_status")
    @patch("openclaw_crm.network.create_deal")
    def test_process_signal_success(self, mock_create_deal, mock_update):
        """Test processing a signal successfully."""
        mock_create_deal.return_value = {"ok": True, "row": 10}
        mock_update.return_value = True

        signal = {
            "Source Client": "Test Client",
            "Signal Text": "Interested in services",
            "row": 5,
        }

        result = process_signal(signal)

        mock_create_deal.assert_called_once()
        mock_update.assert_called_once_with(5, "processed")
        assert result["ok"] is True

    @patch("openclaw_crm.network._update_signal_status")
    @patch("openclaw_crm.network.create_deal")
    def test_process_signal_deal_creation_fails(self, mock_create_deal, mock_update):
        """Test when deal creation fails."""
        mock_create_deal.return_value = {"ok": False, "message": "Error"}
        mock_update.return_value = True

        signal = {"Source Client": "Test Client", "row": 5}

        result = process_signal(signal)

        assert result["ok"] is False
        # Status should still be updated to processed


class TestSignalHeaders:
    """Test SIGNAL_HEADERS constants."""

    def test_all_headers_defined(self):
        """Test that all required signal headers are defined."""
        expected_headers = [
            "Timestamp", "Source Client", "Channel",
            "Signal Text", "Mentioned Company", "Status",
        ]
        for header in expected_headers:
            assert header in SIGNAL_HEADERS

    def test_status_header(self):
        """Test that Status header is defined."""
        assert "Status" in SIGNAL_HEADERS
