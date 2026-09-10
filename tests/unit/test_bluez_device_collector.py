import pytest

from bt_audio_diag.collectors import BlueZDeviceCollector
from bt_audio_diag.models import BluetoothDevice
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
async def test_collect_returns_normalized_bluez_device() -> None:
    managed_objects: BlueZManagedObjects = {
        "/org/bluez/hci0": {
            "org.bluez.Adapter1": {},
        },
        "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF": {
            "org.bluez.Device1": {
                "Adapter": "/org/bluez/hci0",
                "Address": "AA:BB:CC:DD:EE:FF",
                "Name": "Test Headphones",
                "Alias": "Test Headphones",
                "Paired": True,
                "Trusted": True,
                "Connected": True,
                "Blocked": False,
                "RSSI": -42,
                "UUIDs": [
                    "0000110b-0000-1000-8000-00805f9b34fb",
                    "0000110e-0000-1000-8000-00805f9b34fb",
                ],
            },
        },
    }

    collector = BlueZDeviceCollector(object_manager=FakeBlueZObjectManager(managed_objects))

    result = await collector.collect()

    assert result == (
        BluetoothDevice(
            object_path="/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF",
            adapter_path="/org/bluez/hci0",
            address="AA:BB:CC:DD:EE:FF",
            name="Test Headphones",
            alias="Test Headphones",
            paired=True,
            trusted=True,
            connected=True,
            blocked=False,
            rssi=-42,
            uuids=(
                "0000110b-0000-1000-8000-00805f9b34fb",
                "0000110e-0000-1000-8000-00805f9b34fb",
            ),
        ),
    )
