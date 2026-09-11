import pytest

from bt_audio_diag.collectors import BlueZDataError, BlueZDeviceCollector
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
async def test_collect_returns_normalized_connected_device() -> None:
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


@pytest.mark.asyncio
async def test_collect_preserves_paired_but_disconnected_state() -> None:
    managed_objects: BlueZManagedObjects = {
        "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF": {
            "org.bluez.Device1": {
                "Adapter": "/org/bluez/hci0",
                "Address": "AA:BB:CC:DD:EE:FF",
                "Name": "Test Headphones",
                "Alias": "Test Headphones",
                "Paired": True,
                "Trusted": True,
                "Connected": False,
                "Blocked": False,
            },
        },
    }

    collector = BlueZDeviceCollector(object_manager=FakeBlueZObjectManager(managed_objects))

    result = await collector.collect()

    assert result[0].paired is True
    assert result[0].connected is False


@pytest.mark.asyncio
async def test_collect_returns_multiple_devices_in_object_path_order() -> None:
    managed_objects: BlueZManagedObjects = {
        "/org/bluez/hci0/dev_FF_EE_DD_CC_BB_AA": {
            "org.bluez.Device1": {
                "Adapter": "/org/bluez/hci0",
                "Address": "FF:EE:DD:CC:BB:AA",
                "Name": "Device B",
                "Alias": "Device B",
                "Paired": True,
                "Trusted": False,
                "Connected": False,
                "Blocked": False,
            },
        },
        "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF": {
            "org.bluez.Device1": {
                "Adapter": "/org/bluez/hci0",
                "Address": "AA:BB:CC:DD:EE:FF",
                "Name": "Device A",
                "Alias": "Device A",
                "Paired": True,
                "Trusted": True,
                "Connected": True,
                "Blocked": False,
            },
        },
    }

    collector = BlueZDeviceCollector(object_manager=FakeBlueZObjectManager(managed_objects))

    result = await collector.collect()

    assert tuple(device.object_path for device in result) == (
        "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF",
        "/org/bluez/hci0/dev_FF_EE_DD_CC_BB_AA",
    )


@pytest.mark.asyncio
async def test_collect_handles_missing_optional_device_properties() -> None:
    managed_objects: BlueZManagedObjects = {
        "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF": {
            "org.bluez.Device1": {
                "Adapter": "/org/bluez/hci0",
                "Address": "AA:BB:CC:DD:EE:FF",
                "Paired": True,
                "Trusted": False,
                "Connected": False,
                "Blocked": False,
            },
        },
    }

    collector = BlueZDeviceCollector(object_manager=FakeBlueZObjectManager(managed_objects))

    result = await collector.collect()

    device = result[0]

    assert device.name is None
    assert device.alias is None
    assert device.rssi is None
    assert device.uuids == ()


@pytest.mark.asyncio
async def test_collect_rejects_boolean_rssi() -> None:
    managed_objects: BlueZManagedObjects = {
        "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF": {
            "org.bluez.Device1": {
                "Adapter": "/org/bluez/hci0",
                "Address": "AA:BB:CC:DD:EE:FF",
                "Paired": True,
                "Trusted": True,
                "Connected": True,
                "Blocked": False,
                "RSSI": True,
            },
        },
    }

    collector = BlueZDeviceCollector(object_manager=FakeBlueZObjectManager(managed_objects))

    with pytest.raises(
        BlueZDataError,
        match=r"expected integer property RSSI",
    ):
        await collector.collect()


@pytest.mark.asyncio
async def test_collect_rejects_missing_adapter_association() -> None:
    managed_objects: BlueZManagedObjects = {
        "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF": {
            "org.bluez.Device1": {
                "Address": "AA:BB:CC:DD:EE:FF",
                "Paired": True,
                "Trusted": True,
                "Connected": True,
                "Blocked": False,
            },
        },
    }

    collector = BlueZDeviceCollector(object_manager=FakeBlueZObjectManager(managed_objects))

    with pytest.raises(
        BlueZDataError,
        match=r"expected string property Adapter",
    ):
        await collector.collect()
