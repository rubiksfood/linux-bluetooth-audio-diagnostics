import json
from pathlib import Path

import pytest

from bt_audio_diag.diagnostics import DiagnosticContext
from bt_audio_diag.models import (
    AudioNode,
    BluetoothAdapter,
    BluetoothAudioSession,
    BluetoothDevice,
    BtmonEvidence,
    DiagnosticFinding,
    JournalEvidence,
    JournalScope,
    PipeWireDevice,
    PipeWireState,
    ServiceStatus,
    Severity,
    SystemInfo,
)
from bt_audio_diag.services import (
    DiagnosticBundleWriter,
    EvidenceRedactor,
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


def _node() -> AudioNode:
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


def _context() -> DiagnosticContext:
    session = BluetoothAudioSession(
        bluetooth_device=_bluetooth_device(),
        pipewire_device=_pipewire_device(),
        playback_nodes=(_node(),),
    )

    return DiagnosticContext(
        system_info=_system_info(),
        adapters=(_adapter(),),
        sessions=(session,),
    )


def _pipewire_state() -> PipeWireState:
    return PipeWireState(
        devices=(_pipewire_device(),),
        nodes=(_node(),),
    )


def _finding() -> DiagnosticFinding:
    return DiagnosticFinding(
        code="BT005",
        severity=Severity.INFO,
        summary=("AA:BB:CC:DD:EE:FF diagnostic finding from test-host."),
        evidence=("Device AA:BB:CC:DD:EE:FF observed.",),
    )


def _journal_evidence() -> JournalEvidence:
    return JournalEvidence(
        service_name="bluetooth.service",
        scope=JournalScope.SYSTEM,
        command=(
            "journalctl",
            "--unit",
            "bluetooth.service",
        ),
        stdout=("test-host bluetoothd: AA:BB:CC:DD:EE:FF connected\n"),
        stderr="",
        returncode=0,
    )


def test_writes_structured_bundle(
    tmp_path: Path,
) -> None:
    output_directory = tmp_path / "bundle"

    DiagnosticBundleWriter().write(
        output_directory,
        context=_context(),
        pipewire_state=_pipewire_state(),
        findings=(_finding(),),
        journal_evidence=(_journal_evidence(),),
    )

    assert (output_directory / "manifest.json").is_file()

    assert (output_directory / "state" / "system.json").is_file()
    assert (output_directory / "state" / "bluez.json").is_file()
    assert (output_directory / "state" / "pipewire.json").is_file()
    assert (output_directory / "state" / "correlation.json").is_file()

    assert (output_directory / "reports" / "diagnostic.txt").is_file()
    assert (output_directory / "reports" / "diagnostic.json").is_file()

    assert (output_directory / "evidence" / "journal" / "bluetooth.service.log").read_text(
        encoding="utf-8"
    ) == ("test-host bluetoothd: AA:BB:CC:DD:EE:FF connected\n")

    manifest = json.loads((output_directory / "manifest.json").read_text(encoding="utf-8"))

    assert manifest == {
        "btmon_trace_included": False,
        "bundle_schema_version": 1,
        "redacted": False,
    }


def test_redacted_bundle_removes_sensitive_text(
    tmp_path: Path,
) -> None:
    output_directory = tmp_path / "bundle"

    redactor = EvidenceRedactor(
        hostname="test-host",
        bluetooth_addresses=(
            "00:11:22:33:44:55",
            "AA:BB:CC:DD:EE:FF",
        ),
    )

    DiagnosticBundleWriter().write(
        output_directory,
        context=_context(),
        pipewire_state=_pipewire_state(),
        findings=(_finding(),),
        journal_evidence=(_journal_evidence(),),
        redactor=redactor,
    )

    text_files = (
        *output_directory.rglob("*.json"),
        *output_directory.rglob("*.txt"),
        *output_directory.rglob("*.log"),
    )

    bundle_text = "\n".join(path.read_text(encoding="utf-8") for path in text_files)

    assert "test-host" not in bundle_text
    assert "AA:BB:CC:DD:EE:FF" not in bundle_text
    assert "AA_BB_CC_DD_EE_FF" not in bundle_text
    assert "<hostname>" in bundle_text
    assert "<bluetooth-address-" in bundle_text


def test_raw_bundle_includes_available_btmon_trace(
    tmp_path: Path,
) -> None:
    source_trace = tmp_path / "source.btsnoop"
    source_trace.write_bytes(b"test-btsnoop-data")

    evidence = BtmonEvidence(
        output_path=str(source_trace),
        command=(
            "btmon",
            "--write",
            str(source_trace),
        ),
        duration_seconds=10,
        controller=None,
        returncode=124,
        stderr="",
    )

    output_directory = tmp_path / "bundle"

    DiagnosticBundleWriter().write(
        output_directory,
        context=_context(),
        pipewire_state=_pipewire_state(),
        findings=(),
        btmon_evidence=evidence,
    )

    copied_trace = output_directory / "evidence" / "btmon" / "capture.btsnoop"

    assert copied_trace.read_bytes() == b"test-btsnoop-data"

    manifest = json.loads((output_directory / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["btmon_trace_included"] is True


def test_redacted_bundle_omits_raw_btmon_trace(
    tmp_path: Path,
) -> None:
    source_trace = tmp_path / "source.btsnoop"
    source_trace.write_bytes(b"sensitive-btsnoop-data")

    evidence = BtmonEvidence(
        output_path=str(source_trace),
        command=(
            "btmon",
            "--write",
            str(source_trace),
        ),
        duration_seconds=10,
        controller=None,
        returncode=124,
        stderr="",
    )

    output_directory = tmp_path / "bundle"

    DiagnosticBundleWriter().write(
        output_directory,
        context=_context(),
        pipewire_state=_pipewire_state(),
        findings=(),
        btmon_evidence=evidence,
        redactor=EvidenceRedactor(
            hostname="test-host",
        ),
    )

    trace_path = output_directory / "evidence" / "btmon" / "capture.btsnoop"

    assert trace_path.exists() is False

    metadata = json.loads(
        (output_directory / "evidence" / "btmon" / "metadata.json").read_text(encoding="utf-8")
    )

    assert metadata["trace_included"] is False
    assert "sensitive identifiers" in (metadata["trace_omitted_reason"])


def test_rejects_existing_output_directory(
    tmp_path: Path,
) -> None:
    output_directory = tmp_path / "bundle"
    output_directory.mkdir()

    with pytest.raises(
        FileExistsError,
        match="Bundle output already exists",
    ):
        DiagnosticBundleWriter().write(
            output_directory,
            context=_context(),
            pipewire_state=_pipewire_state(),
            findings=(),
        )
