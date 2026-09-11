import json
from collections.abc import Mapping
from typing import cast

from bt_audio_diag.models import AudioNode, PipeWireDevice, PipeWireState
from bt_audio_diag.services.command_runner import (
    CommandExecutionError,
    CommandRunner,
)

_PW_DUMP_COMMAND = ("pw-dump", "--no-colors")

_DEVICE_TYPE = "PipeWire:Interface:Device"
_NODE_TYPE = "PipeWire:Interface:Node"

_AUDIO_MEDIA_CLASSES = frozenset(
    {
        "Audio/Sink",
        "Audio/Source",
        "Audio/Duplex",
    }
)

_BLUEZ_AUDIO_FACTORIES = frozenset(
    {
        "api.bluez5.media.sink",
        "api.bluez5.media.source",
        "api.bluez5.a2dp.sink",
        "api.bluez5.a2dp.source",
        "api.bluez5.sco.sink",
        "api.bluez5.sco.source",
    }
)


class PipeWireCollectionError(RuntimeError):
    """Raised when PipeWire state cannot be collected."""


class PipeWireDataError(ValueError):
    """Raised when pw-dump returns malformed or unexpected data."""


class PipeWireCollector:
    """Collect normalized Bluetooth audio state from PipeWire."""

    def __init__(self, command_runner: CommandRunner) -> None:
        self._command_runner = command_runner

    def collect(self) -> PipeWireState:
        objects = self._collect_objects()

        devices: list[PipeWireDevice] = []
        bluetooth_device_ids: set[int] = set()

        for pipewire_object in objects:
            if pipewire_object.get("type") != _DEVICE_TYPE:
                continue

            object_id = _required_integer(
                pipewire_object,
                "id",
                context="PipeWire device",
            )
            props = _object_properties(
                pipewire_object,
                object_id=object_id,
            )

            if props.get("device.api") != "bluez5":
                continue

            bluetooth_device_ids.add(object_id)

            devices.append(
                PipeWireDevice(
                    object_id=object_id,
                    name=_optional_string(
                        props,
                        "device.name",
                        context=f"PipeWire device {object_id}",
                    ),
                    description=_optional_string(
                        props,
                        "device.description",
                        context=f"PipeWire device {object_id}",
                    ),
                    bluez_address=_optional_string(
                        props,
                        "api.bluez5.address",
                        context=f"PipeWire device {object_id}",
                    ),
                    bluez_path=_optional_string(
                        props,
                        "api.bluez5.path",
                        context=f"PipeWire device {object_id}",
                    ),
                    active_profile=_optional_string(
                        props,
                        "device.profile.name",
                        context=f"PipeWire device {object_id}",
                    ),
                )
            )

        nodes: list[AudioNode] = []

        for pipewire_object in objects:
            if pipewire_object.get("type") != _NODE_TYPE:
                continue

            object_id = _required_integer(
                pipewire_object,
                "id",
                context="PipeWire node",
            )

            info = _object_info(
                pipewire_object,
                object_id=object_id,
            )
            props = _properties_from_info(
                info,
                object_id=object_id,
            )

            media_class = _optional_string(
                props,
                "media.class",
                context=f"PipeWire node {object_id}",
            )

            if media_class not in _AUDIO_MEDIA_CLASSES:
                continue

            device_id = _optional_integer(
                props,
                "device.id",
                context=f"PipeWire node {object_id}",
            )

            if not _is_bluetooth_node(
                props,
                device_id=device_id,
                bluetooth_device_ids=bluetooth_device_ids,
            ):
                continue

            profile = _optional_string(
                props,
                "api.bluez5.profile",
                context=f"PipeWire node {object_id}",
            )

            if profile is None:
                profile = _optional_string(
                    props,
                    "device.profile.name",
                    context=f"PipeWire node {object_id}",
                )

            nodes.append(
                AudioNode(
                    object_id=object_id,
                    device_id=device_id,
                    name=_optional_string(
                        props,
                        "node.name",
                        context=f"PipeWire node {object_id}",
                    ),
                    description=_optional_string(
                        props,
                        "node.description",
                        context=f"PipeWire node {object_id}",
                    ),
                    media_class=media_class,
                    state=_optional_string(
                        info,
                        "state",
                        context=f"PipeWire node {object_id}",
                    ),
                    profile=profile,
                    codec=_optional_string(
                        props,
                        "api.bluez5.codec",
                        context=f"PipeWire node {object_id}",
                    ),
                    sample_rate=_optional_integer(
                        props,
                        "audio.rate",
                        context=f"PipeWire node {object_id}",
                    ),
                    channels=_optional_integer(
                        props,
                        "audio.channels",
                        context=f"PipeWire node {object_id}",
                    ),
                )
            )

        return PipeWireState(
            devices=tuple(sorted(devices, key=lambda device: device.object_id)),
            nodes=tuple(sorted(nodes, key=lambda node: node.object_id)),
        )

    def _collect_objects(self) -> list[dict[str, object]]:
        try:
            result = self._command_runner.run(_PW_DUMP_COMMAND)
        except CommandExecutionError as exc:
            raise PipeWireCollectionError("Failed to execute pw-dump") from exc

        if result.returncode != 0:
            detail = result.stderr.strip()

            message = "pw-dump failed"

            if detail:
                message = f"{message}: {detail}"

            raise PipeWireCollectionError(message)

        try:
            raw_data = cast(object, json.loads(result.stdout))
        except json.JSONDecodeError as exc:
            raise PipeWireDataError("pw-dump returned invalid JSON") from exc

        if not isinstance(raw_data, list):
            raise PipeWireDataError("pw-dump response must be a JSON array")

        objects: list[dict[str, object]] = []

        for index, raw_object in enumerate(raw_data):
            objects.append(
                _string_mapping(
                    raw_object,
                    context=f"pw-dump object at index {index}",
                )
            )

        return objects


def _is_bluetooth_node(
    properties: Mapping[str, object],
    *,
    device_id: int | None,
    bluetooth_device_ids: set[int],
) -> bool:
    if device_id is not None and device_id in bluetooth_device_ids:
        return True

    if properties.get("device.api") == "bluez5":
        return True

    factory_name = properties.get("factory.name")

    return isinstance(factory_name, str) and factory_name in _BLUEZ_AUDIO_FACTORIES


def _object_info(
    pipewire_object: Mapping[str, object],
    *,
    object_id: int,
) -> dict[str, object]:
    if "info" not in pipewire_object:
        raise PipeWireDataError(f"PipeWire object {object_id}: missing info")

    return _string_mapping(
        pipewire_object["info"],
        context=f"PipeWire object {object_id} info",
    )


def _object_properties(
    pipewire_object: Mapping[str, object],
    *,
    object_id: int,
) -> dict[str, object]:
    return _properties_from_info(
        _object_info(pipewire_object, object_id=object_id),
        object_id=object_id,
    )


def _properties_from_info(
    info: Mapping[str, object],
    *,
    object_id: int,
) -> dict[str, object]:
    if "props" not in info:
        raise PipeWireDataError(f"PipeWire object {object_id}: missing props")

    return _string_mapping(
        info["props"],
        context=f"PipeWire object {object_id} props",
    )


def _required_integer(
    values: Mapping[str, object],
    name: str,
    *,
    context: str,
) -> int:
    value = values.get(name)

    if isinstance(value, bool) or not isinstance(value, int):
        raise PipeWireDataError(f"{context}: expected integer property {name}")

    return value


def _optional_integer(
    values: Mapping[str, object],
    name: str,
    *,
    context: str,
) -> int | None:
    value = values.get(name)

    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(value, int):
        raise PipeWireDataError(f"{context}: expected integer property {name}")

    return value


def _optional_string(
    values: Mapping[str, object],
    name: str,
    *,
    context: str,
) -> str | None:
    value = values.get(name)

    if value is None:
        return None

    if not isinstance(value, str):
        raise PipeWireDataError(f"{context}: expected string property {name}")

    return value


def _string_mapping(
    value: object,
    *,
    context: str,
) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise PipeWireDataError(f"{context} must be a mapping")

    normalized: dict[str, object] = {}

    for key, item in value.items():
        if not isinstance(key, str):
            raise PipeWireDataError(f"{context} contains a non-string key")

        normalized[key] = item

    return normalized
