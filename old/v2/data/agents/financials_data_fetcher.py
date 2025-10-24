import time
import logging
import sys
import os
from datetime import datetime
import pandas as pd
import threading
import asyncio

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


session_data_cache= {}

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)



async def use_client_on_broswermcp(text_query):
    from services import mcp_server_manager, mcp_client_manager

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

    
    browsermcp = mcp_server_manager.BrowserMCPServerManager()
    # browsermcp.start()
    await asyncio.to_thread(browsermcp.start)
    await asyncio.sleep(3)

    threading.Thread(target=flush_proc_output, args=(browsermcp._proc,), daemon=True).start()
    threading.Thread(target=flush_proc_error, args=(browsermcp._proc,), daemon=True).start()

    while True:
        try:
            
            ollama_client = mcp_client_manager.BrowserMCPClientManager()

            # text_query = f"""go to https://www.screener.in/company/DMART/consolidated/#profit-loss 
            # and fetch the income statement data in a JSON format"""
            # text_query = "hi"
            
            response = await mcp_client_manager.get_client_response(mcp_client= ollama_client,
                                                                    text_query= text_query)
            
            # browsermcp.stop()
            await asyncio.to_thread(browsermcp.stop)
            return response
                
        except Exception as e:
            print(f"\nError: {str(e)}")
            # browsermcp.stop()
            await asyncio.to_thread(browsermcp.stop)

if __name__ == "__main__":
    try:
        # text_query = f"""ndla893r ?!"""
        # text_query = f"""go to https://www.screener.in/company/DMART/consolidated/#profit-loss 
        #     and fetch the income statement data in a JSON format"""
        text_query = """use the browser navigate tool to https://www.screener.in/company/DMART/consolidated/#profit-loss and extract the full income statement (profit & loss) table for Avenue Supermarts Ltd (DMart).

            Return the data as a JSON array where each element is an object representing one year, structured like this:

            text
            [
            {
                "year": 2014,
                "Revenue": 4686,
                "OperatingProfit": 341,
                "OperatingProfitMargin": 7,
                "Interest": 56,
                "Depreciation": 57,
                "ProfitBeforeTax": 245,
                "TaxPercent": 34,
                "NetProfit": 161,
                "EPS": 2.95,
                "DividendPayout": 0
            },
            {
                "year": 2015,
                ...
            }
            ]

            Extract the year as the four-digit number from the column header (e.g. “Mar 2014” → 2014).
            Ensure all numeric values are properly converted and missing values are represented as null.
            Return a properly formatted JSON array ready for use in Python or JavaScript. 
            Return ONLY the JSON data. Do NOT include any explanations, text, or introductions or the code to fetch it
            """
        # text_query = f"""go to https://pulse.zerodha.com/ and summarise the articles"""
        # text_query = f"""go to https://groww.in/stocks/jsw-cement-ltd/market-news and summarise the latest news"""
        # text_query = f"go to https://www.google.com/search?q=ITC+latest+news, then click on the links about articles that have news on the stock and return summary"
        
        resp = asyncio.run(use_client_on_broswermcp(text_query = text_query))
        print(resp)
    except KeyboardInterrupt:
        print("\nClient shutdown requested. Exiting.")
