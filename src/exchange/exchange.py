import ccxt
import logging
import time
from typing import Dict, List, Tuple, Optional
import os

from config.settings import COINEX_ACCESS_ID, COINEX_SECRET_KEY, GATEIO_ACCESS_ID, GATEIO_SECRET_KEY, SPRED_IN, SPRED_OUT


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("exchange_connector.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("exchange_connector")



class ExchangeConnector:
    def __init__(self, config):
        # Initialize exchange connections
        self.exchanges = {
            'coinex': self._init_coinex(),
            'gateio': self._init_gateio(),
        }
        self.config = config
        
    def _init_coinex(self) -> ccxt.coinex:
        """Initialize connection to Coinex exchange"""
        try:
            exchange = ccxt.coinex({
                'apiKey': COINEX_ACCESS_ID,
                'secret': COINEX_SECRET_KEY,
                'enableRateLimit': True,
            })
            logger.info("Successfully initialized Coinex connection")
            return exchange
        except Exception as e:
            logger.error(f"Failed to initialize Coinex connection: {str(e)}")
            raise
    
    def _init_gateio(self) -> ccxt.gateio:
        """Initialize connection to Gate.io exchange"""
        try:
            exchange = ccxt.gateio({
                'apiKey': GATEIO_ACCESS_ID,
                'secret': GATEIO_SECRET_KEY,
                'enableRateLimit': True,
            })
            logger.info("Successfully initialized Gate.io connection")
            return exchange
        except Exception as e:
            logger.error(f"Failed to initialize Gate.io connection: {str(e)}")
            raise
    
    def get_spot_order_book(self, exchange_id: str, symbol: str, limit: int = 100) -> Dict:
        """
        Fetch spot market order book from specified exchange
        
        Args:
            exchange_id: String identifier for exchange ('coinex' or 'gateio')
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            limit: Order book depth
            
        Returns:
            Dictionary containing order book data
        """
        try:
            exchange = self.exchanges.get(exchange_id.lower())
            if not exchange:
                raise ValueError(f"Exchange {exchange_id} not supported")
            
            order_book = exchange.fetch_order_book(symbol, limit)
            logger.info(f"Fetched spot order book for {symbol} from {exchange_id}")
            return order_book
        except Exception as e:
            logger.error(f"Error fetching spot order book for {symbol} from {exchange_id}: {str(e)}")
            raise
    
    def get_futures_order_book(self, exchange_id: str, symbol: str, limit: int = 100) -> Dict:
        """
        Fetch futures market order book from specified exchange
        
        Args:
            exchange_id: String identifier for exchange ('coinex' or 'gateio')
            symbol: Trading pair symbol (e.g., 'BTC/USDT:USDT')
            limit: Order book depth
            
        Returns:
            Dictionary containing order book data
        """
        try:
            exchange = self.exchanges.get(exchange_id.lower())
            if not exchange:
                raise ValueError(f"Exchange {exchange_id} not supported")
            
            # Load futures markets if not already loaded
            if not exchange.has['fetchOrderBook']:
                raise NotImplementedError(f"{exchange_id} does not support order book fetching")
            
            # Make sure we're using the futures markets
            exchange.options['defaultType'] = 'future'
            
            order_book = exchange.fetch_order_book(symbol, limit)
            
            # Reset to default market type
            exchange.options['defaultType'] = 'spot'
            
            logger.info(f"Fetched futures order book for {symbol} from {exchange_id}")
            return order_book
        except Exception as e:
            logger.error(f"Error fetching futures order book for {symbol} from {exchange_id}: {str(e)}")
            raise
    
    def get_min_trade_amount(self, exchange_id: str, symbol: str, market_type: str = 'spot') -> float:
        """
        Get minimum trade amount for a symbol on an exchange
        
        Args:
            exchange_id: String identifier for exchange ('coinex' or 'gateio')
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            market_type: 'spot' or 'future'
            
        Returns:
            Minimum trade amount as float
        """
        try:
            exchange = self.exchanges.get(exchange_id.lower())
            if not exchange:
                raise ValueError(f"Exchange {exchange_id} not supported")
            
            # Set market type
            if market_type.lower() == 'future':
                exchange.options['defaultType'] = 'future'
            else:
                exchange.options['defaultType'] = 'spot'
            
            # Load markets if not already loaded
            if not exchange.markets:
                exchange.load_markets()
            
            # Get market info
            market = exchange.market(symbol)
            
            # Reset market type
            exchange.options['defaultType'] = 'spot'
            
            # Extract minimum amount
            min_amount = market.get('limits', {}).get('amount', {}).get('min', 0)
            logger.info(f"Minimum trade amount for {symbol} on {exchange_id} ({market_type}): {min_amount}")
            return min_amount
        except Exception as e:
            logger.error(f"Error getting minimum trade amount for {symbol} on {exchange_id}: {str(e)}")
            raise

    def execute_spot_buy(self, exchange_id: str, symbol: str, amount: float, price: float) -> Dict:
        """Execute a spot buy order"""
        try:
            exchange = self.exchanges.get(exchange_id.lower())
            if not exchange:
                raise ValueError(f"Exchange {exchange_id} not supported")
            
            response = exchange.create_limit_buy_order(symbol, amount, price)
            logger.info(f"Executed spot buy order for {amount} {symbol} at {price} on {exchange_id}")
            return response
        except Exception as e:
            logger.error(f"Error executing spot buy for {symbol} on {exchange_id}: {str(e)}")
            raise
    
    def execute_futures_sell(self, exchange_id: str, symbol: str, amount: float, price: float) -> Dict:
        """Execute a futures sell order"""
        try:
            exchange = self.exchanges.get(exchange_id.lower())
            if not exchange:
                raise ValueError(f"Exchange {exchange_id} not supported")
            
            # Set market type to futures
            exchange.options['defaultType'] = 'future'
            
            response = exchange.create_limit_sell_order(symbol, amount, price)
            
            # Reset market type
            exchange.options['defaultType'] = 'spot'
            
            logger.info(f"Executed futures sell order for {amount} {symbol} at {price} on {exchange_id}")
            return response
        except Exception as e:
            logger.error(f"Error executing futures sell for {symbol} on {exchange_id}: {str(e)}")
            raise

# Example usage
if __name__ == "__main__":
    connector = ExchangeConnector()
    
    # Example: fetch BTC/USDT order books from both exchanges
    spot_symbol = "BTC/USDT"
    futures_symbol = "BTC/USDT:USDT"  # Format may vary by exchange
    
    # Fetch order books
    coinex_spot_book = connector.get_spot_order_book("coinex", spot_symbol)
    gateio_spot_book = connector.get_spot_order_book("gateio", spot_symbol)
    
    coinex_futures_book = connector.get_futures_order_book("coinex", futures_symbol)
    gateio_futures_book = connector.get_futures_order_book("gateio", futures_symbol)
    
    # Print some example data
    print(f"Coinex BTC/USDT Spot Best Ask: {coinex_spot_book['asks'][0][0]}")
    print(f"Coinex BTC/USDT Spot Best Bid: {coinex_spot_book['bids'][0][0]}")
    
    print(f"Gate.io BTC/USDT Spot Best Ask: {gateio_spot_book['asks'][0][0]}")
    print(f"Gate.io BTC/USDT Spot Best Bid: {gateio_spot_book['bids'][0][0]}")