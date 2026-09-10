import asyncio
from collections.abc import Mapping
from typing import Protocol, cast

from dbus_fast import BusType, Message, MessageType, Variant
from dbus_fast.aio import MessageBus

_BLUEZ_SERVICE = "org.bluez"
_BLUEZ_ROOT_PATH = "/"
_OBJECT_MANAGER_INTERFACE = "org.freedesktop.DBus.ObjectManager"
_GET_MANAGED_OBJECTS_METHOD = "GetManagedObjects"
_MANAGED_OBJECTS_SIGNATURE = "a{oa{sa{sv}}}"

type BlueZProperties = Mapping[str, object]
type BlueZInterfaces = Mapping[str, BlueZProperties]
type BlueZManagedObjects = Mapping[str, BlueZInterfaces]


class BlueZDBusError(RuntimeError):
    """Raised when BlueZ state cannot be retrieved through D-Bus."""


class BlueZObjectManager(Protocol):
    """Interface for retrieving BlueZ-managed D-Bus objects."""

    async def get_managed_objects(self) -> BlueZManagedObjects:
        """Return normalized BlueZ objects and their properties."""
        ...


class DbusFastBlueZObjectManager:
    """Retrieve BlueZ-managed objects from the system D-Bus."""

    def __init__(self, timeout_seconds: float = 5.0) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")

        self._timeout_seconds = timeout_seconds

    async def get_managed_objects(self) -> BlueZManagedObjects:
        bus = MessageBus(bus_type=BusType.SYSTEM)

        try:
            async with asyncio.timeout(self._timeout_seconds):
                await bus.connect()

                reply = await bus.call(
                    Message(
                        destination=_BLUEZ_SERVICE,
                        path=_BLUEZ_ROOT_PATH,
                        interface=_OBJECT_MANAGER_INTERFACE,
                        member=_GET_MANAGED_OBJECTS_METHOD,
                    )
                )

            if reply.message_type == MessageType.ERROR:
                error_name = reply.error_name or "unknown D-Bus error"
                detail = str(reply.body[0]) if reply.body else ""

                message = f"BlueZ GetManagedObjects failed: {error_name}"

                if detail:
                    message = f"{message}: {detail}"

                raise BlueZDBusError(message)

            if reply.message_type != MessageType.METHOD_RETURN:
                raise BlueZDBusError(
                    "BlueZ GetManagedObjects returned an unexpected D-Bus message type"
                )

            if reply.signature != _MANAGED_OBJECTS_SIGNATURE or len(reply.body) != 1:
                raise BlueZDBusError("BlueZ GetManagedObjects returned an unexpected response")

            return _normalize_managed_objects(cast(object, reply.body[0]))

        except BlueZDBusError:
            raise
        except TimeoutError as exc:
            raise BlueZDBusError("Timed out while querying BlueZ over D-Bus") from exc
        except Exception as exc:
            raise BlueZDBusError("Failed to query BlueZ over D-Bus") from exc
        finally:
            if bus.connected:
                bus.disconnect()


def _normalize_managed_objects(
    raw_objects: object,
) -> dict[str, dict[str, dict[str, object]]]:
    objects = _expect_mapping(
        raw_objects,
        context="managed objects",
    )

    normalized: dict[str, dict[str, dict[str, object]]] = {}

    for raw_object_path, raw_interfaces in objects.items():
        if not isinstance(raw_object_path, str):
            raise BlueZDBusError("Invalid BlueZ D-Bus response: object path is not a string")

        interfaces = _expect_mapping(
            raw_interfaces,
            context=f"interfaces for {raw_object_path}",
        )

        normalized_interfaces: dict[str, dict[str, object]] = {}

        for raw_interface_name, raw_properties in interfaces.items():
            if not isinstance(raw_interface_name, str):
                raise BlueZDBusError("Invalid BlueZ D-Bus response: interface name is not a string")

            properties = _expect_mapping(
                raw_properties,
                context=f"properties for {raw_interface_name}",
            )

            normalized_properties: dict[str, object] = {}

            for raw_property_name, raw_variant in properties.items():
                if not isinstance(raw_property_name, str):
                    raise BlueZDBusError(
                        "Invalid BlueZ D-Bus response: property name is not a string"
                    )

                if not isinstance(raw_variant, Variant):
                    raise BlueZDBusError(
                        "Invalid BlueZ D-Bus response: "
                        f"{raw_interface_name}.{raw_property_name} "
                        "is not a D-Bus variant"
                    )

                normalized_properties[raw_property_name] = cast(
                    object,
                    raw_variant.value,
                )

            normalized_interfaces[raw_interface_name] = normalized_properties

        normalized[raw_object_path] = normalized_interfaces

    return normalized


def _expect_mapping(
    value: object,
    *,
    context: str,
) -> Mapping[object, object]:
    if not isinstance(value, Mapping):
        raise BlueZDBusError(f"Invalid BlueZ D-Bus response: {context} is not a mapping")

    return cast(Mapping[object, object], value)
