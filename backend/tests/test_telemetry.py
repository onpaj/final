from unittest.mock import patch, MagicMock
import logging


def test_setup_telemetry_calls_configure_azure_monitor_in_production():
    mock_configure = MagicMock()
    with (
        patch("app.main.settings") as mock_settings,
        patch.dict("sys.modules", {"azure.monitor.opentelemetry": MagicMock(configure_azure_monitor=mock_configure)}),
    ):
        mock_settings.environment = "production"
        mock_settings.appinsights_connection_string = "InstrumentationKey=test-key"

        from app.main import setup_telemetry
        setup_telemetry()

    mock_configure.assert_called_once_with(connection_string="InstrumentationKey=test-key")


def test_setup_telemetry_does_nothing_in_development():
    mock_configure = MagicMock()
    with (
        patch("app.main.settings") as mock_settings,
        patch.dict("sys.modules", {"azure.monitor.opentelemetry": MagicMock(configure_azure_monitor=mock_configure)}),
    ):
        mock_settings.environment = "development"
        mock_settings.appinsights_connection_string = ""

        from app.main import setup_telemetry
        setup_telemetry()

    mock_configure.assert_not_called()


def test_setup_telemetry_does_nothing_when_connection_string_missing():
    mock_configure = MagicMock()
    with (
        patch("app.main.settings") as mock_settings,
        patch.dict("sys.modules", {"azure.monitor.opentelemetry": MagicMock(configure_azure_monitor=mock_configure)}),
    ):
        mock_settings.environment = "production"
        mock_settings.appinsights_connection_string = ""

        from app.main import setup_telemetry
        setup_telemetry()

    mock_configure.assert_not_called()
