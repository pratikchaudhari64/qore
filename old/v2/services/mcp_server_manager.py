import os, sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..')
sys.path.insert(0, project_root)

import subprocess
import threading
import time
import requests
from services.base_service import ServiceManager

import config


class BrowserMCPServerManager(ServiceManager):
    """
    Manages the lifecycle of the MCP (Multi-Agent Communication Protocol) server.
    Inherits from ServiceManager to provide a standardized interface.
    """
    def __init__(self, port: int = 8089):
        super().__init__("BrowserMCP Server")
        self._port = port
        self.npm_path = config.CONFIG_SERVICES.NPM_PATH

    def start(self):
        """
        Starts the MCP server process and waits for it to become responsive.
        Raises RuntimeError if the server fails to start.
        """
        if self.is_running:
            print(f"{self.name} is already running.")
            return

        print(f"Starting {self.name} on port {self._port}...")
        try:
            # Start MCP server via npx with vision and port
            self._proc = subprocess.Popen(
                [   self.npm_path,
                    # "npx", 
                    "@agent-infra/mcp-server-browser",
                    "--port", str(self._port),
                    "--headless",
                    # "--vision" 
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True, # Decode stdout/stderr as text
                encoding='utf-8',
                bufsize=1, # Line-buffered output
            )
            self._is_running = True

            #Implementing Threads to flush out stdout PIPE (AI SLOP)

            def print_stdout(proc):
                print ('aight')
                # for line in proc.stdout:
                #     print(line, end='')

            print(f"""Process for {self.name} started (PID: {self._proc.pid}); {print_stdout(self._proc)}""")
            # Read the first N lines from stdout after starting
            # max_lines = 10  # adjust as needed
            # lines_read = 0
            # while lines_read < max_lines:
            #     line = self._proc.stdout.readline()
            #     if not line:
            #         break  # No more output
            #     print(f"[MCP Server STDOUT]: {line.strip()}")
            #     lines_read += 1

        except FileNotFoundError:
            self._is_running = False
            self._proc = None
            raise RuntimeError(
                "npx command not found. Ensure Node.js and npm are installed "
                "and npx is available in your PATH."
            )
        except Exception as e:
            self._is_running = False
            self._proc = None
            print(f"Error starting {self.name}: {e}")
            raise

    def stop(self):
        """
        Stops the MCP server process if it is running.
        Terminates the process and cleans up.
        """
        if self._proc:
            print(f"Stopping {self.name} (PID: {self._proc.pid})...")
            try:
                self._proc.terminate()
                self._proc.wait(timeout=5) # Wait for process to terminate
                print(f"✅ {self.name} stopped.")
            except subprocess.TimeoutExpired:
                print(f"❗ {self.name} did not terminate gracefully, killing it.")
                self._proc.kill()
                self._proc.wait()
            finally:
                self._proc = None
                self._is_running = False
        else:
            print(f"{self.name} is not running.")

if __name__ == '__main__':
    # import os, sys
    import asyncio


    async def chat_loop():
        """Run an interactive chat loop"""

        # print("\nMCP Client Started!")
        # print("Type your queries or 'quit' to exit.")

        def flush_proc_output(proc):
            # Continuously read from proc.stdout until EOF
                while True:
                    line = proc.stdout.readline()
                    if not line:
                        # EOF reached; subprocess probably exited
                        break
                    # To discard output, comment this out; to print logs, uncomment:
                    print(line, end='')

        def flush_proc_error(proc):
            # Similarly for stderr
            while True:
                line = proc.stderr.readline()
                if not line:
                    break
                # print(line, end='')  # or discard by commenting
        
        browsermcp = BrowserMCPServerManager()
        browsermcp.start()

        threading.Thread(target=flush_proc_output, args=(browsermcp._proc,), daemon=True).start()
        threading.Thread(target=flush_proc_error, args=(browsermcp._proc,), daemon=True).start()

        while True:
            try:
                query = input("\nType 'Quit' to stop server. Threading has begun: ").strip()
                
                if query.lower() == 'quit':
                    browsermcp.stop()
                    break
                    
                response = query
                print(f"You Typed: {response}")
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    asyncio.run(chat_loop())


    pass
