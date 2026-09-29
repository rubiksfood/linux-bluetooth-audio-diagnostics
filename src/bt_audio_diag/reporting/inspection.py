from bt_audio_diag.diagnostics import DiagnosticContext
from bt_audio_diag.models import PipeWireState

_TITLE = "Bluetooth Audio Inspection"
_TITLE_UNDERLINE = "=" * len(_TITLE)


def render_inspection_report(
    context: DiagnosticContext,
    pipewire_state: PipeWireState,
) -> str:
    """Render normalized Bluetooth audio state as deterministic text."""

    system_info = context.system_info

    distribution = system_info.distribution
    if system_info.distribution_version is not None:
        distribution = f"{distribution} {system_info.distribution_version}"

    lines = [
        _TITLE,
        _TITLE_UNDERLINE,
        "",
        "System",
        f"  Distribution: {distribution}",
        f"  Kernel: {system_info.kernel}",
        f"  Architecture: {system_info.architecture}",
        f"  Python: {system_info.python_version}",
        f"  Tool: {system_info.tool_version}",
        f"  BlueZ: {_display_optional(system_info.bluez_version)}",
        f"  PipeWire: {_display_optional(system_info.pipewire_version)}",
        f"  WirePlumber: {_display_optional(system_info.wireplumber_version)}",
        "",
        "Services",
    ]

    if system_info.services:
        for service in system_info.services:
            lines.append(f"  {service.name}: {_service_state(service.running)}")
    else:
        lines.append("  None")

    lines.extend(
        [
            "",
            f"Bluetooth adapters ({len(context.adapters)})",
        ]
    )

    if context.adapters:
        for adapter in context.adapters:
            name = adapter.alias or adapter.address
            lines.extend(
                [
                    f"  - {name}",
                    f"    Address: {adapter.address}",
                    f"    Powered: {_yes_no(adapter.powered)}",
                    f"    Discoverable: {_yes_no(adapter.discoverable)}",
                    f"    Pairable: {_yes_no(adapter.pairable)}",
                ]
            )
    else:
        lines.append("  None")

    lines.extend(
        [
            "",
            f"Bluetooth audio sessions ({len(context.sessions)})",
        ]
    )

    if context.sessions:
        for session in context.sessions:
            bluetooth_device = session.bluetooth_device
            name = bluetooth_device.alias or bluetooth_device.name or bluetooth_device.address

            pipewire_device_id = (
                str(session.pipewire_device.object_id)
                if session.pipewire_device is not None
                else "none"
            )
            playback_nodes = (
                ", ".join(str(node.object_id) for node in session.playback_nodes) or "none"
            )
            capture_nodes = (
                ", ".join(str(node.object_id) for node in session.capture_nodes) or "none"
            )

            lines.extend(
                [
                    f"  - {name}",
                    f"    Address: {bluetooth_device.address}",
                    f"    Paired: {_yes_no(bluetooth_device.paired)}",
                    f"    Trusted: {_yes_no(bluetooth_device.trusted)}",
                    f"    Connected: {_yes_no(bluetooth_device.connected)}",
                    f"    Blocked: {_yes_no(bluetooth_device.blocked)}",
                    f"    PipeWire device: {pipewire_device_id}",
                    f"    Playback nodes: {playback_nodes}",
                    f"    Capture nodes: {capture_nodes}",
                ]
            )
    else:
        lines.append("  None")

    lines.extend(
        [
            "",
            "PipeWire Bluetooth objects",
            f"  Devices: {len(pipewire_state.devices)}",
        ]
    )

    for pipewire_device in pipewire_state.devices:
        name = pipewire_device.description or pipewire_device.name or "<unnamed>"
        profile = _display_optional(pipewire_device.active_profile)
        lines.append(f"    - {pipewire_device.object_id}: {name} (profile={profile})")

    lines.append(f"  Nodes: {len(pipewire_state.nodes)}")

    for node in pipewire_state.nodes:
        name = node.description or node.name or "<unnamed>"
        state = _display_optional(node.state)
        lines.append(f"    - {node.object_id}: {name} ({node.media_class}, state={state})")

    return "\n".join(lines)


def _display_optional(value: str | None) -> str:
    return value if value is not None else "unknown"


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _service_state(running: bool | None) -> str:
    if running is True:
        return "running"

    if running is False:
        return "not running"

    return "unknown"
