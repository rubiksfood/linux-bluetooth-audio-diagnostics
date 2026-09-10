from importlib.metadata import version as distribution_version

from typer.testing import CliRunner

from bt_audio_diag.cli import app

runner = CliRunner()


def test_help_option() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Inspect and diagnose Linux Bluetooth audio environments." in result.stdout
    assert "--version" in result.stdout


def test_version_option() -> None:
    result = runner.invoke(app, ["--version"])

    expected_version = distribution_version("linux-bluetooth-audio-diagnostics")

    assert result.exit_code == 0
    assert result.stdout == f"bt-audio-diag {expected_version}\n"
