import os, sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

import yfinance as yf
from data import fetcher, db
import config
from kiteconnect import KiteConnect
import pandas as pd

def main():

    kiteapikey = config.CONFIG_GLOBAL.KITE_API_KEY
    kc_instance = KiteConnect(api_key=kiteapikey)
    kitedata = fetcher.AuthData(kc_instance)

    all_instr = pd.DataFrame(kitedata.test_instruments())

    nse_eq_instr = all_instr[(all_instr['instrument_type'] == 'EQ') & 
                             (all_instr['exchange'] == 'NSE') & 
                             (all_instr['segment'] == 'NSE')]

    symbols = nse_eq_instr['tradingsymbol'].tolist()
    symbols = [symbol + ".NS" for symbol in symbols]

    chunk_size = 250
    num_chunks = (len(symbols) + chunk_size - 1) // chunk_size

    for i in range(num_chunks):
        start_index = i * chunk_size
        end_index = (i + 1) * chunk_size
        chunk_symbols = symbols[start_index:end_index]
        
        print(f"Processing chunk {i+1} of {num_chunks} with {len(chunk_symbols)} symbols...")

        # --- Start of the original code block ---
        data = yf.download(chunk_symbols, 
                            start="1995-01-01", 
                            auto_adjust=True,
                        #   keepna= True,
                            rounding=True
                            )
        
        #preparing data to store
        unstacked = data.unstack().reset_index()
        df_list = []
        for price_type in unstacked['Price'].unique():
            ptype_df = unstacked.loc[unstacked['Price'] == price_type].copy()
            ptype_df.rename(columns={0: price_type}, inplace = True)
            ptype_df['Ticker'] = ptype_df['Ticker'].str[:-3]
            ptype_df['Date'] = pd.to_datetime(ptype_df['Date'])
            ptype_df.drop(columns=['Price'], inplace=True)

            if price_type == 'Adj Close':
                print(ptype_df[ptype_df['Adj Close'].isnull() == False])

            df_list.append(ptype_df)
        
        merged_df = df_list[0]
        for i in range(1, len(df_list)):
            merged_df = pd.merge(merged_df, df_list[i], on=['Ticker', 'Date'], how='outer')

        merged_df.rename(columns={'Adj Close': 'Adj_close'}, inplace=True)
        print(merged_df)
        # --- End of the original code block ---


    # yf API call
    # data = yf.download(symbols, 
    #                    start="1995-01-01", 
    #                    auto_adjust=True,
    #                 #    keepna= True,
    #                    rounding=True
    #                    )
    
    # #preparing data to store
    # unstacked = data.unstack().reset_index()
    # df_list = []
    # for price_type in unstacked['Price'].unique():
    #     ptype_df = unstacked.loc[unstacked['Price'] == price_type].copy()
    #     ptype_df.rename(columns={0: price_type}, inplace = True)
    #     ptype_df['Ticker'] = ptype_df['Ticker'].str[:-3]
    #     ptype_df['Date'] = pd.to_datetime(ptype_df['Date'])
    #     ptype_df.drop(columns=['Price'], inplace=True)

    #     if price_type == 'Adj Close':
    #         print(ptype_df[ptype_df['Adj Close'].isnull() == False])

    #     df_list.append(ptype_df)
    
    # merged_df = df_list[0]
    # for i in range(1, len(df_list)):
    #     merged_df = pd.merge(merged_df, df_list[i], on=['Ticker', 'Date'], how='outer')

    # merged_df.rename(columns={'Adj Close': 'Adj_close'}, inplace=True)
    # print(merged_df)
    

if __name__ == '__main__':
    main()
