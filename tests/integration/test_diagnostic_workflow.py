import json
from pathlib import Path

from bt_audio_diag.diagnostics import DiagnosticContext, DiagnosticEngine
from bt_audio_diag.models import (
    AudioNode,
    BluetoothAdapter,
    BluetoothDevice,
    PipeWireDevice,
    PipeWireState,
    ServiceStatus,
    SystemInfo,
)
from bt_audio_diag.reporting import (
    render_json_report,
    render_terminal_report,
)
from bt_audio_diag.services import (
    DiagnosticBundleWriter,
    EvidenceRedactor,
    correlate_bluetooth_audio,
)


def _system_info() -> SystemInfo:
    return SystemInfo(
        distribution="Test Linux",
        distribution_version="1",
        kernel="6.0.0",
        architecture="x86_64",
        python_version="3.13.0",
        tool_version="0.1.0.dev0",
        hostname="test-host",
        services=(
            ServiceStatus(
                name="bluetooth.service",
                running=True,
            ),
            ServiceStatus(
                name="pipewire.service",
                running=True,
            ),
            ServiceStatus(
                name="wireplumber.service",
                running=True,
            ),
        ),
    )


def _adapter() -> BluetoothAdapter:
    return BluetoothAdapter(
        object_path="/org/bluez/hci0",
        address="00:11:22:33:44:55",
        alias="Test Adapter",
        powered=True,
        discoverable=False,
        pairable=True,
    )


def _bluetooth_device() -> BluetoothDevice:
    return BluetoothDevice(
        object_path="/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF",
        adapter_path="/org/bluez/hci0",
        address="AA:BB:CC:DD:EE:FF",
        name="Test Headphones",
        alias="Test Headphones",
        paired=True,
        trusted=True,
        connected=True,
        blocked=False,
    )


def _pipewire_device() -> PipeWireDevice:
    return PipeWireDevice(
        object_id=40,
        name="bluez_card.AA_BB_CC_DD_EE_FF",
        description="Test Headphones",
        bluez_address="AA:BB:CC:DD:EE:FF",
        bluez_path="/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF",
        active_profile="a2dp-sink",
    )


def _playback_node() -> AudioNode:
    return AudioNode(
        object_id=41,
        device_id=40,
        name="bluez_output.AA_BB_CC_DD_EE_FF.a2dp-sink",
        description="Test Headphones",
        media_class="Audio/Sink",
        state="running",
        profile="a2dp-sink",
        codec="sbc",
        sample_rate=48000,
        channels=2,
    )


def _healthy_pipewire_state() -> PipeWireState:
    return PipeWireState(
        devices=(_pipewire_device(),),
        nodes=(_playback_node(),),
    )


def _context(
    pipewire_state: PipeWireState,
) -> DiagnosticContext:
    sessions = correlate_bluetooth_audio(
        (_bluetooth_device(),),
        pipewire_state,
    )

    return DiagnosticContext(
        system_info=_system_info(),
        adapters=(_adapter(),),
        sessions=sessions,
    )


def test_healthy_workflow_produces_reports_and_bundle(
    tmp_path: Path,
) -> None:
    pipewire_state = _healthy_pipewire_state()
    context = _context(pipewire_state)

    findings = DiagnosticEngine().evaluate(context)

    assert findings == ()

    terminal_report = render_terminal_report(findings)
    json_report = json.loads(render_json_report(findings))

    assert "No diagnostic findings." in terminal_report
    assert json_report["summary"] == {
        "findings": 0,
        "errors": 0,
        "warnings": 0,
        "informational": 0,
    }

    output_directory = tmp_path / "healthy-bundle"

    DiagnosticBundleWriter().write(
        output_directory,
        context=context,
        pipewire_state=pipewire_state,
        findings=findings,
    )

    assert (output_directory / "reports" / "diagnostic.txt").read_text(encoding="utf-8") == (
        f"{terminal_report}\n"
    )

    bundled_json_report = json.loads(
        (output_directory / "reports" / "diagnostic.json").read_text(encoding="utf-8")
    )

    assert bundled_json_report == json_report


def test_connected_device_missing_from_pipewire_produces_bt003(
    tmp_path: Path,
) -> None:
    pipewire_state = PipeWireState()
    context = _context(pipewire_state)

    findings = DiagnosticEngine().evaluate(context)

    assert [finding.code for finding in findings] == ["BT003"]

    terminal_report = render_terminal_report(findings)

    assert "BT003" in terminal_report
    assert "no corresponding PipeWire audio device" in terminal_report

    json_report = json.loads(render_json_report(findings))

    assert json_report["findings"][0]["code"] == "BT003"
    assert json_report["findings"][0]["severity"] == "warning"

    output_directory = tmp_path / "failure-bundle"

    DiagnosticBundleWriter().write(
        output_directory,
        context=context,
        pipewire_state=pipewire_state,
        findings=findings,
    )

    correlation = json.loads(
        (output_directory / "state" / "correlation.json").read_text(encoding="utf-8")
    )

    assert len(correlation["sessions"]) == 1
    assert correlation["sessions"][0]["pipewire_device"] is None

    bundled_report = (output_directory / "reports" / "diagnostic.txt").read_text(encoding="utf-8")

    assert "BT003" in bundled_report


def test_redacted_workflow_bundle_contains_no_sensitive_identifiers(
    tmp_path: Path,
) -> None:
    pipewire_state = _healthy_pipewire_state()
    context = _context(pipewire_state)

    findings = DiagnosticEngine().evaluate(context)

    redactor = EvidenceRedactor(
        hostname="test-host",
        bluetooth_addresses=(
            "00:11:22:33:44:55",
            "AA:BB:CC:DD:EE:FF",
        ),
    )

    output_directory = tmp_path / "redacted-bundle"

    DiagnosticBundleWriter().write(
        output_directory,
        context=context,
        pipewire_state=pipewire_state,
        findings=findings,
        redactor=redactor,
    )

    text_files = (
        *output_directory.rglob("*.json"),
        *output_directory.rglob("*.txt"),
        *output_directory.rglob("*.log"),
    )

    bundle_text = "\n".join(path.read_text(encoding="utf-8") for path in text_files)

    assert "test-host" not in bundle_text
    assert "00:11:22:33:44:55" not in bundle_text
    assert "AA:BB:CC:DD:EE:FF" not in bundle_text
    assert "AA_BB_CC_DD_EE_FF" not in bundle_text

    assert "<hostname>" in bundle_text
    assert "<bluetooth-address-1>" in bundle_text
    assert "<bluetooth-address-2>" in bundle_text

    manifest = json.loads((output_directory / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["redacted"] is True
