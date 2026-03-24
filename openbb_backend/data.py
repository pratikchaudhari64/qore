"""
Portfolio Holdings Timeline Calculator

This module calculates portfolio holdings over time from trade data.
Supports both daily and trade-date granularity.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Literal
from databases import quest_db

class HoldingsTimelineCalculator:
    """
    Calculates portfolio holdings timeline from trades data.
    
    Aggregates trades by symbol (across exchanges) and tracks:
    - Quantity held over time
    - Weighted average price
    - Invested value
    - Daily holdings with carry-forward logic
    """
    
    def __init__(self, trades_df: pd.DataFrame):
        """
        Initialize calculator with trades dataframe.
        
        Args:
            trades_df: DataFrame with columns:
                - fill_timestamp: datetime of trade execution
                - tradingsymbol: symbol name
                - quantity: number of shares
                - average_price: price per share
                - transaction_type: 'BUY'/'buy' or 'SELL'/'sell'
                - account_id: account identifier
        """
        self.trades_df = trades_df.copy()
        self._prepare_data()
        self._fetch_portfolio_market_prices()
        self.price_map = {}
        self.sec_id_dict = {}
    
    def _prepare_data(self):
        """Prepare and clean the trades data."""
        # Convert fill_timestamp to datetime
        self.trades_df['fill_timestamp'] = pd.to_datetime(
            self.trades_df['fill_timestamp']
        )
        
        # Extract date only (remove time component)
        self.trades_df['trade_date'] = self.trades_df['fill_timestamp'].dt.date
        
        # Standardize transaction type to uppercase
        self.trades_df['transaction_type'] = (
            self.trades_df['transaction_type'].str.upper()
        )
        
        # Handle tags - default to 'untagged' if null/empty
        if 'tag' not in self.trades_df.columns:
            self.trades_df['tag'] = 'untagged'
        else:
            self.trades_df['tag'] = self.trades_df['tag'].fillna('untagged')
            self.trades_df['tag'] = self.trades_df['tag'].replace('', 'untagged')
        
        # Sort by date and timestamp
        self.trades_df = self.trades_df.sort_values(
            ['trade_date', 'fill_timestamp']
        ).reset_index(drop=True)
    
    def _fetch_portfolio_market_prices(self):
        
        accounts = self.trades_df['account_id'].unique()

        self.market_prices = {}

        def get_all_market_prices(acc):

            account_trades = self.trades_df[
                self.trades_df['account_id'] == acc
            ].copy()
            
            if account_trades.empty:
                return self._empty_response(acc, granularity = 'daily')
            

            account_trades['fill_timestamp'] = pd.to_datetime(account_trades['fill_timestamp'])
            first_trade_date = (account_trades['fill_timestamp'].dt.date).min()

            
            daily_price_sql = f"""
            select *,
            date_trunc('day', timestamp) as ts_day
            from daily_historical_prices
            where 1=1
            AND security_id in ({str(list(account_trades['exchange_token'].unique()))[1:-1]})
            AND timestamp >= to_timestamp('{str(first_trade_date)}', 'yyyy-MM-dd')
            order by security_id, timestamp
            """

            acc_daily_prices = quest_db.read_questdb_dataframe(query= daily_price_sql)

            acc_daily_prices.loc[:, 'date'] = pd.to_datetime(acc_daily_prices['ts_day']).dt.date


            token_symbol_map = self.trades_df.groupby(['tradingsymbol', 'exchange_token', 'exchange'])['id'].count().reset_index().drop(columns=['id'])
            acc_daily_prices = acc_daily_prices.merge(token_symbol_map,
                            left_on='security_id',
                            right_on='exchange_token',
                            how='left')

            return acc_daily_prices

        for acc in accounts:
            self.market_prices[acc] = get_all_market_prices(acc)
            pass

        return self.market_prices
    
    def calculate_timeline(
        self,
        account_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        granularity: Literal['daily', 'trade_dates'] = 'daily'
    ) -> Dict:
        """
        Calculate holdings timeline for a specific account.
        
        Args:
            account_id: Account to calculate holdings for
            start_date: Start date (YYYY-MM-DD), defaults to first trade
            end_date: End date (YYYY-MM-DD), defaults to today
            granularity: 'daily' for all days, 'trade_dates' for trade days only
        
        Returns:
            Dictionary with holdings timeline in the specified format
        """
        # Filter trades for this account
        account_trades = self.trades_df[
            self.trades_df['account_id'] == account_id
        ].copy()
        
        if account_trades.empty:
            return self._empty_response(account_id, granularity)
        
        # Filter market prices for this account --> dataframe
        account_market_prices = self.market_prices[account_id]

        self.price_map = {
            (row.tradingsymbol, row.exchange_token, row.date): row.close
            for row in account_market_prices.itertuples(index=False)
        }
        self.sec_id_dict = (
            account_market_prices
            .drop_duplicates('tradingsymbol')
            .set_index('tradingsymbol')['exchange_token']
            .to_dict()
        )

        # Determine date range
        first_trade_date = account_trades['trade_date'].min()
        last_trade_date = account_trades['trade_date'].max()
        
        if start_date:
            start_date = pd.to_datetime(start_date).date()
            start_date = max(start_date, first_trade_date)
        else:
            start_date = first_trade_date
        
        if end_date:
            end_date = pd.to_datetime(end_date).date()
        else:
            end_date = datetime.now().date()
        
        # Filter trades within date range
        account_trades = account_trades[
            (account_trades['trade_date'] >= start_date) &
            (account_trades['trade_date'] <= end_date)
        ]
        
        # Calculate holdings based on granularity
        if granularity == 'trade_dates':
            timeline = self._calculate_trade_dates_timeline(
                account_trades, start_date, end_date
            )
        else:  # daily
            timeline = self._calculate_daily_timeline(
                account_trades, start_date, end_date
            )
        
        # Count trading days (days with actual trades)
        trading_days = len(account_trades['trade_date'].unique())
        total_days = (end_date - start_date).days + 1
        
        return {
            'account_id': account_id,
            'currency': 'INR',
            'granularity': granularity,
            'date_range': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'total_days': total_days,
                'trading_days': trading_days
            },
            'timeline': timeline
        }
    
    def _calculate_trade_dates_timeline(
        self,
        trades: pd.DataFrame,
        start_date,
        end_date
    ) -> List[Dict]:
        """Calculate holdings only for dates with trades."""
        timeline = []
        holdings_state = {}  # symbol -> bucket -> {qty, avg_price, invested_value}
        
        # Group trades by date
        for trade_date in trades['trade_date'].unique():
            date_trades = trades[trades['trade_date'] == trade_date]
            
            # Process all trades for this date
            trades_count_today = self._process_trades_for_date(
                date_trades, holdings_state
            )
            
            # Create snapshot for this date
            timeline_entry = self._create_timeline_entry(
                trade_date, holdings_state, trades_count_today
            )
            timeline.append(timeline_entry)
        
        return timeline
    
    def _calculate_daily_timeline(
        self,
        trades: pd.DataFrame,
        start_date,
        end_date
        # account_market_prices: pd.DataFrame
    ) -> List[Dict]:
        """Calculate holdings for every day (with carry-forward)."""
        timeline = []
        holdings_state = {}  # symbol -> bucket -> {qty, avg_price, invested_value}
        
        # Create date range for all days
        current_date = start_date
        
        while current_date <= end_date:
            # Get trades for this date
            date_trades = trades[trades['trade_date'] == current_date]
            
            if not date_trades.empty:
                # Process trades and update holdings
                trades_count_today = self._process_trades_for_date(
                    date_trades, holdings_state
                )
            else:
                # No trades today - carry forward
                trades_count_today = {}
                for symbol in holdings_state:
                    for bucket in holdings_state[symbol]:
                        key = f"{symbol}:{bucket}"
                        trades_count_today[key] = 0
            
            # Create snapshot for this date
            timeline_entry = self._create_timeline_entry(
                current_date, holdings_state, trades_count_today
            )
            timeline.append(timeline_entry)
            
            # Move to next day
            current_date += timedelta(days=1)
        
        return timeline
    
    def _process_trades_for_date(
        self,
        date_trades: pd.DataFrame,
        holdings_state: Dict
    ) -> Dict[str, int]:
        """
        Process all trades for a date and update holdings state.
        
        Args:
            date_trades: Trades for this specific date
            holdings_state: Mutable dict tracking current holdings by symbol and bucket
        
        Returns:
            Dict mapping "symbol:bucket" -> number of trades today
        """
        trades_count = {}
        
        # Process each trade individually to track bucket
        for _, trade in date_trades.iterrows():
            symbol = trade['tradingsymbol']
            tag = trade['tag']
            key = f"{symbol}:{tag}"
            
            trades_count[key] = trades_count.get(key, 0) + 1
            
            self._apply_trade(
                symbol,
                tag,
                trade['transaction_type'],
                trade['quantity'],
                trade['average_price'],
                holdings_state
            )
        
        return trades_count
    
    def _apply_trade(
        self,
        symbol: str,
        tag: str,
        transaction_type: str,
        quantity: int,
        price: float,
        holdings_state: Dict
    ):
        """
        Apply a single trade to update holdings state.
        
        Updates holdings_state in-place with bucket-aware tracking.
        Structure: holdings_state[symbol][bucket] = {quantity, average_price, invested_value}
        """
        if symbol not in holdings_state:
            holdings_state[symbol] = {}
        
        if tag not in holdings_state[symbol]:
            holdings_state[symbol][tag] = {
                'quantity': 0,
                'average_price': 0.0,
                'invested_value': 0.0
            }
        
        current = holdings_state[symbol][tag]
        
        if transaction_type == 'BUY':
            # Calculate new weighted average price
            old_value = current['quantity'] * current['average_price']
            new_value = quantity * price
            total_quantity = current['quantity'] + quantity
            
            if total_quantity > 0:
                new_avg_price = (old_value + new_value) / total_quantity
            else:
                new_avg_price = price
            
            # Update holdings
            current['quantity'] = total_quantity
            current['average_price'] = round(new_avg_price, 2)
            current['invested_value'] = round(
                current['quantity'] * current['average_price'], 2
            )
        
        elif transaction_type == 'SELL':
            # Reduce quantity, keep average price same
            current['quantity'] -= quantity
            
            if current['quantity'] < 0:
                # Handle short positions or errors
                pass
            
            # Recalculate invested value with same avg price
            current['invested_value'] = round(
                current['quantity'] * current['average_price'], 2
            )
            
            # If completely sold out, remove this bucket
            if current['quantity'] == 0:
                del holdings_state[symbol][tag]
                # If no buckets left for symbol, remove symbol
                if not holdings_state[symbol]:
                    del holdings_state[symbol]
    
    def _create_timeline_entry(
        self,
        date,
        holdings_state: Dict,
        trades_count_today: Dict[str, int]
        # account_market_prices: pd.DataFrame
    ) -> Dict:
        """Create a timeline entry for a specific date with bucket breakdown."""
        
        # Prepare bucket-wise holdings
        buckets = {}

        # price_map = account_market_prices.set_index(['tradingsymbol', 'exchange_token', 'date'])['close'].to_dict()
        # sec_id_dict = account_market_prices.set_index(['tradingsymbol'])['exchange_token'].to_dict()

        def get_mkt_close_price(symbol, date_str):

            try:
                sec_id = self.sec_id_dict.get(symbol)
                close_price = self.price_map.get((symbol, str(sec_id), date_str))
                
                while close_price is None:
                    date_str = date_str - timedelta(days = 1)
                    close_price = self.price_map.get((symbol, str(sec_id), date_str))
        
                return close_price
            
            except Exception as e:
                print(symbol)
                print(date_str)
                print(e)
                return None
            
            
        

        # First, organize by bucket
        for symbol, bucket_holdings in holdings_state.items():
            for bucket, holding in bucket_holdings.items():
                if holding['quantity'] <= 0:
                    continue
                    
                if bucket not in buckets:
                    buckets[bucket] = {
                        'invested_value': 0.0,
                        'market_value': 0.0,
                        'unique_symbols': 0,
                        'holdings': []
                    }
                mkt_close = get_mkt_close_price(symbol=symbol, date_str=date)
                if mkt_close == None:
                    mkt_val = None
                else:
                    mkt_val = mkt_close * holding['quantity']
                # Create holding entry for this bucket
                holding_entry = {
                    'symbol': symbol,
                    'quantity': holding['quantity'],
                    'average_price': holding['average_price'],
                    'invested_value': holding['invested_value'],
                    'trades_today': trades_count_today.get(f"{symbol}:{bucket}", 0),
                    'market_price': mkt_close,
                    'market_value': mkt_val,
                    'unrealized_pnl': round(mkt_val - holding['invested_value'], 2) if mkt_val is not None else None  # CALCULATE PNL
                }
                
                buckets[bucket]['holdings'].append(holding_entry)
                buckets[bucket]['invested_value'] += holding['invested_value']
                # buckets[bucket]['market_value'] += holding['market_value']
                if mkt_val is not None:
                    buckets[bucket]['market_value'] += mkt_val
        
        # Calculate unique symbols per bucket and sort holdings
        for bucket in buckets:
            buckets[bucket]['unique_symbols'] = len(buckets[bucket]['holdings'])
            buckets[bucket]['holdings'].sort(key=lambda x: x['symbol'])
            buckets[bucket]['invested_value'] = round(buckets[bucket]['invested_value'], 2)
            buckets[bucket]['market_value'] = round(buckets[bucket]['market_value'], 2)  # ROUND IT
        
        # Create aggregated flat holdings list (across all buckets)
        aggregated_holdings = {}
        total_invested = 0.0
        total_market_value = 0.0
        total_quantity = 0
        
        for symbol, bucket_holdings in holdings_state.items():
            for bucket, holding in bucket_holdings.items():
                if holding['quantity'] <= 0:
                    continue
                
                if symbol not in aggregated_holdings:
                    aggregated_holdings[symbol] = {
                        'quantity': 0,
                        'total_value': 0.0,
                        'total_market_value': 0.0,
                        'trades_today': 0
                    }
                
                aggregated_holdings[symbol]['quantity'] += holding['quantity']
                aggregated_holdings[symbol]['total_value'] += holding['invested_value']
                aggregated_holdings[symbol]['total_market_value'] += mkt_val
                aggregated_holdings[symbol]['trades_today'] += trades_count_today.get(
                    f"{symbol}:{bucket}", 0
                )
        
        # Convert aggregated holdings to list format
        holdings_list = []
        for symbol, agg in aggregated_holdings.items():
            avg_price = agg['total_value'] / agg['quantity'] if agg['quantity'] > 0 else 0
            mkt_close = get_mkt_close_price(symbol=symbol, date_str=date)
            if mkt_close == None:
                mkt_val = None
            else:
                mkt_val = mkt_close * agg['quantity']
            holding_entry = {
                'symbol': symbol,
                'quantity': agg['quantity'],
                'average_price': round(avg_price, 2),
                'invested_value': round(agg['total_value'], 2),
                'trades_today': agg['trades_today'],
                'market_price': mkt_close,
                'market_value': mkt_val,
                'unrealized_pnl': round(mkt_val - agg['total_value'], 2) if mkt_val is not None else None  
            }
            holdings_list.append(holding_entry)
            total_invested += agg['total_value']
            
            if mkt_val is not None:
                total_market_value += mkt_val
            
            total_quantity += agg['quantity']
        
        # Sort by symbol
        holdings_list.sort(key=lambda x: x['symbol'])

        total_unrealized_pnl = round(total_market_value - total_invested, 2) if total_market_value > 0 else None
        
        return {
            'date': date.isoformat(),
            'holdings': holdings_list,
            'summary': {
                'total_invested_value': round(total_invested, 2),
                'total_market_value': round(total_market_value, 2) if total_market_value > 0 else None, 
                'total_unrealized_pnl': total_unrealized_pnl,
                'unique_symbols': len(holdings_list),
                'total_quantity_all_symbols': total_quantity
            },
            'buckets': buckets
        }
    
    def _empty_response(self, account_id: str, granularity: str) -> Dict:
        """Return empty response when no trades found."""
        return {
            'account_id': account_id,
            'currency': 'INR',
            'granularity': granularity,
            'date_range': {
                'start_date': None,
                'end_date': None,
                'total_days': 0,
                'trading_days': 0
            },
            'timeline': []
        }

if __name__ == '__main__':

    def calculate_holdings_timeline(
        trades_df: pd.DataFrame,
        account_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        granularity: Literal['daily', 'trade_dates'] = 'daily'
    ) -> Dict:
        """
        Convenience function to calculate holdings timeline.
        
        Args:
            trades_df: DataFrame from "SELECT * FROM users_auth_trades"
            account_id: Account to calculate holdings for
            start_date: Start date (YYYY-MM-DD), defaults to first trade
            end_date: End date (YYYY-MM-DD), defaults to today
            granularity: 'daily' or 'trade_dates'
        
        Returns:
            Dictionary with holdings timeline
        
        Example:
            >>> import pandas as pd
            >>> trades_df = pd.read_sql("SELECT * FROM users_auth_trades", conn)
            >>> timeline = calculate_holdings_timeline(
            ...     trades_df,
            ...     account_id='AGL883',
            ...     granularity='daily'
            ... )
        """
        calculator = HoldingsTimelineCalculator(trades_df)
        return calculator.calculate_timeline(
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
            granularity=granularity
        )
    
    def get_data(query):
        try:
            with sqlite3.connect("../src_django/db.sqlite3") as conn:
                df = pd.read_sql_query(query, conn)
                # conn.close()
                return df
        except Exception as e:
            return e
        finally:
            conn.close()

    # conn.close()
    # "stonks/src_django/db.sqlite3"

    import pandas as pd
    import sqlite3
    trades_df = get_data("select * from users_auth_trades")

    print(trades_df)

    # timeline = calculate_holdings_timeline(
    #     trades_df,
    #     account_id='AGL883',
    #     granularity='daily'
    #         )
    # print(type(timeline['timeline']))
    # print(timeline['timeline'][0].keys())
    # print(pd.json_normalize(timeline['timeline']).columns)
    # print(pd.json_normalize(timeline['timeline']))