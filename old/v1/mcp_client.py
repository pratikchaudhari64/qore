import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

# from anthropic import Anthropic
import ollama
from dotenv import load_dotenv

from testing_ollama_server import main as testing_ollama_main

load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        # self.anthropic = Anthropic()

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server
        
        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")
            
        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )
        
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        
        await self.session.initialize()
        
        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])
    
    async def connect_to_streamablehttp_server(self, url: str):

        strhttp_transport = await self.exit_stack.enter_async_context(streamablehttp_client(url))
        self.read_stream, self.write_stream, _ = strhttp_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.read_stream, self.write_stream))

        await self.session.initialize()

        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    # Connect to a streamable HTTP server
        # async with streamablehttp_client(url) as (
        #     read_stream,
        #     write_stream,
        #     _,
        # ):
        #     # Create a session using the client streams
        #     async with ClientSession(read_stream, write_stream) as session:
        #         # Initialize the connection
        #         await session.initialize()
        #         # List available tools
        #         tools = await session.list_tools()
        #         print(f"Available tools: {[tool.name for tool in tools.tools]}")

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        response = await self.session.list_tools()
        
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            },
        } for tool in response.tools]

        print('sending to llm model...\n')
        ollama_response = testing_ollama_main(messages= messages, tools = available_tools)
        
        # print(ollama_response.json()['message']['tool_calls'][0]['function'])

        if ollama_response.json()['message']['tool_calls']:
            tool_name = ollama_response.json()['message']['tool_calls'][0]['function']['name']
            tool_args = ollama_response.json()['message']['tool_calls'][0]['function']['arguments']
            result = await self.session.call_tool(tool_name, tool_args)

        if len(ollama_response.json()['message']['content']) > 0:
            messages.append(
                {
                "role": "assistant",
                "content":ollama_response.json()['message']['content']
                }
            )
        # print(result.content)
        messages.append(
                {
                    "role": "user",
                    "content": result.content[0].text
                }
        )

        # print(messages)

        ollama_new_response = testing_ollama_main(messages= messages)

        final_text = ollama_new_response.json()['message']['content']

        return final_text


    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                
                if query.lower() == 'quit':
                    break
                    
                response = await self.process_query(query)
                print(response)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    # if len(sys.argv) < 2:
    #     print("Usage: python client.py <path_to_server_script>")
    #     sys.exit(1)
        
    client = MCPClient()
    try:
        # await client.connect_to_server(sys.argv[1])
        await client.connect_to_streamablehttp_server(url= "http://127.0.0.1:8089/mcp")
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())