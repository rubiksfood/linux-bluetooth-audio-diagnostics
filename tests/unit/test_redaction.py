import pytest

from bt_audio_diag.models import (
    BtmonEvidence,
    JournalEvidence,
    JournalScope,
)
from bt_audio_diag.services import EvidenceRedactor


def test_redacts_bluetooth_address_variants() -> None:
    redactor = EvidenceRedactor(bluetooth_addresses=("AA:BB:CC:DD:EE:FF",))

    text = (
        "address=AA:BB:CC:DD:EE:FF "
        "path=/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF "
        "name=bluez_output.aa-bb-cc-dd-ee-ff"
    )

    redacted = redactor.redact_text(text)

    assert redacted == (
        "address=<bluetooth-address-1> "
        "path=/org/bluez/hci0/dev_<bluetooth-address-1> "
        "name=bluez_output.<bluetooth-address-1>"
    )


def test_address_replacements_are_deterministic() -> None:
    first = EvidenceRedactor(
        bluetooth_addresses=(
            "BB:BB:BB:BB:BB:BB",
            "AA:AA:AA:AA:AA:AA",
        )
    )
    second = EvidenceRedactor(
        bluetooth_addresses=(
            "AA:AA:AA:AA:AA:AA",
            "BB:BB:BB:BB:BB:BB",
        )
    )

    text = "AA:AA:AA:AA:AA:AA BB:BB:BB:BB:BB:BB"

    expected = "<bluetooth-address-1> <bluetooth-address-2>"

    assert first.redact_text(text) == expected
    assert second.redact_text(text) == expected


def test_redacts_hostname_and_host_aliases() -> None:
    redactor = EvidenceRedactor(
        hostname="test-host",
        host_aliases=("Private Workstation",),
    )

    text = "Host test-host advertises itself as Private Workstation."

    assert redactor.redact_text(text) == ("Host <hostname> advertises itself as <hostname>.")


def test_redacts_hostname_case_insensitively() -> None:
    redactor = EvidenceRedactor(
        hostname="test-host",
    )

    text = "test-host started. TEST-HOST.local reported an event."

    assert redactor.redact_text(text) == "<hostname> started. <hostname>.local reported an event."


def test_hostname_is_not_redacted_inside_larger_identifier() -> None:
    redactor = EvidenceRedactor(
        hostname="test-host",
    )

    assert redactor.redact_text("other-test-host-name") == "other-test-host-name"


def test_redacts_journal_evidence_without_modifying_original() -> None:
    evidence = JournalEvidence(
        service_name="bluetooth.service",
        scope=JournalScope.SYSTEM,
        command=(
            "journalctl",
            "--unit",
            "bluetooth.service",
        ),
        stdout=("test-host bluetoothd: Device AA:BB:CC:DD:EE:FF connected\n"),
        stderr="",
        returncode=0,
    )

    redactor = EvidenceRedactor(
        hostname="test-host",
        bluetooth_addresses=("AA:BB:CC:DD:EE:FF",),
    )

    redacted = redactor.redact_journal_evidence(evidence)

    assert redacted.stdout == "<hostname> bluetoothd: Device <bluetooth-address-1> connected\n"

    assert evidence.stdout == "test-host bluetoothd: Device AA:BB:CC:DD:EE:FF connected\n"


def test_redacts_btmon_metadata_without_touching_trace_file() -> None:
    evidence = BtmonEvidence(
        output_path=("/tmp/test-host/AA:BB:CC:DD:EE:FF.btsnoop"),
        command=(
            "btmon",
            "--write",
            "/tmp/test-host/AA:BB:CC:DD:EE:FF.btsnoop",
        ),
        duration_seconds=10,
        controller="hci0",
        returncode=124,
        stderr=("test-host observed AA:BB:CC:DD:EE:FF"),
    )

    redactor = EvidenceRedactor(
        hostname="test-host",
        bluetooth_addresses=("AA:BB:CC:DD:EE:FF",),
    )

    redacted = redactor.redact_btmon_evidence(evidence)

    assert redacted.output_path == "/tmp/<hostname>/<bluetooth-address-1>.btsnoop"
    assert redacted.command[-1] == "/tmp/<hostname>/<bluetooth-address-1>.btsnoop"
    assert redacted.stderr == "<hostname> observed <bluetooth-address-1>"

    assert evidence.output_path == "/tmp/test-host/AA:BB:CC:DD:EE:FF.btsnoop"


@pytest.mark.parametrize(
    "address",
    [
        "",
        "AA:BB:CC",
        "GG:BB:CC:DD:EE:FF",
        "AA-BB-CC-DD-EE-FF",
    ],
)
def test_rejects_invalid_configured_bluetooth_address(
    address: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="Invalid Bluetooth address",
    ):
        EvidenceRedactor(
            bluetooth_addresses=(address,),
        )


@pytest.mark.parametrize(
    "hostname",
    [
        "",
        "   ",
    ],
)
def test_rejects_empty_hostname(
    hostname: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="hostname must not be empty",
    ):
        EvidenceRedactor(
            hostname=hostname,
        )
