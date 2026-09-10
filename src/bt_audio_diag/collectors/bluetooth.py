from collections.abc import Mapping, Sequence

from bt_audio_diag.models import BluetoothAdapter
from bt_audio_diag.services.bluez_dbus import BlueZObjectManager

_ADAPTER_INTERFACE = "org.bluez.Adapter1"


class BlueZDataError(ValueError):
    """Raised when BlueZ returns invalid or incomplete object data."""


class BlueZAdapterCollector:
    """Collect normalized Bluetooth adapter state from BlueZ."""

    def __init__(self, object_manager: BlueZObjectManager) -> None:
        self._object_manager = object_manager

    async def collect(self) -> tuple[BluetoothAdapter, ...]:
        managed_objects = await self._object_manager.get_managed_objects()
        adapters: list[BluetoothAdapter] = []

        for object_path in sorted(managed_objects):
            interfaces = managed_objects[object_path]
            properties = interfaces.get(_ADAPTER_INTERFACE)

            if properties is None:
                continue

            adapters.append(
                _normalize_adapter(
                    object_path=object_path,
                    properties=properties,
                )
            )

        return tuple(adapters)


def _normalize_adapter(
    *,
    object_path: str,
    properties: Mapping[str, object],
) -> BluetoothAdapter:
    return BluetoothAdapter(
        object_path=object_path,
        address=_required_string(
            properties,
            "Address",
            object_path=object_path,
        ),
        alias=_optional_string(
            properties,
            "Alias",
            object_path=object_path,
        ),
        powered=_required_boolean(
            properties,
            "Powered",
            object_path=object_path,
        ),
        discoverable=_required_boolean(
            properties,
            "Discoverable",
            object_path=object_path,
        ),
        pairable=_required_boolean(
            properties,
            "Pairable",
            object_path=object_path,
        ),
        uuids=_string_tuple(
            properties,
            "UUIDs",
            object_path=object_path,
        ),
    )


def _required_string(
    properties: Mapping[str, object],
    name: str,
    *,
    object_path: str,
) -> str:
    value = properties.get(name)

    if not isinstance(value, str):
        raise BlueZDataError(f"{object_path}: expected string property {name}")

    return value


def _optional_string(
    properties: Mapping[str, object],
    name: str,
    *,
    object_path: str,
) -> str | None:
    value = properties.get(name)

    if value is None:
        return None

    if not isinstance(value, str):
        raise BlueZDataError(f"{object_path}: expected string property {name}")

    return value


def _required_boolean(
    properties: Mapping[str, object],
    name: str,
    *,
    object_path: str,
) -> bool:
    value = properties.get(name)

    if not isinstance(value, bool):
        raise BlueZDataError(f"{object_path}: expected boolean property {name}")

    return value


def _string_tuple(
    properties: Mapping[str, object],
    name: str,
    *,
    object_path: str,
) -> tuple[str, ...]:
    value = properties.get(name)

    if value is None:
        return ()

    if (
        not isinstance(value, Sequence)
        or isinstance(value, str)
        or not all(isinstance(item, str) for item in value)
    ):
        raise BlueZDataError(f"{object_path}: expected string-array property {name}")

    return tuple(value)
