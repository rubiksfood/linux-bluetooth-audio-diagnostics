# Linux Bluetooth Audio Diagnostics

A Python CLI toolkit for inspecting and diagnosing Bluetooth audio state on Linux across BlueZ, PipeWire, WirePlumber, and related system services.

The project correlates Bluetooth connection state with PipeWire audio objects, applies deterministic diagnostic rules, and can produce structured evidence bundles for troubleshooting and bug reporting.

## Features

- Collect Linux, BlueZ, PipeWire, and WirePlumber environment information
- Inspect Bluetooth adapters and connected devices through BlueZ D-Bus
- Collect structured Bluetooth audio state from `pw-dump`
- Correlate BlueZ devices with PipeWire devices and audio nodes
- Detect common cross-layer Bluetooth audio problems
- Produce human-readable and JSON diagnostic reports
- Capture relevant system and user journal evidence
- Optionally capture a bounded `btmon` trace
- Generate structured diagnostic bundles
- Redact known host and Bluetooth identifiers from textual bundle content
- Run deterministic automated tests without requiring Bluetooth hardware

## Requirements

The toolkit is intended for Linux systems using the standard BlueZ and PipeWire Bluetooth audio stack.

Required:

- Linux
- Python 3.13+
- BlueZ
- PipeWire
- WirePlumber
- systemd / `systemctl`
- access to the system D-Bus

The following command-line tools should be available:

```text
bluetoothd
pw-dump
pipewire
wireplumber
systemctl
journalctl
```

Optional:

- `btmon`
- GNU `timeout`

`btmon` and `timeout` are required only when using the `capture --btmon` option.

## Installation

Clone the repository:

```bash
git clone https://github.com/rubiksfood/linux-bluetooth-audio-diagnostics.git
cd linux-bluetooth-audio-diagnostics
```

Create and activate a virtual environment:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
```

Install the project:

```bash
python -m pip install --upgrade pip
python -m pip install .
```

For development, install the development dependencies instead:

```bash
python -m pip install -e ".[dev]"
```

Verify the installation:

```bash
bt-audio-diag --version
bt-audio-diag --help
```

## Quick start

The CLI provides three primary workflows:

```text
inspect   Inspect the current Bluetooth and PipeWire audio state.
check     Run Bluetooth audio diagnostics.
capture   Capture diagnostic state and supporting evidence into a bundle.
```

### Inspect the current audio state

```bash
bt-audio-diag inspect
```

`inspect` displays normalised information about:

- the Linux and audio-stack environment
- relevant services
- Bluetooth adapters
- Bluetooth audio sessions
- correlated PipeWire devices
- playback and capture nodes

Example:

```text
Bluetooth Audio Inspection
==========================

System
  Distribution: Ubuntu 24.04
  Kernel: 6.x.x
  Architecture: x86_64
  Python: 3.13.x
  Tool: 0.1.0

Bluetooth adapters (1)
  - Bluetooth Adapter
    Powered: yes

Bluetooth audio sessions (1)
  - Bluetooth Headphones
    Paired: yes
    Connected: yes
    PipeWire device: 40
```

The exact values depend on the local system and connected hardware.

### Run diagnostics

```bash
bt-audio-diag check
```

The diagnostic engine evaluates the collected Bluetooth and PipeWire state and reports evidence-based findings.

Example:

```text
[INFO] BT005 - Bluetooth audio capture node is in the suspended state.
  Evidence:
    - PipeWire node reports state=suspended.
    - Node media class is Audio/Source.
  Possible cause: A suspended capture node is normally idle when no application is using the audio input.
  Recommended next step: Start audio capture and check whether the node leaves the suspended state.
```

Informational findings do not necessarily indicate a fault. For example, a Bluetooth microphone source may normally remain suspended while only playback is active.

### JSON diagnostic output

Use `--json` for machine-readable output:

```bash
bt-audio-diag check --json
```

The JSON report uses a stable structured schema containing:

- schema version
- finding counts
- diagnostic codes
- severity
- summaries
- evidence
- possible causes
- recommended next steps

## Diagnostic exit codes

`bt-audio-diag check` uses the following exit codes:

| Exit code | Meaning |
| --- | --- |
| `0` | The command completed and no WARNING or ERROR findings were produced |
| `1` | At least one WARNING or ERROR diagnostic finding was produced |
| `2` | An operational error prevented the diagnostic workflow from completing |

INFO findings do not cause exit code `1`.

These exit codes make `check` suitable for shell scripts and other automated workflows.

## Diagnostic findings

The current diagnostic rules cover:

| Code | Condition |
| --- | --- |
| `BT001` | Bluetooth adapter is not powered |
| `BT002` | Paired Bluetooth device is not connected |
| `BT003` | BlueZ reports a connected device but no corresponding PipeWire device exists |
| `BT004` | A correlated PipeWire device exposes no playback node |
| `BT005` | A relevant Bluetooth audio node is suspended or in an error state |
| `BT006` | The Bluetooth service is confirmed not to be running |
| `BT007` | The PipeWire service is confirmed not to be running |

Diagnostics are intentionally evidence-driven. Possible causes and recommended next steps are presented separately from observed state so that the tool does not claim a root cause that has not been demonstrated.

## Capture diagnostic evidence

Create a diagnostic bundle with:

```bash
bt-audio-diag capture --output diagnostic-bundle
```

The output directory must not already exist.

A bundle contains normalised state, diagnostic reports, and relevant journal evidence.

Example structure:

```text
diagnostic-bundle/
├── manifest.json
├── state/
│   ├── system.json
│   ├── bluez.json
│   ├── pipewire.json
│   └── correlation.json
├── reports/
│   ├── diagnostic.txt
│   └── diagnostic.json
└── evidence/
    └── journal/
        ├── metadata.json
        ├── bluetooth.service.log
        ├── pipewire.service.log
        └── wireplumber.service.log
```

Evidence collection is observational. The toolkit does not modify Bluetooth, PipeWire, or WirePlumber configuration.

## Redacted capture bundles

To reduce exposure of local identifiers when sharing a bundle:

```bash
bt-audio-diag capture \
    --output diagnostic-bundle-redacted \
    --redact
```

Redaction currently covers known textual identifiers including:

- the system hostname
- local Bluetooth adapter aliases treated as host identifiers
- known Bluetooth addresses
- Bluetooth-address variants using `:`, `_`, or `-` separators

Journal collection also suppresses the standard journal hostname column.

Redacted values are replaced with placeholders such as:

```text
<hostname>
<bluetooth-address-1>
```

### Redaction limitations

`--redact` reduces exposure of known identifiers, but it is **not a guarantee of complete anonymisation**.

Journal messages and other diagnostic text may contain information that the toolkit cannot reliably identify automatically, such as:

- usernames
- filesystem paths
- application names
- user-defined peripheral names
- network addresses
- arbitrary text written by other services

Review a bundle before sharing it outside a trusted environment.

## Optional btmon capture

Include a bounded Bluetooth monitor trace with:

```bash
bt-audio-diag capture \
    --output diagnostic-bundle \
    --btmon
```

The capture is automatically bounded rather than leaving `btmon` running indefinitely.

A successful raw capture adds:

```text
evidence/btmon/
├── metadata.json
└── capture.btsnoop
```

Raw `.btsnoop` files may contain sensitive Bluetooth identifiers or protocol data.

For that reason, raw btmon traces are **not included in redacted bundles**:

```bash
bt-audio-diag capture \
    --output diagnostic-bundle-redacted \
    --redact \
    --btmon
```

The bundle retains capture metadata but omits the binary trace.

## How it works

The main diagnostic workflow is:

```text
System / BlueZ / PipeWire collection
                │
                ▼
       State normalisation
                │
                ▼
     BlueZ ↔ PipeWire correlation
                │
                ▼
        Diagnostic engine
                │
        ┌───────┴────────┐
        ▼                ▼
     Reports        Capture bundle
```

### BlueZ

Bluetooth adapters and devices are collected through the BlueZ D-Bus `ObjectManager` interface and normalised into typed application models.

### PipeWire

Bluetooth audio devices and nodes are collected from structured `pw-dump` JSON rather than parsing human-oriented command output.

### Correlation

BlueZ devices are matched with PipeWire Bluetooth devices using BlueZ object paths, with Bluetooth addresses available as a fallback.

Associated playback and capture nodes are then attached to the correlated Bluetooth audio session.

### Diagnostics

Diagnostic rules operate on normalised correlated state rather than querying the operating system directly.

This separation keeps the rules deterministic and allows the diagnostic engine to be tested without Bluetooth hardware.

## Development

Create and activate a virtual environment:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
```

Install the project with development dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Install the configured pre-commit hooks:

```bash
pre-commit install
```

Run all hooks against the repository:

```bash
pre-commit run --all-files
```

## Quality checks

Run the test suite:

```bash
pytest
```

Run Ruff linting:

```bash
ruff check .
```

Check Ruff formatting:

```bash
ruff format --check .
```

Run strict static type checking:

```bash
mypy
```

The same core quality checks run in GitHub Actions on the supported Python versions.

## Testing approach

The automated test suite is designed to run without real Bluetooth hardware.

Tests use:

- deterministic fake command runners
- mocked BlueZ D-Bus state
- sanitised PipeWire JSON fixtures
- normalised in-memory models
- temporary bundle directories
- Typer CLI test runners

This allows collection, correlation, diagnostics, reporting, evidence handling, privacy behaviour, and CLI workflows to be tested reproducibly in CI.

Real Linux hardware is used for manual validation of the complete Bluetooth audio workflow.

## Project scope

Version 0.1 focuses on read-only diagnostics and evidence collection.

The toolkit does not currently:

- pair or connect Bluetooth devices
- change Bluetooth profiles
- restart services
- modify PipeWire or WirePlumber configuration
- automatically remediate detected problems
- provide live monitoring

These are intentionally outside the initial release scope.

## Licence

This project is licensed under the MIT Licence. See `LICENSE` for details.
