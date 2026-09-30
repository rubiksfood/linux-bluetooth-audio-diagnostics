# Changelog

Notable changes to Linux Bluetooth Audio Diagnostics are documented in this file.

## v0.1.0 — 2026-09-30

Initial portfolio release.

### Added

- Linux system and audio-stack environment collection
- BlueZ adapter and device collection through D-Bus
- Structured PipeWire Bluetooth device and audio-node collection
- BlueZ-to-PipeWire device correlation
- Typed models for system, Bluetooth, PipeWire, diagnostic, session, and evidence state
- Rule-based Bluetooth audio diagnostics covering:
  - unpowered Bluetooth adapters
  - paired but disconnected devices
  - connected BlueZ devices missing from PipeWire
  - PipeWire devices without playback nodes
  - suspended and error-state audio nodes
  - unavailable Bluetooth and PipeWire services
- Media-class-aware guidance for suspended playback and capture nodes
- Human-readable terminal diagnostic reports
- Structured JSON diagnostic reports
- Journal evidence collection for BlueZ, PipeWire, and WirePlumber
- Optional bounded `btmon` evidence capture
- Structured diagnostic capture bundles
- Privacy-aware redaction of known host identifiers and Bluetooth addresses
- Omission of raw `.btsnoop` traces from redacted bundles
- `bt-audio-diag inspect` for inspecting correlated Bluetooth audio state
- `bt-audio-diag check` for running diagnostics
- `bt-audio-diag check --json` for machine-readable diagnostic output
- `bt-audio-diag capture` for creating diagnostic evidence bundles
- Deterministic unit and integration tests without requiring Bluetooth hardware
- GitHub Actions CI for Python 3.13 and 3.14
- Ruff, strict mypy, pytest, and pre-commit quality checks

### Known limitations

- The toolkit is read-only and does not pair, connect, reconnect, or reconfigure Bluetooth devices
- Bluetooth profile switching and automatic remediation are not implemented
- Live monitoring is not implemented
- Hardware-in-the-loop testing is not part of CI
- Redaction removes known identifiers but does not guarantee complete anonymisation of arbitrary journal or diagnostic text
- Raw `btmon` traces may contain sensitive information and should be reviewed before sharing

### Supported environment

v0.1.0 targets Linux systems using BlueZ, PipeWire, and WirePlumber with Python 3.13 or later.
