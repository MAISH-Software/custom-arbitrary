import os
import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional
import psycopg2
import json
from psycopg2.extras import execute_values
from datetime import datetime

# Set up logging
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
    
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "spread_calculator.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("spread_calculator")

class SpreadCalculator:
    def __init__(self, 
                 db_connection_string: str,
                 lot_min: float = 250.0, 
                 lot_max: float = 1000.0, 
                 spread_in: float = 10.0, 
                 spread_out: float = 5.0):
        """
        Initialize the spread calculator
        
        Args:
            db_connection_string: PostgreSQL connection string
            lot_min: Minimum lot size in USDT
            lot_max: Maximum lot size in USDT
            spread_in: Entry spread threshold percentage
            spread_out: Exit spread threshold percentage
        """
        self.lot_min = lot_min
        self.lot_max = lot_max
        self.spread_in = spread_in
        self.spread_out = spread_out
        self.db_connection_string = db_connection_string
        
    def _connect_to_db(self):
        """Connect to the PostgreSQL database"""
        try:
            conn = psycopg2.connect(self.db_connection_string)
            return conn
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            raise
    
    def calculate_weighted_spot_ask(self, asks: List[List[float]], target_volume_usdt: float) -> Tuple[float, float, float]:
        """
        Calculate weighted average ask price on spot market for a given target volume
        
        Args:
            asks: List of [price, volume] pairs ordered by increasing price
            target_volume_usdt: Target volume in USDT
            
        Returns:
            Tuple of (weighted_avg_price, actual_volume_coins, actual_volume_usdt)
        """
        if not asks:
            return 0.0, 0.0, 0.0
        
        total_cost = 0.0
        total_coins = 0.0
        
        for price, coin_volume in asks:
            usdt_volume = price * coin_volume
            
            if total_cost + usdt_volume <= target_volume_usdt:
                # Take entire level
                total_cost += usdt_volume
                total_coins += coin_volume
            else:
                # Take partial level
                remaining_usdt = target_volume_usdt - total_cost
                remaining_coins = remaining_usdt / price
                total_cost += remaining_usdt
                total_coins += remaining_coins
                break
                
        if total_coins == 0:
            return 0.0, 0.0, 0.0
            
        weighted_avg_price = total_cost / total_coins
        
        logger.debug(f"Calculated weighted spot ask: {weighted_avg_price} for {total_coins} coins ({total_cost} USDT)")
        
        return weighted_avg_price, total_coins, total_cost
    
    def calculate_weighted_futures_bid(self, bids: List[List[float]], target_coins: float) -> Tuple[float, float, float]:
        """
        Calculate weighted average bid price on futures market for a given coin amount
        
        Args:
            bids: List of [price, volume] pairs ordered by decreasing price
            target_coins: Target volume in coins
            
        Returns:
            Tuple of (weighted_avg_price, actual_volume_coins, actual_volume_usdt)
        """
        if not bids:
            return 0.0, 0.0, 0.0
        
        total_cost = 0.0
        total_coins = 0.0
        
        for price, coin_volume in bids:
            if total_coins + coin_volume <= target_coins:
                # Take entire level
                total_cost += price * coin_volume
                total_coins += coin_volume
            else:
                # Take partial level
                remaining_coins = target_coins - total_coins
                remaining_cost = remaining_coins * price
                total_cost += remaining_cost
                total_coins += remaining_coins
                break
                
        if total_coins == 0:
            return 0.0, 0.0, 0.0
            
        weighted_avg_price = total_cost / total_coins
        
        logger.debug(f"Calculated weighted futures bid: {weighted_avg_price} for {total_coins} coins ({total_cost} USDT)")
        
        return weighted_avg_price, total_coins, total_cost
    
    def calculate_weighted_spot_bid(self, bids: List[List[float]], target_coins: float) -> Tuple[float, float, float]:
        """
        Calculate weighted average bid price on spot market for a given coin amount
        
        Args:
            bids: List of [price, volume] pairs ordered by decreasing price
            target_coins: Target volume in coins
            
        Returns:
            Tuple of (weighted_avg_price, actual_volume_coins, actual_volume_usdt)
        """
        if not bids:
            return 0.0, 0.0, 0.0
        
        total_cost = 0.0
        total_coins = 0.0
        
        for price, coin_volume in bids:
            if total_coins + coin_volume <= target_coins:
                # Take entire level
                total_cost += price * coin_volume
                total_coins += coin_volume
            else:
                # Take partial level
                remaining_coins = target_coins - total_coins
                remaining_cost = remaining_coins * price
                total_cost += remaining_cost
                total_coins += remaining_coins
                break
                
        if total_coins == 0:
            return 0.0, 0.0, 0.0
            
        weighted_avg_price = total_cost / total_coins
        
        logger.debug(f"Calculated weighted spot bid: {weighted_avg_price} for {total_coins} coins ({total_cost} USDT)")
        
        return weighted_avg_price, total_coins, total_cost
    
    def calculate_weighted_futures_ask(self, asks: List[List[float]], target_coins: float) -> Tuple[float, float, float]:
        """
        Calculate weighted average ask price on futures market for a given coin amount
        
        Args:
            asks: List of [price, volume] pairs ordered by increasing price
            target_coins: Target volume in coins
            
        Returns:
            Tuple of (weighted_avg_price, actual_volume_coins, actual_volume_usdt)
        """
        if not asks:
            return 0.0, 0.0, 0.0
        
        total_cost = 0.0
        total_coins = 0.0
        
        for price, coin_volume in asks:
            if total_coins + coin_volume <= target_coins:
                # Take entire level
                total_cost += price * coin_volume
                total_coins += coin_volume
            else:
                # Take partial level
                remaining_coins = target_coins - total_coins
                remaining_cost = remaining_coins * price
                total_cost += remaining_cost
                total_coins += remaining_coins
                break
                
        if total_coins == 0:
            return 0.0, 0.0, 0.0
            
        weighted_avg_price = total_cost / total_coins
        
        logger.debug(f"Calculated weighted futures ask: {weighted_avg_price} for {total_coins} coins ({total_cost} USDT)")
        
        return weighted_avg_price, total_coins, total_cost
    
    def calculate_entry_spread(
        self, 
        spot_order_book: Dict, 
        futures_order_book: Dict, 
        target_volume_usdt: float = None
    ) -> Dict:
        """
        Calculate entry spread between spot and futures markets
        
        Args:
            spot_order_book: Spot market order book
            futures_order_book: Futures market order book
            target_volume_usdt: Target volume in USDT (defaults to self.lot_min)
            
        Returns:
            Dictionary with spread details
        """
        if target_volume_usdt is None:
            target_volume_usdt = self.lot_min
        
        # Get best prices
        spot_best_ask = spot_order_book['asks'][0][0]
        spot_best_bid = spot_order_book['bids'][0][0]
        futures_best_ask = futures_order_book['asks'][0][0]
        futures_best_bid = futures_order_book['bids'][0][0]
        
        # Calculate weighted average prices
        spot_weighted_ask, spot_coins, actual_spot_usdt = self.calculate_weighted_spot_ask(
            spot_order_book['asks'], target_volume_usdt
        )
        
        futures_weighted_bid, futures_coins, actual_futures_usdt = self.calculate_weighted_futures_bid(
            futures_order_book['bids'], spot_coins
        )
        
        # For exit spread calculation
        futures_weighted_ask, _, _ = self.calculate_weighted_futures_ask(
            futures_order_book['asks'], spot_coins
        )
        
        spot_weighted_bid, _, _ = self.calculate_weighted_spot_bid(
            spot_order_book['bids'], spot_coins
        )
        
        # Calculate entry spread
        entry_spread = (futures_weighted_bid - spot_weighted_ask) / spot_weighted_ask * 100
        
        # Calculate exit spread
        exit_spread = (spot_weighted_bid - futures_weighted_ask) / futures_weighted_ask * 100
        
        # Determine if there's a trade opportunity
        trade_opportunity = entry_spread > self.spread_in
        
        result = {
            'entry_spread': entry_spread,
            'exit_spread': exit_spread,
            'spot_best_ask': spot_best_ask,
            'spot_best_bid': spot_best_bid,
            'futures_best_ask': futures_best_ask,
            'futures_best_bid': futures_best_bid,
            'spot_weighted_ask': spot_weighted_ask,
            'futures_weighted_bid': futures_weighted_bid,
            'spot_weighted_bid': spot_weighted_bid,
            'futures_weighted_ask': futures_weighted_ask,
            'tradable_volume_coins': spot_coins,
            'tradable_volume_usdt': actual_spot_usdt,
            'trade_opportunity': trade_opportunity
        }
        
        logger.info(f"Entry spread: {entry_spread:.2f}%, Exit spread: {exit_spread:.2f}%, Trade opportunity: {trade_opportunity}")
        
        return result
    
    def calculate_exit_spread(
        self, 
        spot_order_book: Dict, 
        futures_order_book: Dict, 
        position_coins: float
    ) -> Dict:
        """
        Calculate exit spread for an existing position
        
        Args:
            spot_order_book: Spot market order book
            futures_order_book: Futures market order book
            position_coins: Size of the position in coins
            
        Returns:
            Dictionary with exit spread details
        """
        # Calculate weighted prices for the position size
        spot_weighted_bid, actual_spot_coins, actual_spot_usdt = self.calculate_weighted_spot_bid(
            spot_order_book['bids'], position_coins
        )
        
        futures_weighted_ask, actual_futures_coins, actual_futures_usdt = self.calculate_weighted_futures_ask(
            futures_order_book['asks'], position_coins
        )
        
        # Calculate exit spread
        exit_spread = (spot_weighted_bid - futures_weighted_ask) / futures_weighted_ask * 100
        
        # Determine if there's a close opportunity
        close_opportunity = exit_spread > self.spread_out
        
        result = {
            'exit_spread': exit_spread,
            'spot_weighted_bid': spot_weighted_bid,
            'futures_weighted_ask': futures_weighted_ask,
            'tradable_volume_coins': min(actual_spot_coins, actual_futures_coins),
            'spot_volume_usdt': actual_spot_usdt,
            'futures_volume_usdt': actual_futures_usdt,
            'close_opportunity': close_opportunity
        }
        
        logger.info(f"Exit spread: {exit_spread:.2f}%, Close opportunity: {close_opportunity}")
        
        return result
    
    def store_spread_data(
        self,
        spot_exchange: str,
        futures_exchange: str,
        symbol: str,
        spread_data: Dict
    ) -> None:
        """
        Store spread calculation results in the database
        
        Args:
            spot_exchange: Name of spot exchange
            futures_exchange: Name of futures exchange
            symbol: Trading pair symbol
            spread_data: Dictionary with spread calculation results
        """
        try:
            conn = self._connect_to_db()
            cursor = conn.cursor()
            
            # Execute the stored procedure
            cursor.execute(
                """
                SELECT insert_spread(
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    spot_exchange,
                    futures_exchange,
                    symbol,
                    spread_data['entry_spread'],
                    spread_data['exit_spread'],
                    spread_data['spot_best_ask'],
                    spread_data['spot_best_bid'],
                    spread_data['futures_best_ask'],
                    spread_data['futures_best_bid'],
                    spread_data['spot_weighted_ask'],
                    spread_data['futures_weighted_bid'],
                    spread_data['spot_weighted_bid'],
                    spread_data['futures_weighted_ask'],
                    spread_data['tradable_volume_coins'],
                    spread_data['tradable_volume_usdt'],
                    spread_data['trade_opportunity'],
                    spread_data['close_opportunity']
                )
            )
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("Spread data stored successfully")
        except Exception as e:
            logger.error(f"Error storing spread data: {str(e)}")
            if conn:
                conn.rollback()
                cursor.close()
                conn.close()
                logger.error("Database transaction rolled back")
                raise
        finally:
            if conn:
                conn.close()
                logger.debug("Database connection closed")
            else:
                logger.debug("No database connection to close")
        logger.info("Stored procedure executed successfully")
        logger.debug("Stored procedure executed successfully")

    
    def store_order_book_data(
        self,
        exchange: str,
        symbol: str,
        market_type: str,
        order_book: Dict
    ) -> None:
        """
        Store order book data in the database
        
        Args:
            exchange: Name of exchange
            symbol: Trading pair symbol
            market_type: 'spot' or 'futures'
            order_book: Order book data
        """
        try:
            # Extract and format order book data
            ask_prices = [price for price, _ in order_book['asks']]
            ask_volumes = [volume for _, volume in order_book['asks']]
            bid_prices = [price for price, _ in order_book['bids']]
            bid_volumes = [volume for _, volume in order_book['bids']]
            
            conn = self._connect_to_db()
            cursor = conn.cursor()
            
            # Execute the stored procedure
            cursor.execute(
                """
                SELECT insert_order_book(
                    %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    exchange,
                    symbol,
                    market_type,
                    json.dumps(ask_prices),
                    json.dumps(ask_volumes),
                    json.dumps(bid_prices),
                    json.dumps(bid_volumes)
                )
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Stored {market_type} order book data for {symbol} on {exchange}")
        except Exception as e:
            logger.error(f"Error storing order book data: {str(e)}")
            raise
            
    def get_historical_spreads(
        self,
        symbol: str,
        hours: int = 48,
        interval_minutes: int = 1
    ) -> pd.DataFrame:
        """
        Retrieve historical spread data for charting
        
        Args:
            symbol: Trading pair symbol
            hours: Number of hours of history to retrieve
            interval_minutes: Interval in minutes for aggregation
            
        Returns:
            DataFrame with historical spread data
        """
        try:
            conn = self._connect_to_db()
            
            query = f"""
            SELECT 
                time_bucket('{interval_minutes} minutes', timestamp) AS time,
                AVG(entry_spread) AS avg_entry_spread,
                AVG(exit_spread) AS avg_exit_spread,
                MAX(entry_spread) AS max_entry_spread,
                MIN(entry_spread) AS min_entry_spread,
                AVG(spot_best_ask) AS avg_spot_ask,
                AVG(futures_best_bid) AS avg_futures_bid
            FROM spreads
            WHERE 
                symbol = %s AND
                timestamp > NOW() - INTERVAL '%s hours'
            GROUP BY time
            ORDER BY time ASC
            """
            
            df = pd.read_sql(query, conn, params=(symbol, hours))
            conn.close()
            
            logger.info(f"Retrieved {len(df)} historical spread records for {symbol}")
            
            return df
        except Exception as e:
            logger.error(f"Error retrieving historical spreads: {str(e)}")
            raise
            
    def should_close_position(
        self,
        position_id: str,
        position_coins: float,
        spot_order_book: Dict,
        futures_order_book: Dict,
        min_trade_amount: float
    ) -> Tuple[bool, float, Dict]:
        """
        Determine if a position should be closed or partially closed
        
        Args:
            position_id: UUID of the position
            position_coins: Current position size in coins
            spot_order_book: Current spot order book
            futures_order_book: Current futures order book
            min_trade_amount: Minimum tradable amount in coins
            
        Returns:
            Tuple of (should_close, coins_to_close, exit_spread_data)
        """
        # Calculate exit spread
        exit_data = self.calculate_exit_spread(
            spot_order_book, futures_order_book, position_coins
        )
        
        if not exit_data['close_opportunity']:
            return False, 0.0, exit_data
            
        # Determine how many coins to close
        coins_to_close = min(
            position_coins,
            exit_data['tradable_volume_coins']
        )
        
        # Check if the remaining position would be below minimum
        if position_coins - coins_to_close < min_trade_amount:
            # Close the entire position
            coins_to_close = position_coins
            
        if coins_to_close <= 0:
            return False, 0.0, exit_data
            
        logger.info(f"Position {position_id} exit opportunity: close {coins_to_close} coins")
        
        return True, coins_to_close, exit_data
