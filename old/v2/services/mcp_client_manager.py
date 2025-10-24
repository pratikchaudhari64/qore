import asyncio
import os
import sys
from typing import Optional
from contextlib import AsyncExitStack
import requests

# --- Required MCP and LLM libraries ---
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from dotenv import load_dotenv

# Assuming your ollama test script is available
# from testing_ollama_server import main as testing_ollama_main

# --- Mocking ollama for standalone example ---
# If testing_ollama_main is not available, this mock will be used.
def testing_ollama_main(messages, tools=None):
    url = "http://localhost:11434/api/chat"

    payload = {
        "model": "llama3.1:latest",
        "messages":messages,
        "stream": False,
        "tools": tools
    }

    try:
        # Send a POST request with the JSON data
        response = requests.post(url, json=payload)
        return response

    except requests.exceptions.ConnectionError as e:
        print(f"Failed to connect to the Ollama server.")
        print(f"Please ensure the Ollama server is running. Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
# --- End Mock ---


# Add the project root to the Python path to allow importing 'services'
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..')
sys.path.insert(0, project_root)

from services.base_service import ServiceManager

load_dotenv()

class BrowserMCPClientManager(ServiceManager):
    """
    Manages the lifecycle of a connection to a BrowserMCP server, using the
    `mcp-client` library. It handles connection, tool interaction, and cleanup.
    """
    def __init__(self, url: str = "http://127.0.0.1:8089/mcp"):
        """
        Initializes the BrowserMCPClientManager.

        Args:
            url (str): The full URL to the MCP server's endpoint.
        """
        super().__init__("BrowserMCP Client")
        self._url = url
        self._session: Optional[ClientSession] = None
        self._exit_stack: Optional[AsyncExitStack] = None

    @property
    def is_running(self) -> bool:
        """Checks if the client session is active."""
        return self._is_running and self._session is not None

    async def start(self):
        """
        Starts the service by connecting to the MCP server via streamable HTTP.
        It establishes a session and lists the available tools.
        """
        if self.is_running:
            print(f"{self.name} is already connected.")
            return

        print(f"Starting {self.name} and connecting to {self._url}...")
        self._exit_stack = AsyncExitStack()
        try:
            strhttp_transport = await self._exit_stack.enter_async_context(
                streamablehttp_client(self._url)
            )
            read_stream, write_stream, _ = strhttp_transport
            self._session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )

            await self._session.initialize()
            self._is_running = True

            response = await self._session.list_tools()
            tools = response.tools
            print(f"✅ Connected to {self.name} with tools: {[tool.name for tool in tools]}")

        except Exception as e:
            print(f"❗ Failed to start {self.name}: {e}")
            await self.stop() # Ensure cleanup on failed start
            raise RuntimeError(f"Could not connect to MCP server at {self._url}") from e

    async def stop(self):
        """
        Stops the service by cleaning up all resources, including the
        MCP session and HTTP transport, using the async exit stack.
        """
        if not self._exit_stack:
            print(f"{self.name} is not running.")
            return

        print(f"Stopping {self.name}...")
        try:
            await self._exit_stack.aclose()
            print(f"✅ {self.name} stopped.")
        except Exception as e:
            print(f"❗ An error occurred while stopping {self.name}: {e}")
        finally:
            self._session = None
            self._exit_stack = None
            self._is_running = False

    # async def process_query(self, query: str) -> str:
    #     """
    #     Processes a user query by communicating with an LLM (Ollama) and
    #     using the MCP server's tools as needed.
    #     """
    #     if not self.is_running or not self._session:
    #         raise ConnectionError("Client is not connected. Please call start() first.")

    #     messages = [{"role": "user", "content": query}]

    #     # 1. Get available tools from the MCP session
    #     response = await self._session.list_tools()
    #     available_tools = [{
    #         "type": "function",
    #         "function": {
    #             "name": tool.name,
    #             "description": tool.description,
    #             "parameters": tool.inputSchema,
    #         },
    #     } for tool in response.tools]

    #     # 2. First call to LLM to decide if a tool should be used
    #     print('Sending to LLM model for tool selection...')
    #     ollama_response = testing_ollama_main(messages=messages, tools=available_tools)
    #     ollama_json = ollama_response.json()

    #     # 3. If the LLM decides to call a tool, execute it via MCP
    #     if ollama_json['message']['tool_calls']:
    #         tool_call = ollama_json['message']['tool_calls'][0]['function']
    #         tool_name = tool_call['name']
    #         tool_args = tool_call['arguments']
    #         print(f"LLM decided to call tool '{tool_name}' with args: {tool_args}")
            
    #         result = await self._session.call_tool(tool_name, tool_args)
    #         print(f"Tool '{tool_name}' returned: {result.content[0].text}")

    #         # Append the tool's result to the message history
    #         messages.append({
    #             "role": "assistant",
    #             "content": ollama_json['message']['content']
    #         })
    #         messages.append({
    #             "role": "user",  # Representing tool output as user input for the next turn
    #             "content": result.content[0].text
    #         })

    #         # 4. Second call to LLM to generate a final response based on tool output
    #         print("Sending tool result back to LLM for final response...")
    #         ollama_new_response = testing_ollama_main(messages=messages)
    #         final_text = ollama_new_response.json()['message']['content']
    #     else:
    #         # If no tool was called, the first response is the final one
    #         final_text = ollama_json['message']['content']

    #     return final_text

    async def process_query(self, query: str) -> str:
        """
        Processes a user query by communicating with an LLM (Ollama) and
        using the MCP server's tools as needed, with robust error handling.
        """
        if not self.is_running or not self._session:
            return "Error: Client is not connected. Please restart the application."

        messages = [{"role": "user", "content": query}]

        try:
            # 1. Get available tools from the MCP session
            response = await self._session.list_tools()
            available_tools = [{
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            } for tool in response.tools]

            # 2. First call to LLM to decide if a tool should be used
            print('Sending to LLM model for tool selection...')
            # ollama_response = testing_ollama_main(messages=messages, tools=available_tools)
            ollama_response = await asyncio.to_thread(testing_ollama_main, messages=messages, tools=available_tools)
            ollama_json = ollama_response.json()

            # 3. If the LLM decides to call a tool, execute it via MCP
            # Use .get() for safe dictionary key access to prevent KeyErrors
            tool_calls = ollama_json.get('message', {}).get('tool_calls')
            if tool_calls:
                tool_call = tool_calls[0]['function']
                tool_name = tool_call['name']
                tool_args = tool_call['arguments']
                print(f"LLM decided to call tool '{tool_name}' with args: {tool_args}")

                # result = await self._session.call_tool(tool_name, tool_args)
                # result = await asyncio.wait_for(
                #             self._session.call_tool(tool_name, tool_args),
                #             timeout=60
                #         )
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        print(f"Executing tool '{tool_name}' (Attempt {attempt + 1}/{max_retries})...")
                        
                        # The operation we are trying to retry
                        result = await asyncio.wait_for(
                            self._session.call_tool(tool_name, tool_args),
                            timeout=60
                        )

                        # If the call succeeds, break the loop
                        break 
                        
                    except asyncio.TimeoutError as e:
                        # This is where your previous code was breaking
                        print(f"❗ Operation timed out while calling tool '{tool_name}' on attempt {attempt + 1}.")
                        if attempt < max_retries - 1:
                            wait_time = 2 ** attempt  # Exponential backoff (1s, 2s, 4s...)
                            print(f"Retrying in {wait_time} seconds...")
                            await asyncio.sleep(wait_time)
                            continue  # Go to the next iteration of the loop
                        else:
                            # If all retries are exhausted, raise the error
                            print(f"All {max_retries} attempts to call '{tool_name}' failed.")
                            # Return a clear, actionable message to the LLM
                            return f"Error: The tool '{tool_name}' consistently timed out after {max_retries} attempts. The server may have an issue with the arguments provided. Please try a different approach."
                            
                else:
                    # This 'else' block runs if the loop completes without a 'break' (all retries failed)
                    # We already returned the error message above, so this is just a final fail-safe.
                    return f"An unknown error occurred after {max_retries} retries."



                # Validate the tool's response before proceeding
                if not result.content or not hasattr(result.content[0], 'text'):
                    return f"Error: Tool '{tool_name}' returned an empty or invalid response."
                
                tool_result_text = result.content[0].text
                print(f"Tool '{tool_name}' returned: {tool_result_text}")

                # Append the tool's result to the message history
                messages.append({
                    "role": "assistant",
                    "content": ollama_json.get('message', {}).get('content')
                })
                messages.append({
                    "role": "user",  # Representing tool output as user input for the next turn
                    "content": tool_result_text
                })

                # 4. Second call to LLM to generate a final response based on tool output
                print("Sending tool result back to LLM for final response...")
                # ollama_new_response = testing_ollama_main(messages=messages)
                ollama_new_response = await asyncio.to_thread(testing_ollama_main, messages=messages)
                final_text = ollama_new_response.json().get('message', {}).get('content', "Sorry, I couldn't generate a final response.")
            else:
                # If no tool was called, the first response is the final one
                final_text = ollama_json.get('message', {}).get('content', "Sorry, I couldn't process that request.")

            return final_text

        except ConnectionError as e:
            return f"Network Error: Could not communicate with the MCP server. Please check if it's running. Details: {e}"
        except (KeyError, IndexError, TypeError) as e:
            return f"Error: Received an unexpected response format from the LLM or tool. Details: {e}"
        except Exception as e:
            # A general catch-all for any other unexpected errors
            return f"An unexpected error occurred: {e}"



    async def chat_loop(self, terminal_input = True, text_query = None):

        if terminal_input:
            """Runs an interactive command-line chat loop."""
            print("\n🗣️  MCP Client Chat Started!")
            print("Type your queries or 'quit' to exit.")

            while self.is_running:
                try:
                    query = await asyncio.to_thread(input, "\nQuery: ")
                    if query.strip().lower() == 'quit':
                        break
                    response = await self.process_query(query)
                    print(f"\nResponse: {response}")
                except (EOFError, KeyboardInterrupt):
                    print("\nExiting chat loop...")
                    break
                except Exception as e:
                    print(f"\n❗ An error occurred during chat: {e}")
                    break
        
        else:
            """processes input query made to the client"""
            query = text_query
            while self.is_running:
                try:
                    # query = await asyncio.to_thread(input, "\nQuery: ")
                    # if query.strip().lower() == 'quit':
                    #     break
                    response = await self.process_query(query)
                    # print(f"\nResponse: {response}")
                    return response

                except Exception as e:
                    print(f"\n❗ An error occurred during chat: {e}")
                    return e
            
async def get_client_response(mcp_client, text_query):
    """Main function to demonstrate the BrowserMCPClientManager."""
    # Note: The BrowserMCPServer from the first example must be running for this to work.
    client_manager = mcp_client
    
    try:
        await client_manager.start()
        if client_manager.is_running:
            client_resp = await client_manager.chat_loop(terminal_input=False, text_query=text_query)
            # print(type(client_resp))
    except Exception as e:
        print(f"A critical error occurred: {e}")
        raise e
    finally:
        # The chat_loop breaking will lead here, ensuring cleanup.
        if client_manager.is_running:
            print('stopping the client')
            await client_manager.stop()
    
    return client_resp



async def main():
    """Main function to demonstrate the BrowserMCPClientManager."""
    # Note: The BrowserMCPServer from the first example must be running for this to work.
    client_manager = BrowserMCPClientManager()
    
    try:
        await client_manager.start()
        if client_manager.is_running:
            await client_manager.chat_loop()
    except Exception as e:
        print(f"A critical error occurred: {e}")
    finally:
        # The chat_loop breaking will lead here, ensuring cleanup.
        if client_manager.is_running:
            print('stopping the client')
            await client_manager.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nClient shutdown requested. Exiting.")
