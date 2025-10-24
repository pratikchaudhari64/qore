# services/questdb_server_manager.py
import subprocess
import time
import requests
import os
import sys
from services.base_service import ServiceManager

class QuestDBServerManager(ServiceManager):
    """
    Manages the lifecycle of the QuestDB server.
    Inherits from ServiceManager to provide a standardized interface.
    """
    def __init__(self, questdb_home_path: str, http_port: int = 9000, pg_port: int = 8812, db_root_path: str | None = None):
        """
        Initializes the QuestDBServerManager.

        Args:
            questdb_home_path (str): The absolute path to the root directory of your QuestDB installation.
                                     This is the directory containing 'bin', 'lib', 'conf' folders.
            http_port (int): The HTTP port QuestDB will listen on (default 9000).
            pg_port (int): The PostgreSQL wire protocol port QuestDB will listen on (default 8812).
            db_root_path (str | None): Optional. The absolute path where QuestDB should store its data.
                                       If None, data will be stored in a 'db' folder within questdb_home_path.
        """
        super().__init__("QuestDB Server")
        self._questdb_home_path = os.path.abspath(questdb_home_path)
        self._http_port = http_port
        self._pg_port = pg_port
        self._db_root_path = os.path.abspath(db_root_path) if db_root_path else None
        # QuestDB's HTTP endpoint on port 9000 is used for health checks and API calls.
        self._health_check_url = f"http://localhost:{self._http_port}/"
        self._java_executable = 'java'

        self._questdb_jar_path = os.path.join(self._questdb_home_path, 'lib', 'questdb.jar')

        if not os.path.exists(self._questdb_jar_path):
            raise FileNotFoundError(
                f"QuestDB JAR not found at: {self._questdb_jar_path}. "
                "Please ensure `questdb_home_path` points to the root of your QuestDB installation."
            )

    def start(self):
        """
        Starts the QuestDB server process and waits for it to become responsive.
        Raises RuntimeError if the server fails to start.
        """
        if self.is_running:
            print(f"{self.name} is already running.")
            return

        print(f"Starting {self.name} on HTTP port {self._http_port}, PG port {self._pg_port}...")

        # Construct the command to run QuestDB directly via its JAR file.
        # This is a robust way to manage the process.
        command = [
            self._java_executable,
            '-jar', self._questdb_jar_path,
            '-p', str(self._http_port),
            '-P', str(self._pg_port),
        ]

        # Add -d flag for a custom data path if provided.
        if self._db_root_path:
            command.extend(['-d', self._db_root_path])
            os.makedirs(self._db_root_path, exist_ok=True)
            print(f"QuestDB data path set to: {self._db_root_path}")
        else:
            print(f"QuestDB data path will default to '{self._questdb_home_path}/db'.")

        print(f"Executing QuestDB command: {' '.join(command)}")

        try:
            self._proc = subprocess.Popen(
                command,
                cwd=self._questdb_home_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            self._is_running = True
            print(f"Process for {self.name} started (PID: {self._proc.pid}). Waiting for health check...")

            start_time = time.time()
            timeout = 60
            server_ready = False
            while time.time() - start_time < timeout:
                try:
                    r = requests.get(self._health_check_url, timeout=2)
                    if r.status_code == 200:
                        print(f"✅ {self.name} is running and responsive on {self._health_check_url}")
                        server_ready = True
                        break
                except requests.ConnectionError:
                    pass
                except requests.Timeout:
                    pass
                time.sleep(1)

            if not server_ready:
                self.stop()
                stdout, stderr = self._proc.communicate(timeout=5)
                raise RuntimeError(
                    f"{self.name} failed to start in time ({timeout}s timeout). "
                    f"Last captured STDOUT:\n{stdout}\nLast captured STDERR:\n{stderr}"
                )
        except FileNotFoundError as e:
            self._is_running = False
            self._proc = None
            if self._java_executable in str(e):
                raise RuntimeError(
                    "Java executable not found. Please ensure Java (JRE 11+) is installed "
                    "and its 'java' command is accessible in your system's PATH."
                )
            raise RuntimeError(
                f"Error finding QuestDB components or executable: {e}. "
                "Ensure `questdb_home_path` is correct and Java is installed."
            )
        except Exception as e:
            self._is_running = False
            self._proc = None
            print(f"An unexpected error occurred while starting {self.name}: {e}", file=sys.stderr)
            raise

    def stop(self):
        """
        Stops the QuestDB server process if it is running.
        """
        if self._proc and self._proc.poll() is None:
            print(f"Stopping {self.name} (PID: {self._proc.pid})...")
            try:
                self._proc.terminate()
                self._proc.wait(timeout=10)
                print(f"✅ {self.name} stopped.")
            except subprocess.TimeoutExpired:
                print(f"❗ {self.name} did not terminate gracefully, killing it (PID: {self._proc.pid}).")
                self._proc.kill()
                self._proc.wait()
            finally:
                self._proc = None
                self._is_running = False
        else:
            print(f"{self.name} is not running or already stopped.")
