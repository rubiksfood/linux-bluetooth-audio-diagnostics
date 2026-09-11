import pytest

from bt_audio_diag.collectors import BlueZAdapterCollector, BlueZDataError
from bt_audio_diag.models import BluetoothAdapter
from bt_audio_diag.services.bluez_dbus import BlueZManagedObjects


class FakeBlueZObjectManager:
    def __init__(
        self,
        managed_objects: BlueZManagedObjects,
    ) -> None:
        self._managed_objects = managed_objects

    async def get_managed_objects(self) -> BlueZManagedObjects:
        return self._managed_objects


@pytest.mark.asyncio
async def test_collect_returns_empty_tuple_when_no_adapter_exists() -> None:
    managed_objects: BlueZManagedObjects = {
        "/org/bluez": {
            "org.bluez.AgentManager1": {},
        },
    }

    collector = BlueZAdapterCollector(object_manager=FakeBlueZObjectManager(managed_objects))

    result = await collector.collect()

    assert result == ()


@pytest.mark.asyncio
async def test_collect_returns_normalized_bluez_adapter() -> None:
    managed_objects: BlueZManagedObjects = {
        "/org/bluez": {
            "org.bluez.AgentManager1": {},
        },
        "/org/bluez/hci0": {
            "org.bluez.Adapter1": {
                "Address": "00:11:22:33:44:55",
                "Alias": "Test Adapter",
                "Powered": True,
                "Discoverable": False,
                "Pairable": True,
                "UUIDs": [
                    "0000110b-0000-1000-8000-00805f9b34fb",
                    "0000110e-0000-1000-8000-00805f9b34fb",
                ],
            },
        },
    }

    collector = BlueZAdapterCollector(object_manager=FakeBlueZObjectManager(managed_objects))

    result = await collector.collect()

    assert result == (
        BluetoothAdapter(
            object_path="/org/bluez/hci0",
            address="00:11:22:33:44:55",
            alias="Test Adapter",
            powered=True,
            discoverable=False,
            pairable=True,
            uuids=(
                "0000110b-0000-1000-8000-00805f9b34fb",
                "0000110e-0000-1000-8000-00805f9b34fb",
            ),
        ),
    )


@pytest.mark.asyncio
async def test_collect_returns_multiple_adapters_in_object_path_order() -> None:
    managed_objects: BlueZManagedObjects = {
        "/org/bluez/hci1": {
            "org.bluez.Adapter1": {
                "Address": "11:22:33:44:55:66",
                "Alias": "Adapter 1",
                "Powered": False,
                "Discoverable": False,
                "Pairable": False,
                "UUIDs": [],
            },
        },
        "/org/bluez/hci0": {
            "org.bluez.Adapter1": {
                "Address": "00:11:22:33:44:55",
                "Alias": "Adapter 0",
                "Powered": True,
                "Discoverable": True,
                "Pairable": True,
                "UUIDs": [],
            },
        },
    }

    collector = BlueZAdapterCollector(object_manager=FakeBlueZObjectManager(managed_objects))

    result = await collector.collect()

    assert tuple(adapter.object_path for adapter in result) == (
        "/org/bluez/hci0",
        "/org/bluez/hci1",
    )


@pytest.mark.asyncio
async def test_collect_handles_missing_optional_adapter_properties() -> None:
    managed_objects: BlueZManagedObjects = {
        "/org/bluez/hci0": {
            "org.bluez.Adapter1": {
                "Address": "00:11:22:33:44:55",
                "Powered": True,
                "Discoverable": False,
                "Pairable": True,
            },
        },
    }

    collector = BlueZAdapterCollector(object_manager=FakeBlueZObjectManager(managed_objects))

    result = await collector.collect()

    assert result[0].alias is None
    assert result[0].uuids == ()


@pytest.mark.asyncio
async def test_collect_rejects_invalid_required_adapter_property() -> None:
    managed_objects: BlueZManagedObjects = {
        "/org/bluez/hci0": {
            "org.bluez.Adapter1": {
                "Address": "00:11:22:33:44:55",
                "Alias": "Test Adapter",
                "Powered": "yes",
                "Discoverable": False,
                "Pairable": True,
                "UUIDs": [],
            },
        },
    }

    collector = BlueZAdapterCollector(object_manager=FakeBlueZObjectManager(managed_objects))

    with pytest.raises(
        BlueZDataError,
        match=r"expected boolean property Powered",
    ):
        await collector.collect()
