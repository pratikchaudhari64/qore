# services/questdb_server_manager.py
import subprocess
import time
import requests
import os
import sys
from services.base_service import ServiceManager

class QuestDBServerManager(ServiceManager):
    """
    Manages the lifecycle of the QuestDB server using its Docker image.
    Inherits from ServiceManager to provide a standardized interface.
    """
    def __init__(self, container_name: str = "questdb_instance", http_port: int = 9000, pg_port: int = 8812, data_volume_path: str | None = None):
        """
        Initializes the QuestDBServerManager for Docker.

        Args:
            container_name (str): The name to give the Docker container (default: "questdb_instance").
            http_port (int): The HTTP port on the host to map to QuestDB's internal HTTP port (default 9000).
            pg_port (int): The PostgreSQL wire protocol port on the host to map (default 8812).
            data_volume_path (str | None): Optional. Absolute path on the host for persistent QuestDB data.
                                           If None, a Docker volume will be used (data persists if container is stopped,
                                           but not if it's removed with `docker rm -v`).
                                           It is highly recommended to provide a specific path for clarity and backup.
        """
        super().__init__("QuestDB Docker Server")
        self._container_name = container_name
        self._http_port = http_port
        self._pg_port = pg_port
        self._data_volume_path = os.path.abspath(data_volume_path) if data_volume_path else None
        self._health_check_url = f"http://localhost:{self._http_port}/"
        self._docker_image = "questdb/questdb:latest" # Using the official QuestDB Docker image

    def _check_docker_daemon(self):
        """Checks if the Docker daemon is running."""
        try:
            subprocess.run(["docker", "info"], check=True, capture_output=True, text=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def start(self):
        """
        Starts the QuestDB Docker container and waits for it to become responsive.
        Raises RuntimeError if the container fails to start or Docker is not available.
        """
        if not self._check_docker_daemon():
            raise RuntimeError(
                "Docker daemon is not running or 'docker' command not found. "
                "Please start Docker Desktop/daemon or install Docker."
            )

        # Check if a container with this name already exists or is running
        try:
            # Check if container exists (running or stopped)
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"name={self._container_name}", "--format", "{{.Names}}"],
                capture_output=True, text=True, check=True
            )
            existing_container_name = result.stdout.strip()

            if existing_container_name == self._container_name:
                print(f"Container '{self._container_name}' already exists.")
                # Check if it's running
                running_check = subprocess.run(
                    ["docker", "ps", "--filter", f"name={self._container_name}", "--format", "{{.Names}}"],
                    capture_output=True, text=True, check=True
                )
                if running_check.stdout.strip() == self._container_name:
                    print(f"Container '{self._container_name}' is already running. Attaching to it.")
                    self._is_running = True
                    # We don't have a direct self._proc like for Popen, but conceptually it's running.
                    # For this ServiceManager, is_running will be based on Docker status.
                    return
                else:
                    print(f"Container '{self._container_name}' is stopped. Starting it...")
                    subprocess.run(["docker", "start", self._container_name], check=True)
                    print(f"Container '{self._container_name}' started.")
            else:
                print(f"Starting new QuestDB Docker container '{self._container_name}'...")
                # Build the docker run command
                docker_command = [
                    "docker", "run",
                    "-d", # Run in detached mode
                    "--name", self._container_name,
                    "-p", f"{self._http_port}:9000", # Map host_http_port to container's 9000
                    "-p", f"{self._pg_port}:8812"    # Map host_pg_port to container's 8812
                ]

                if self._data_volume_path:
                    os.makedirs(self._data_volume_path, exist_ok=True)
                    docker_command.extend(["-v", f"{self._data_volume_path}:/var/lib/questdb"])
                    print(f"QuestDB data will be stored on host at: {self._data_volume_path}")
                else:
                    print("QuestDB data will be stored in a Docker volume.")

                docker_command.append(self._docker_image)

                subprocess.run(docker_command, check=True)
            self._is_running = True

            # Wait for QuestDB to become responsive via its HTTP health check
            print(f"Waiting for {self.name} on {self._health_check_url} to become responsive...")
            start_time = time.time()
            timeout = 60 # Allow up to 60 seconds for QuestDB to fully start in Docker
            server_ready = False
            while time.time() - start_time < timeout:
                try:
                    r = requests.get(self._health_check_url, timeout=2)
                    if r.status_code == 200:
                        print(f"✅ {self.name} is running and responsive.")
                        server_ready = True
                        break
                except requests.ConnectionError:
                    pass
                except requests.Timeout:
                    pass
                time.sleep(1)

            if not server_ready:
                # If health check fails, try to stop/remove the container for a clean slate
                print(f"Health check failed for {self.name}. Attempting to stop and remove container '{self._container_name}'.")
                self.stop()
                self.remove_container()
                raise RuntimeError(f"{self.name} failed to become responsive in time.")

        except subprocess.CalledProcessError as e:
            self._is_running = False
            print(f"Docker command failed: {e.cmd}\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}", file=sys.stderr)
            raise RuntimeError(f"Failed to start QuestDB Docker container: {e.stderr}")
        except Exception as e:
            self._is_running = False
            print(f"An unexpected error occurred while starting {self.name}: {e}", file=sys.stderr)
            raise

    def stop(self):
        """
        Stops the QuestDB Docker container.
        """
        if self._check_docker_daemon():
            try:
                # Check if the container is running
                result = subprocess.run(
                    ["docker", "ps", "--filter", f"name={self._container_name}", "--format", "{{.Names}}"],
                    capture_output=True, text=True, check=True
                )
                if result.stdout.strip() == self._container_name:
                    print(f"Stopping QuestDB Docker container '{self._container_name}'...")
                    subprocess.run(["docker", "stop", self._container_name], check=True)
                    print(f"✅ Container '{self._container_name}' stopped.")
                else:
                    print(f"Container '{self._container_name}' is not running.")
                self._is_running = False
            except subprocess.CalledProcessError as e:
                print(f"Error stopping container '{self._container_name}': {e.stderr}", file=sys.stderr)
            except FileNotFoundError:
                print("Docker command not found. Cannot stop container.", file=sys.stderr)
        else:
            print("Docker daemon not running. Cannot stop container.", file=sys.stderr)

    def remove_container(self):
        """
        Removes the QuestDB Docker container.
        This will delete the container and its associated (unnamed) volumes.
        If a named volume or host-mounted path was used, the data will persist.
        """
        if self._check_docker_daemon():
            try:
                # Check if container exists (running or stopped)
                result = subprocess.run(
                    ["docker", "ps", "-a", "--filter", f"name={self._container_name}", "--format", "{{.Names}}"],
                    capture_output=True, text=True, check=True
                )
                if result.stdout.strip() == self._container_name:
                    print(f"Removing QuestDB Docker container '{self._container_name}'...")
                    subprocess.run(["docker", "rm", "-f", "-v", self._container_name], check=True) # -f to force stop if running, -v to remove anonymous volumes
                    print(f"🗑️ Container '{self._container_name}' removed.")
                else:
                    print(f"Container '{self._container_name}' does not exist.")
            except subprocess.CalledProcessError as e:
                print(f"Error removing container '{self._container_name}': {e.stderr}", file=sys.stderr)
            except FileNotFoundError:
                print("Docker command not found. Cannot remove container.", file=sys.stderr)
        else:
            print("Docker daemon not running. Cannot remove container.", file=sys.stderr)

    # Override is_running to check Docker container status
    @property
    def is_running(self) -> bool:
        """Checks if the Docker container is currently running."""
        if not self._check_docker_daemon():
            return False
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={self._container_name}", "--format", "{{.Names}}"],
                capture_output=True, text=True, check=True
            )
            return result.stdout.strip() == self._container_name
        except subprocess.CalledProcessError:
            return False # Docker command failed, assume not running