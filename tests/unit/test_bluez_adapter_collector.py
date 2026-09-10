import pytest

from bt_audio_diag.collectors import BlueZAdapterCollector
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
