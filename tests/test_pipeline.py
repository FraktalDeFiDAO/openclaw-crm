"""Unit tests for pipeline.py"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import date, datetime

from openclaw_crm.pipeline import (
    _parse_rows,
    _days_since,
    get_pipeline,
    create_deal,
    update_deal_stage,
    STAGE_PROBABILITY,
)


class TestParseRows:
    """Test _parse_rows helper function."""

    def test_empty_result(self):
        """Test parsing empty result."""
        result = MagicMock()
        result.success = False
        result.data = None
        assert _parse_rows(result) == []

    def test_no_data(self):
        """Test parsing result with no data."""
        result = MagicMock()
        result.success = True
        result.data = {}
        assert _parse_rows(result) == []

    def test_only_headers(self):
        """Test parsing result with only headers."""
        result = MagicMock()
        result.success = True
        result.data = {"values": [["Header1", "Header2"]]}
        assert _parse_rows(result) == []

    def test_single_row(self):
        """Test parsing single data row."""
        result = MagicMock()
        result.success = True
        result.data = {"values": [["Header1", "Header2"], ["Value1", "Value2"]]}
        parsed = _parse_rows(result)
        assert len(parsed) == 1
        assert parsed[0] == {"Header1": "Value1", "Header2": "Value2"}

    def test_multiple_rows(self):
        """Test parsing multiple data rows."""
        result = MagicMock()
        result.success = True
        result.data = {
            "values": [
                ["Name", "Age"],
                ["Alice", "30"],
                ["Bob", "25"],
            ]
        }
        parsed = _parse_rows(result)
        assert len(parsed) == 2
        assert parsed[0] == {"Name": "Alice", "Age": "30"}
        assert parsed[1] == {"Name": "Bob", "Age": "25"}

    def test_rows_with_missing_values(self):
        """Test parsing rows with missing values."""
        result = MagicMock()
        result.success = True
        result.data = {"values": [["A", "B", "C"], ["1", "2"]]}
        parsed = _parse_rows(result)
        assert len(parsed) == 1
        assert parsed[0] == {"A": "1", "B": "2", "C": ""}


class TestDaysSince:
    """Test _days_since helper function."""

    def test_empty_string(self):
        """Test with empty string."""
        assert _days_since("") == 999

    def test_none_value(self):
        """Test with None value."""
        assert _days_since(None) == 999

    def test_valid_date(self):
        """Test with valid date string."""
        from datetime import date, timedelta
        yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        assert _days_since(yesterday) == 1

    def test_today(self):
        """Test with today's date."""
        today = date.today().strftime("%Y-%m-%d")
        assert _days_since(today) == 0

    def test_invalid_format(self):
        """Test with invalid date format."""
        assert _days_since("invalid-date") == 999


class TestGetPipeline:
    """Test get_pipeline function."""

    @patch("openclaw_crm.pipeline.get_spreadsheet_id")
    @patch("openclaw_crm.pipeline.read_sheet")
    def test_get_pipeline_all(self, mock_read, mock_get_id):
        """Test getting all pipeline deals."""
        mock_get_id.return_value = "test-sheet-id"
        mock_read.return_value = MagicMock(
            success=True,
            data={"values": [["Header1", "Header2"], ["Value1", "Value2"]]}
        )

        pipeline = get_pipeline(active_only=False)

        mock_get_id.assert_called_once()
        mock_read.assert_called_once_with("test-sheet-id", "Pipeline!A:U")
        assert len(pipeline) == 1


class TestCreateDeal:
    """Test create_deal function."""

    @patch("openclaw_crm.pipeline.get_spreadsheet_id")
    @patch("openclaw_crm.pipeline.append_sheet")
    def test_create_deal_success(self, mock_append, mock_get_id):
        """Test creating a new deal."""
        mock_get_id.return_value = "test-sheet-id"
        mock_append.return_value = MagicMock(success=True)

        deal = {
            "Client": "Test Client",
            "Contact": "test@example.com",
            "Stage": "lead",
        }

        result = create_deal(deal)

        mock_get_id.assert_called_once()
        mock_append.assert_called_once()
        assert result["ok"] is True
        assert "row" in result


class TestUpdateDealStage:
    """Test update_deal_stage function."""

    @patch("openclaw_crm.pipeline.get_spreadsheet_id")
    @patch("openclaw_crm.pipeline.update_sheet")
    @patch("openclaw_crm.pipeline.get_pipeline")
    def test_update_stage_found(self, mock_get_pipeline, mock_update, mock_get_id):
        """Test updating deal stage when found."""
        mock_get_id.return_value = "test-sheet-id"
        mock_get_pipeline.return_value = [
            {"Client": "Test Client", "row": 5}
        ]
        mock_update.return_value = MagicMock(success=True)

        result = update_deal_stage("Test Client", "won")

        mock_get_id.assert_called_once()
        mock_update.assert_called_once()
        assert result["ok"] is True

    @patch("openclaw_crm.pipeline.get_pipeline")
    def test_update_stage_not_found(self, mock_get_pipeline):
        """Test updating deal stage when not found."""
        mock_get_pipeline.return_value = []

        result = update_deal_stage("Nonexistent Client", "won")

        assert result["ok"] is False
        assert "not found" in result["message"]


class TestStageProbability:
    """Test STAGE_PROBABILITY constants."""

    def test_all_stages_defined(self):
        """Test that all pipeline stages have probabilities."""
        expected_stages = ["lead", "qualifying", "proposal", "negotiation", "won", "lost"]
        for stage in expected_stages:
            assert stage in STAGE_PROBABILITY
            assert 0.0 <= STAGE_PROBABILITY[stage] <= 1.0

    def test_won_probability(self):
        """Test won stage has 100% probability."""
        assert STAGE_PROBABILITY["won"] == 1.0

    def test_lost_probability(self):
        """Test lost stage has 0% probability."""
        assert STAGE_PROBABILITY["lost"] == 0.0
