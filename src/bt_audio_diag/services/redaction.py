import re
from collections.abc import Iterable
from dataclasses import replace

from bt_audio_diag.models import BtmonEvidence, JournalEvidence

_HOSTNAME_REPLACEMENT = "<hostname>"


class EvidenceRedactor:
    """Redact sensitive identifiers from captured diagnostic evidence."""

    def __init__(
        self,
        *,
        hostname: str | None = None,
        host_aliases: Iterable[str] = (),
        bluetooth_addresses: Iterable[str] = (),
    ) -> None:
        if hostname is not None and not hostname.strip():
            raise ValueError("hostname must not be empty")

        normalized_host_aliases = {alias.strip() for alias in host_aliases if alias.strip()}

        host_identifiers = normalized_host_aliases

        if hostname is not None:
            host_identifiers.add(hostname.strip())

        self._host_patterns = tuple(
            _hostname_pattern(identifier)
            for identifier in sorted(
                host_identifiers,
                key=lambda value: (-len(value), value.casefold()),
            )
        )

        normalized_addresses = sorted(
            {_normalize_bluetooth_address(address) for address in bluetooth_addresses}
        )

        self._address_patterns = tuple(
            (
                _bluetooth_address_pattern(address),
                f"<bluetooth-address-{index}>",
            )
            for index, address in enumerate(
                normalized_addresses,
                start=1,
            )
        )

    def redact_text(
        self,
        text: str,
    ) -> str:
        """Return text with configured sensitive identifiers redacted."""

        redacted = text

        for pattern, replacement in self._address_patterns:
            redacted = pattern.sub(
                replacement,
                redacted,
            )

        for pattern in self._host_patterns:
            redacted = pattern.sub(
                _HOSTNAME_REPLACEMENT,
                redacted,
            )

        return redacted

    def redact_journal_evidence(
        self,
        evidence: JournalEvidence,
    ) -> JournalEvidence:
        """Return a sanitized copy of journal evidence."""

        return replace(
            evidence,
            command=tuple(self.redact_text(argument) for argument in evidence.command),
            stdout=self.redact_text(evidence.stdout),
            stderr=self.redact_text(evidence.stderr),
            error=_redact_optional(
                evidence.error,
                self,
            ),
        )

    def redact_btmon_evidence(
        self,
        evidence: BtmonEvidence,
    ) -> BtmonEvidence:
        """Return sanitized btmon metadata.

        This does not modify the binary btsnoop trace itself.
        """

        return replace(
            evidence,
            output_path=self.redact_text(evidence.output_path),
            command=tuple(self.redact_text(argument) for argument in evidence.command),
            controller=_redact_optional(
                evidence.controller,
                self,
            ),
            stderr=self.redact_text(evidence.stderr),
            error=_redact_optional(
                evidence.error,
                self,
            ),
        )


def _normalize_bluetooth_address(
    address: str,
) -> str:
    normalized = address.strip()

    if (
        re.fullmatch(
            r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}",
            normalized,
        )
        is None
    ):
        raise ValueError(f"Invalid Bluetooth address: {address!r}")

    return normalized.upper()


def _bluetooth_address_pattern(
    address: str,
) -> re.Pattern[str]:
    octets = address.split(":")
    body = r"[:_-]".join(re.escape(octet) for octet in octets)

    return re.compile(
        rf"(?<![0-9A-Fa-f]){body}(?![0-9A-Fa-f])",
        re.IGNORECASE,
    )


def _hostname_pattern(
    hostname: str,
) -> re.Pattern[str]:
    return re.compile(
        rf"(?<![A-Za-z0-9-])"
        rf"{re.escape(hostname)}"
        rf"(?![A-Za-z0-9-])",
        re.IGNORECASE,
    )


def _redact_optional(
    value: str | None,
    redactor: EvidenceRedactor,
) -> str | None:
    if value is None:
        return None

    return redactor.redact_text(value)
