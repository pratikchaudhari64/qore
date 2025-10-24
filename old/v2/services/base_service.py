import abc
import subprocess
import time
import requests

class ServiceManager(abc.ABC):
    """
    Abstract base class for managing external services.
    All service managers should inherit from this class and implement
    the start and stop methods.
    """
    def __init__(self, name: str):
        self._name = name
        self._proc: subprocess.Popen | None = None
        self._is_running: bool = False

    @property
    def name(self) -> str:
        """Returns the name of the service."""
        return self._name

    @property
    def is_running(self) -> bool:
        """Checks if the service process is currently running."""
        # Check if the process exists and is still alive
        if self._proc is not None:
            return self._proc.poll() is None and self._is_running
        return self._is_running

    @abc.abstractmethod
    def start(self):
        """
        Starts the service.
        This method should handle process creation and any necessary
        initialization or health checks.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def stop(self):
        """
        Stops the service.
        This method should handle process termination and cleanup.
        """
        raise NotImplementedError

    def __enter__(self):
        """Context manager entry point: starts the service."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point: stops the service."""
        self.stop()
