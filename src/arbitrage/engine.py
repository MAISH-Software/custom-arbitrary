import os
import time
import uuid
import logging
import threading
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from datetime import datetime, timedelta
import pytz
import psycopg2
from psycopg2.extras import DictCursor
from dotenv import load_dotenv
import ccxt
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from config.settings import Config

# Import our custom modules
from src.exchange.connectors import ExchangeConnector
from src.arbitrage.calculator import SpreadCalculator

# Load environment variables
load_dotenv()

log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "arbitrage_engine.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("arbitrage_engine")

class ArbitrageEngine:
    def __init__(self, config_input: Union[str, Dict, Config] = "config.json"):
        """
        Initialize the arbitrage engine
        
        Args:
            config_path: Path to configuration file
        """
        if config_input is None:
            config_input = Config()
        self.config = self._load_config(config_input)
        self.exchange_connector = ExchangeConnector(self.config)
        self.spread_calculator = SpreadCalculator(
            db_connection_string=self.config.DB_URL,
            lot_min=self.config.TRADING_PARAMS['lot_min'],
            lot_max=self.config.TRADING_PARAMS['lot_max'],
            spread_in=self.config.TRADING_PARAMS['spread_in'],
            spread_out=self.config.TRADING_PARAMS['spread_out']
        )
        self.running = False
        self.monitor_thread = None
        
    def _load_config(self, config_input: Union[str, Dict, Config]):
        """Load configuration from JSON file"""
        if not isinstance(config_input, str):
            logger.info("Using provided configuration dictionary")
            return config_input
        
        try:
            with open(config_input, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded configuration from {config_input}")
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {str(e)}")
            raise 
    
    def _connect_to_db(self):
        """Connect to the PostgreSQL database"""
        try:
            conn = psycopg2.connect(self.config.DB_URL)
            return conn
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            raise
    
    def start_monitoring(self):
        """Start the monitoring thread"""
        if self.running:
            logger.warning("Monitoring is already running")
            return
            
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitor_thread.start()
        logger.info("Started arbitrage monitoring")
        
    
    def stop_monitoring(self):
        """Stop the monitoring thread"""
        if not self.running:
            logger.warning("Monitoring is not running")
            return
            
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=30)
        logger.info("Stopped arbitrage monitoring")
    
    def _monitoring_loop(self):
        """Main monitoring loop for arbitrage opportunities"""
        while self.running:
            try:
                self._check_arbitrage_opportunities()
                self._check_exit_opportunities()
                
                # Sleep for the configured interval
                time.sleep(self.config.MONITORING["check_interval_seconds"])
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(10)  # Sleep a bit longer on error
    
    def _check_arbitrage_opportunities(self):
        """Check for new arbitrage opportunities"""
        for pair_config in self.config.TRADING_PAIRS:
            symbol = pair_config['symbol']
            spot_exchange = pair_config['spot_exchange']
            futures_exchange = pair_config['futures_exchange']
            spot_symbol = pair_config['spot_symbol']
            futures_symbol = pair_config['futures_symbol']
            
            try:
                # Fetch order books
                spot_order_book = self.exchange_connector.get_order_book(
                    spot_exchange, spot_symbol
                )
                
                futures_order_book = self.exchange_connector.get_order_book(
                    futures_exchange, futures_symbol
                )
                
                # Store order book data
                self.spread_calculator.store_order_book_data(
                    spot_exchange, symbol, 'spot', spot_order_book
                )
                
                self.spread_calculator.store_order_book_data(
                    futures_exchange, symbol, 'futures', futures_order_book
                )
                
                # Calculate spread based on the entry condition formula:
                # (BID_fut - ASK_spot) / ASK_spot * 100% > Spred_IN
                spread_data = self.spread_calculator.calculate_entry_spread(
                    spot_order_book, futures_order_book
                )
                
                # Store spread data
                self.spread_calculator.store_spread_data(
                    spot_exchange, futures_exchange, symbol, spread_data
                )
                
                # Emit spread data to web interface if enabled
                if self.config.WEB_INTERFACE:
                    self.socketio.emit('spread_update', {
                        'symbol': symbol,
                        'entry_spread': spread_data['entry_spread'],
                        'exit_spread': spread_data['exit_spread'],
                        'timestamp': datetime.now().isoformat()
                    })
                
                # Check if there's a trade opportunity
                if spread_data['trade_opportunity']:
                    logger.info(f"Found arbitrage opportunity for {symbol}: {spread_data['entry_spread']:.2f}%")
                    
                    # Check if auto-trading is enabled
                    if self.config.TRADING_PARAMS['auto_trade']:
                        # Check if we already have an open position
                        if not self._has_open_position(symbol):
                            # Execute the trade
                            self._execute_arbitrage_trade(
                                symbol, spot_exchange, futures_exchange,
                                spot_symbol, futures_symbol, spread_data
                            )
                        else:
                            # Check if we can increase the position
                            self._check_position_increase(
                                symbol, spot_exchange, futures_exchange,
                                spot_symbol, futures_symbol, spread_data
                            )
                    
                    # Send notification
                    self._send_notification(
                        f"Arbitrage opportunity for {symbol}: {spread_data['entry_spread']:.2f}%"
                    )
                
            except Exception as e:
                logger.error(f"Error checking arbitrage for {symbol}: {str(e)}")
    
    def _check_exit_opportunities(self):
        """Check for exit opportunities on open positions"""
        try:
            # Get all open positions
            conn = self._connect_to_db()
            cursor = conn.cursor(cursor_factory=DictCursor)
            
            cursor.execute(
                """
                SELECT * FROM positions
                WHERE status IN ('open', 'partially_closed')
                """
            )
            
            positions = cursor.fetchall()
            cursor.close()
            conn.close()
            
            for position in positions:
                symbol = position['symbol']
                position_id = position['position_id']
                remaining_coins = position['remaining_spot_coins']
                spot_exchange = position['spot_exchange']
                futures_exchange = position['futures_exchange']
                
                # Find the corresponding pair config
                pair_config = next(
                    (p for p in self.config.TRADING_PAIRS if p['symbol'] == symbol),
                    None
                )
                
                if not pair_config:
                    logger.warning(f"No configuration found for symbol {symbol}")
                    continue
                
                spot_symbol = pair_config['spot_symbol']
                futures_symbol = pair_config['futures_symbol']
                
                # Fetch order books
                spot_order_book = self.exchange_connector.get_order_book(
                    spot_exchange, spot_symbol
                )
                
                futures_order_book = self.exchange_connector.get_order_book(
                    futures_exchange, futures_symbol
                )
                
                # Get minimum trade amount
                min_trade_amount = self.exchange_connector.get_min_trade_amount(
                    spot_exchange, spot_symbol
                )
                
                # Calculate exit spread based on the exit condition formula:
                # (BID_spot - ASK_fut) / ASK_fut * 100% > Spred_OUT
                exit_data = self.spread_calculator.calculate_exit_spread(
                    spot_order_book, futures_order_book
                )
                
                # Check if we should close the position
                should_close, coins_to_close = self.spread_calculator.should_close_position(
                    position_id, remaining_coins, exit_data, min_trade_amount
                )
                
                if should_close:
                    logger.info(f"Found exit opportunity for position {position_id}: {exit_data['exit_spread']:.2f}%")
                    
                    # Check if auto-trading is enabled
                    if self.config.TRADING_PARAMS['auto_trade']:
                        # Execute the exit trade
                        self._execute_exit_trade(
                            position_id, coins_to_close, spot_exchange, futures_exchange,
                            spot_symbol, futures_symbol, exit_data
                        )
                    
                    # Send notification
                    self._send_notification(
                        f"Exit opportunity for {symbol} position {position_id}: {exit_data['exit_spread']:.2f}%"
                    )
        
        except Exception as e:
            logger.error(f"Error checking exit opportunities: {str(e)}")
    
    def _has_open_position(self, symbol: str) -> bool:
        """Check if there's already an open position for the given symbol"""
        try:
            conn = self._connect_to_db()
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT COUNT(*) FROM positions
                WHERE symbol = %s AND status IN ('open', 'partially_closed')
                """,
                (symbol,)
            )
            
            count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            
            return count > 0
        except Exception as e:
            logger.error(f"Error checking for open positions: {str(e)}")
            return False
    
    def _check_position_increase(
        self,
        symbol: str,
        spot_exchange: str,
        futures_exchange: str,
        spot_symbol: str,
        futures_symbol: str,
        spread_data: Dict
    ):
        """Check if we can increase an existing position"""
        try:
            conn = self._connect_to_db()
            cursor = conn.cursor(cursor_factory=DictCursor)
            
            cursor.execute(
                """
                SELECT * FROM positions
                WHERE symbol = %s AND status IN ('open', 'partially_closed')
                """,
                (symbol,)
            )
            
            position = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if not position:
                return
                
            # Check if the total position size is already at the maximum
            current_volume_usdt = position['spot_volume_usdt']
            
            if current_volume_usdt >= self.config.TRADING_PARAMS['lot_max']:
                logger.info(f"Position for {symbol} already at maximum size")
                return
                
            # Calculate how much more we can add
            remaining_volume = self.config.TRADING_PARAMS['lot_max'] - current_volume_usdt
            
            # If we can add at least lot_min more, execute the trade
            if remaining_volume >= self.config.TRADING_PARAMS['lot_min']:
                logger.info(f"Increasing position for {symbol} by {remaining_volume} USDT")
                
                # Recalculate spread for the remaining volume
                spread_data = self.spread_calculator.calculate_entry_spread(
                    self.exchange_connector.get_order_book(spot_exchange, spot_symbol),
                    self.exchange_connector.get_order_book(futures_exchange, futures_symbol),
                    remaining_volume
                )
                
                if spread_data['trade_opportunity']:
                    # Execute additional trade to increase position
                    self._execute_arbitrage_trade(
                        symbol, spot_exchange, futures_exchange,
                        spot_symbol, futures_symbol, spread_data,
                        position_id=position['position_id']
                    )
                else:
                    logger.info(f"Spread no longer favorable for increasing position for {symbol}")
            
        except Exception as e:
            logger.error(f"Error checking position increase: {str(e)}")
    
    def _execute_arbitrage_trade(
        self,
        symbol: str,
        spot_exchange: str,
        futures_exchange: str,
        spot_symbol: str,
        futures_symbol: str,
        spread_data: Dict,
        position_id: str = None
    ):
        """Execute an arbitrage trade (entry)"""
        try:
            # Generate a position ID if this is a new position
            if position_id is None:
                position_id = str(uuid.uuid4())
                
            # Get the volume to trade
            spot_volume_coins = spread_data['tradable_volume_coins']
            spot_avg_price = spread_data['spot_weighted_ask']
            futures_avg_price = spread_data['futures_weighted_bid']
            
            # Execute spot buy
            spot_order = self.exchange_connector.execute_spot_buy(
                spot_exchange, spot_symbol, spot_volume_coins, spot_avg_price
            )
            
            # Execute futures sell
            futures_order = self.exchange_connector.execute_futures_sell(
                futures_exchange, futures_symbol, spot_volume_coins, futures_avg_price
            )
            
            # Calculate volumes in USDT
            spot_volume_usdt = spot_volume_coins * spot_avg_price
            futures_volume_usdt = spot_volume_coins * futures_avg_price
            
            # Store the position in the database
            conn = self._connect_to_db()
            cursor = conn.cursor()
            
            if position_id is None:
                # New position
                cursor.execute(
                    """
                    INSERT INTO positions (
                        position_id, status, spot_exchange, futures_exchange, symbol,
                        initial_entry_spread, spot_volume_coins, futures_volume_coins,
                        spot_volume_usdt, futures_volume_usdt, spot_avg_price, futures_avg_price,
                        remaining_spot_coins, remaining_futures_coins, spot_orders, futures_orders
                    ) VALUES (
                        %s, 'open', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        position_id, spot_exchange, futures_exchange, symbol,
                        spread_data['entry_spread'], spot_volume_coins, spot_volume_coins,
                        spot_volume_usdt, futures_volume_usdt, spot_avg_price, futures_avg_price,
                        spot_volume_coins, spot_volume_coins, 
                        json.dumps([spot_order['id']]), json.dumps([futures_order['id']])
                    )
                )
            else:
                # Update existing position
                cursor.execute(
                    """
                    UPDATE positions SET
                        spot_volume_coins = spot_volume_coins + %s,
                        futures_volume_coins = futures_volume_coins + %s,
                        spot_volume_usdt = spot_volume_usdt + %s,
                        futures_volume_usdt = futures_volume_usdt + %s,
                        remaining_spot_coins = remaining_spot_coins + %s,
                        remaining_futures_coins = remaining_futures_coins + %s,
                        spot_orders = spot_orders || %s::jsonb,
                        futures_orders = futures_orders || %s::jsonb
                    WHERE position_id = %s
                    """,
                    (
                        spot_volume_coins, spot_volume_coins,
                        spot_volume_usdt, futures_volume_usdt,
                        spot_volume_coins, spot_volume_coins,
                        json.dumps([spot_order['id']]), json.dumps([futures_order['id']]),
                        position_id
                    )
                )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Executed arbitrage trade for {symbol}: {spot_volume_coins} coins, {spot_volume_usdt} USDT")
            
            # Send notification
            self._send_notification(
                f"Executed arbitrage trade for {symbol}: {spot_volume_coins} coins, {spot_volume_usdt:.2f} USDT"
            )
            
            # Emit to web interface if enabled
            if self.config.WEB_INTERFACE:
                self.socketio.emit('trade_executed', {
                    'type': 'entry',
                    'symbol': symbol,
                    'position_id': position_id,
                    'volume_coins': spot_volume_coins,
                    'volume_usdt': spot_volume_usdt,
                    'entry_spread': spread_data['entry_spread'],
                    'timestamp': datetime.now().isoformat()
                })
            
        except Exception as e:
            logger.error(f"Error executing arbitrage trade: {str(e)}")
            
            # Send error notification
            self._send_notification(
                f"Error executing arbitrage trade for {symbol}: {str(e)}"
            )
    
    def _execute_exit_trade(
        self,
        position_id: str,
        coins_to_close: float,
        spot_exchange: str,
        futures_exchange: str,
        spot_symbol: str,
        futures_symbol: str,
        exit_data: Dict
    ):
        """Execute an exit trade"""
        try:
            # Get the current position
            conn = self._connect_to_db()
            cursor = conn.cursor(cursor_factory=DictCursor)
            
            cursor.execute(
                """
                SELECT * FROM positions
                WHERE position_id = %s
                """,
                (position_id,)
            )
            
            position = cursor.fetchone()
            
            if not position:
                logger.error(f"Position {position_id} not found")
                return
            
            # Get prices for exit trade
            spot_avg_price = exit_data['spot_weighted_bid']
            futures_avg_price = exit_data['futures_weighted_ask']
            
            # Execute spot sell
            spot_order = self.exchange_connector.execute_spot_sell(
                spot_exchange, spot_symbol, coins_to_close, spot_avg_price
            )
            
            # Execute futures buy
            futures_order = self.exchange_connector.execute_futures_buy(
                futures_exchange, futures_symbol, coins_to_close, futures_avg_price
            )
            
            # Calculate volumes in USDT
            spot_close_usdt = coins_to_close * spot_avg_price
            futures_close_usdt = coins_to_close * futures_avg_price
            
            # Calculate PnL
            initial_spot_cost = (position['spot_volume_usdt'] / position['spot_volume_coins']) * coins_to_close
            initial_futures_value = (position['futures_volume_usdt'] / position['futures_volume_coins']) * coins_to_close
            
            pnl = (spot_close_usdt - initial_spot_cost) + (initial_futures_value - futures_close_usdt)
            
            # Update the position in the database
            remaining_spot_coins = position['remaining_spot_coins'] - coins_to_close
            remaining_futures_coins = position['remaining_futures_coins'] - coins_to_close
            
            status = 'closed' if remaining_spot_coins <= 0 else 'partially_closed'
            
            cursor.execute(
                """
                UPDATE positions SET
                    status = %s,
                    remaining_spot_coins = %s,
                    remaining_futures_coins = %s,
                    close_timestamp = CASE WHEN %s = 'closed' THEN NOW() ELSE close_timestamp END,
                    pnl_usdt = COALESCE(pnl_usdt, 0) + %s
                WHERE position_id = %s
                """,
                (
                    status, remaining_spot_coins, remaining_futures_coins,
                    status, pnl, position_id
                )
            )
            
            # Record the position adjustment
            cursor.execute(
                """
                INSERT INTO position_adjustments (
                    position_id, adjustment_type, exit_spread, spot_volume_coins,
                    futures_volume_coins, spot_price, futures_price, pnl_usdt,
                    spot_order_id, futures_order_id
                ) VALUES (
                    %s, 'partial_close', %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    position_id, exit_data['exit_spread'], coins_to_close,
                    coins_to_close, spot_avg_price, futures_avg_price, pnl,
                    spot_order['id'], futures_order['id']
                )
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Executed exit trade for position {position_id}: {coins_to_close} coins, PnL: {pnl:.2f} USDT")
            
            # Send notification
            self._send_notification(
                f"Executed exit trade for {position['symbol']}: {coins_to_close} coins, PnL: {pnl:.2f} USDT"
            )
            
            # Emit to web interface if enabled
            if self.config.WEB_INTERFACE:
                self.socketio.emit('trade_executed', {
                    'type': 'exit',
                    'symbol': position['symbol'],
                    'position_id': position_id,
                    'volume_coins': coins_to_close,
                    'pnl': pnl,
                    'exit_spread': exit_data['exit_spread'],
                    'status': status,
                    'timestamp': datetime.now().isoformat()
                })
            
        except Exception as e:
            logger.error(f"Error executing exit trade: {str(e)}")
            
            # Send error notification
            self._send_notification(
                f"Error executing exit trade for position {position_id}: {str(e)}"
            )
    
    def _send_notification(self, message: str):
        """Send a notification message"""
        if not self.config.NOTIFICATIONS:
            return
            
        notification_type = self.config.NOTIFICATIONS
        
        if notification_type == 'telegram':
            self._send_telegram_notification(message)
        elif notification_type == 'sms':
            self._send_sms_notification(message)
        else:
            logger.warning(f"Unknown notification type: {notification_type}")
    
    def _send_telegram_notification(self, message: str):
        """Send a notification via Telegram"""
        try:
            import telegram
            
            bot_token = self.config.NOTIFICATIONS['telegram']['bot_token']
            chat_id = self.config.NOTIFICATIONS['telegram']['chat_id']
            
            bot = telegram.Bot(token=bot_token)
            bot.send_message(chat_id=chat_id, text=message)
            
            logger.info(f"Sent Telegram notification: {message}")
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {str(e)}")
    
    def _send_sms_notification(self, message: str):
        """Send a notification via SMS"""
        try:
            from twilio.rest import Client
            
            account_sid = self.config.NOTIFICATIONS['twilio']['account_sid']
            auth_token = self.config.NOTIFICATIONS['twilio']['auth_token']
            from_number = self.config.NOTIFICATIONS['twilio']['from_number']
            to_number = self.config.NOTIFICATIONS['twilio']['to_number']
            
            client = Client(account_sid, auth_token)
            client.messages.create(
                body=message,
                from_=from_number,
                to=to_number
            )
            
            logger.info(f"Sent SMS notification: {message}")
        except Exception as e:
            logger.error(f"Error sending SMS notification: {str(e)}")
    
    def get_position_details(self, position_id: str) -> Tuple[Dict, List[Dict]]:
        """Get details for a specific position, including adjustments"""
        try:
            conn = self._connect_to_db()
            cursor = conn.cursor(cursor_factory=DictCursor)
            
            # Get position details
            cursor.execute(
                """
                SELECT * FROM positions
                WHERE position_id = %s
                """,
                (position_id,)
            )
            
            position = cursor.fetchone()
            
            if not position:
                logger.warning(f"Position {position_id} not found")
                return None, []
            
            position_dict = dict(position)
            
            # Get all adjustments for this position
            cursor.execute(
                """
                SELECT * FROM position_adjustments
                WHERE position_id = %s
                ORDER BY created_at ASC
                """,
                (position_id,)
            )
            
            adjustments = [dict(adj) for adj in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            
            return position_dict, adjustments
        except Exception as e:
            logger.error(f"Error getting position details: {str(e)}")
            return None, []
    
    def get_open_positions(self) -> List[Dict]:
        """Get list of all open positions"""
        try:
            conn = self._connect_to_db()
            cursor = conn.cursor(cursor_factory=DictCursor)
            
            cursor.execute(
                """
                SELECT * FROM positions
                WHERE status IN ('open', 'partially_closed')
                """
            )
            
            positions = [dict(position) for position in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            return positions
        except Exception as e:
            logger.error(f"Error getting open positions: {str(e)}")
            return []
    
    def get_closed_positions(self, days: int = 7) -> List[Dict]:
        """Get list of closed positions within the specified number of days"""
        try:
            conn = self._connect_to_db()
            cursor = conn.cursor(cursor_factory=DictCursor)
            
            cursor.execute(
                """
                SELECT * FROM positions
                WHERE status = 'closed'
                AND close_timestamp > NOW() - INTERVAL %s DAY
                ORDER BY close_timestamp DESC
                """,
                (days,)
            )
            
            positions = [dict(position) for position in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            return positions
        except Exception as e:
            logger.error(f"Error getting closed positions: {str(e)}")
            return []
    
    def get_current_spreads(self) -> List[Dict]:
        """Get current spreads for all configured trading pairs"""
        try:
            spreads = []
            
            for pair_config in self.config.TRADING_PAIRS:
                symbol = pair_config['symbol']
                spot_exchange = pair_config['spot_exchange']
                futures_exchange = pair_config['futures_exchange']
                spot_symbol = pair_config['spot_symbol']
                futures_symbol = pair_config['futures_symbol']
                
                # Fetch latest order books
                spot_order_book = self.exchange_connector.get_order_book(
                    spot_exchange, spot_symbol
                )
                
                futures_order_book = self.exchange_connector.get_order_book(
                    futures_exchange, futures_symbol
                )
                
                # Calculate entry spread (BID_fut - ASK_spot) / ASK_spot * 100%
                entry_spread_data = self.spread_calculator.calculate_entry_spread(
                    spot_order_book, futures_order_book
                )

                # Calculate exit spread with a default position size
                spot_best_ask = float(spot_order_book['asks'][0][0])  # Convert to float
                default_position_coins = self.config.TRADING_PARAMS['lot_min'] / spot_best_ask
                
                # Calculate exit spread (BID_spot - ASK_fut) / ASK_fut * 100%
                exit_spread_data = self.spread_calculator.calculate_exit_spread(
                    spot_order_book, futures_order_book, default_position_coins
                )
                
                spreads.append({
                    'symbol': symbol,
                    'spot_exchange': spot_exchange,
                    'futures_exchange': futures_exchange,
                    'entry_spread': entry_spread_data['entry_spread'],
                    'exit_spread': exit_spread_data['exit_spread'],
                    'entry_opportunity': entry_spread_data['trade_opportunity'],
                    'exit_opportunity': exit_spread_data['close_opportunity'],
                    'tradable_volume': entry_spread_data['tradable_volume_coins'],
                    'timestamp': datetime.now(pytz.UTC)
                })

            logger.info(f"Current spreads: {spreads}")
            
            return spreads
        except Exception as e:
            logger.error(f"Error getting current spreads: {str(e)}")
            return []
    
    def get_spread_history(self, symbol: str, hours: int = 48) -> List[Dict]:
        """Get the spread history for a specific symbol for up to 48 hours"""
        try:
            conn = self._connect_to_db()
            cursor = conn.cursor(cursor_factory=DictCursor)
            
            cursor.execute(
                """
                SELECT * FROM spreads
                WHERE symbol = %s
                AND timestamp > NOW() - INTERVAL %s
                ORDER BY timestamp ASC
                """,
                (symbol, f"{hours} hours")
            )
            
            history = [dict(record) for record in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            return history
        except Exception as e:
            logger.error(f"Error getting spread history: {str(e)}")
            return []
    
    def generate_spread_chart(self, symbol: str, hours: int = 48, chart_type: str = 'plotly'):
        """Generate a spread chart for the given symbol"""
        try:
            # Get spread history
            spread_history = self.get_spread_history(symbol, hours)
        
            if not spread_history:
                logger.warning(f"No spread history found for {symbol}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(spread_history)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
            if chart_type == 'plotly':
                # Create plotly chart
                fig = go.Figure()
            
                # Add entry spread line
                fig.add_trace(go.Scatter(
                    x=df['timestamp'],
                    y=df['entry_spread'],
                    mode='lines',
                    name='Entry Spread',
                    line=dict(color='green', width=2)
                ))
            
                # Add exit spread line
                fig.add_trace(go.Scatter(
                    x=df['timestamp'],
                    y=df['exit_spread'],
                    mode='lines',
                    name='Exit Spread',
                    line=dict(color='red', width=2)
                ))
            
                # Add threshold lines
                fig.add_shape(
                    type="line",
                    x0=df['timestamp'].min(),
                    y0=self.config.TRADING_PARAMS['spread_in'],
                    x1=df['timestamp'].max(),
                    y1=self.config.TRADING_PARAMS['spread_in'],
                    line=dict(color="green", width=1, dash="dash"),
                    name="Entry Threshold"
                )
            
                fig.add_shape(
                    type="line",
                    x0=df['timestamp'].min(),
                    y0=self.config.TRADING_PARAMS['spread_out'],
                    x1=df['timestamp'].max(),
                    y1=self.config.TRADING_PARAMS['spread_out'],
                    line=dict(color="red", width=1, dash="dash"),
                    name="Exit Threshold"
                )
            
                # Add trades (if any)
                conn = self._connect_to_db()
                cursor = conn.cursor(cursor_factory=DictCursor)
            
                # Get entries
                cursor.execute(
                    """
                    SELECT position_id, created_at, initial_entry_spread
                    FROM positions
                    WHERE symbol = %s AND created_at > NOW() - INTERVAL %s HOUR
                    """,
                    (symbol, hours)
                )
            
                entries = cursor.fetchall()
            
                # Get exits
                cursor.execute(
                    """
                    SELECT position_id, created_at, exit_spread
                    FROM position_adjustments
                    WHERE position_id IN (
                        SELECT position_id FROM positions WHERE symbol = %s
                    ) AND created_at > NOW() - INTERVAL %s HOUR
                    """,
                    (symbol, hours)
                )
            
                exits = cursor.fetchall()
                cursor.close()
                conn.close()
            
                # Plot entries and exits
                for entry in entries:
                    fig.add_trace(go.Scatter(
                        x=[entry['created_at']],
                        y=[entry['initial_entry_spread']],
                        mode='markers',
                        marker=dict(symbol='triangle-up', size=12, color='green'),
                        name=f'Entry {entry["position_id"][-6:]}',
                        showlegend=False
                    ))
            
                for exit in exits:
                    fig.add_trace(go.Scatter(
                        x=[exit['created_at']],
                        y=[exit['exit_spread']],
                        mode='markers',
                        marker=dict(symbol='triangle-down', size=12, color='red'),
                        name=f'Exit {exit["position_id"][-6:]}',
                        showlegend=False
                    ))
            
                # Update layout
                fig.update_layout(
                    title=f'{symbol} Spot-Futures Spread History ({hours}h)',
                    xaxis_title='Time',
                    yaxis_title='Spread (%)',
                    template='plotly_white',
                    hovermode='x unified',
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    )
                )
            
                return fig
            
            elif chart_type == 'matplotlib':
                # Create matplotlib chart
                plt.figure(figsize=(12, 6))
            
                # Plot entry and exit spreads
                plt.plot(df['timestamp'], df['entry_spread'], 'g-', label='Entry Spread')
                plt.plot(df['timestamp'], df['exit_spread'], 'r-', label='Exit Spread')
            
                # Add threshold lines
                plt.axhline(y=self.config.TRADING_PARAMS['spread_in'], color='g', linestyle='--', label='Entry Threshold')
                plt.axhline(y=self.config.TRADING_PARAMS['spread_out'], color='r', linestyle='--', label='Exit Threshold')
            
                # Format plot
                plt.title(f'{symbol} Spot-Futures Spread History ({hours}h)')
                plt.xlabel('Time')
                plt.ylabel('Spread (%)')
                plt.grid(True, alpha=0.3)
                plt.legend()
                plt.tight_layout()
            
                return plt
        
            else:
                logger.warning(f"Unknown chart type: {chart_type}")
                return None
            
        except Exception as e:
            logger.error(f"Error generating spread chart: {str(e)}")
            return None
        
    def execute_manual_entry_trade(self, symbol: str, volume_coins: float):
        """Execute a manual entry trade"""
        try:
            # Find the pair config
            pair_config = next(
                (p for p in self.config.TRADING_PAIRS if p['symbol'] == symbol),
                None
            )
            
            if not pair_config:
                logger.warning(f"No configuration found for symbol {symbol}")
                return
            
            spot_exchange = pair_config['spot_exchange']
            futures_exchange = pair_config['futures_exchange']
            spot_symbol = pair_config['spot_symbol']
            futures_symbol = pair_config['futures_symbol']
            
            # Fetch order books
            spot_order_book = self.exchange_connector.get_order_book(
                spot_exchange, spot_symbol
            )
            
            futures_order_book = self.exchange_connector.get_order_book(
                futures_exchange, futures_symbol
            )
            
            # Calculate entry spread
            entry_data = self.spread_calculator.calculate_entry_spread(
                spot_order_book, futures_order_book, volume_coins
            )
            
            # Execute the trade
            self._execute_arbitrage_trade(
                symbol, spot_exchange, futures_exchange,
                spot_symbol, futures_symbol, entry_data
            )
        
        except Exception as e:
            logger.error(f"Error executing manual entry trade: {str(e)}")

    def execute_manual_exit_trade(self, position_id: str, volume_coins: float):
        """Execute a manual exit trade"""
        try:
            # Get the position details
            position, adjustments = self.get_position_details(position_id)
            
            if not position:
                logger.warning(f"No position found with ID {position_id}")
                return
            
            # Find the pair config
            pair_config = next(
                (p for p in self.config.TRADING_PAIRS if p['symbol'] == position['symbol']),
                None
            )
            
            if not pair_config:
                logger.warning(f"No configuration found for symbol {position['symbol']}")
                return
            
            spot_exchange = pair_config['spot_exchange']
            futures_exchange = pair_config['futures_exchange']
            spot_symbol = pair_config['spot_symbol']
            futures_symbol = pair_config['futures_symbol']
            
            # Fetch order books
            spot_order_book = self.exchange_connector.get_order_book(
                spot_exchange, spot_symbol
            )
            
            futures_order_book = self.exchange_connector.get_order_book(
                futures_exchange, futures_symbol
            )
            
            # Calculate exit spread
            exit_data = self.spread_calculator.calculate_exit_spread(
                spot_order_book, futures_order_book, volume_coins
            )
            
            # Execute the exit trade
            self._execute_exit_trade(
                position_id, volume_coins, spot_exchange, futures_exchange,
                spot_symbol, futures_symbol, exit_data
            )
        
        except Exception as e:
            logger.error(f"Error executing manual exit trade: {str(e)}")

