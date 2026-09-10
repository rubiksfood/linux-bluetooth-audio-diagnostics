from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ServiceStatus:
    """Runtime status for a relevant Linux service."""

    name: str
    running: bool | None


@dataclass(frozen=True, slots=True)
class SystemInfo:
    """Normalized information about the host and Linux audio stack."""

    distribution: str
    distribution_version: str | None
    kernel: str
    architecture: str
    python_version: str
    tool_version: str
    bluez_version: str | None = None
    pipewire_version: str | None = None
    wireplumber_version: str | None = None
    hostname: str | None = None
    services: tuple[ServiceStatus, ...] = ()
