from dataclasses import dataclass
from typing import Protocol

from bt_audio_diag.diagnostics import DiagnosticContext, DiagnosticEngine
from bt_audio_diag.models import (
    BluetoothAdapter,
    BluetoothDevice,
    DiagnosticFinding,
    PipeWireState,
    SystemInfo,
)
from bt_audio_diag.services.correlation import correlate_bluetooth_audio


class SystemInfoCollectorProtocol(Protocol):
    """Collection interface required for normalized system information."""

    def collect(self) -> SystemInfo: ...


class BluetoothAdapterCollectorProtocol(Protocol):
    """Collection interface required for BlueZ adapter state."""

    async def collect(self) -> tuple[BluetoothAdapter, ...]: ...


class BluetoothDeviceCollectorProtocol(Protocol):
    """Collection interface required for BlueZ device state."""

    async def collect(self) -> tuple[BluetoothDevice, ...]: ...


class PipeWireCollectorProtocol(Protocol):
    """Collection interface required for normalized PipeWire state."""

    def collect(self) -> PipeWireState: ...


@dataclass(frozen=True, slots=True)
class DiagnosticWorkflowResult:
    """Complete normalized result of one diagnostic workflow run."""

    context: DiagnosticContext
    pipewire_state: PipeWireState
    findings: tuple[DiagnosticFinding, ...]


class DiagnosticWorkflow:
    """Collect and correlate system evidence, then evaluate diagnostics."""

    def __init__(
        self,
        *,
        system_info_collector: SystemInfoCollectorProtocol,
        bluetooth_adapter_collector: BluetoothAdapterCollectorProtocol,
        bluetooth_device_collector: BluetoothDeviceCollectorProtocol,
        pipewire_collector: PipeWireCollectorProtocol,
        diagnostic_engine: DiagnosticEngine | None = None,
    ) -> None:
        self._system_info_collector = system_info_collector
        self._bluetooth_adapter_collector = bluetooth_adapter_collector
        self._bluetooth_device_collector = bluetooth_device_collector
        self._pipewire_collector = pipewire_collector
        self._diagnostic_engine = (
            diagnostic_engine if diagnostic_engine is not None else DiagnosticEngine()
        )

    async def run(self) -> DiagnosticWorkflowResult:
        """Run one complete Bluetooth audio diagnostic workflow."""

        system_info = self._system_info_collector.collect()
        adapters = await self._bluetooth_adapter_collector.collect()
        bluetooth_devices = await self._bluetooth_device_collector.collect()
        pipewire_state = self._pipewire_collector.collect()

        sessions = correlate_bluetooth_audio(
            bluetooth_devices,
            pipewire_state,
        )

        context = DiagnosticContext(
            system_info=system_info,
            adapters=adapters,
            sessions=sessions,
        )

        findings = self._diagnostic_engine.evaluate(context)

        return DiagnosticWorkflowResult(
            context=context,
            pipewire_state=pipewire_state,
            findings=findings,
        )
