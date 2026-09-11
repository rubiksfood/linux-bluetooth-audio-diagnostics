import platform
import socket
from collections.abc import Mapping
from typing import Protocol


class SystemProvider(Protocol):
    """Interface for retrieving host operating-system information."""

    def os_release(self) -> Mapping[str, str]:
        """Return Linux distribution metadata."""
        ...

    def kernel_release(self) -> str:
        """Return the running kernel release."""
        ...

    def architecture(self) -> str:
        """Return the machine architecture."""
        ...

    def python_version(self) -> str:
        """Return the running Python version."""
        ...

    def hostname(self) -> str:
        """Return the system hostname."""
        ...


class PlatformSystemProvider:
    """Retrieve host information using the Python standard library."""

    def os_release(self) -> Mapping[str, str]:
        try:
            return platform.freedesktop_os_release()
        except OSError:
            return {}

    def kernel_release(self) -> str:
        return platform.release()

    def architecture(self) -> str:
        return platform.machine()

    def python_version(self) -> str:
        return platform.python_version()

    def hostname(self) -> str:
        return socket.gethostname()
