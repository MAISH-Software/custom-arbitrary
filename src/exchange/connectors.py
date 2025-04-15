from venv import logger
import ccxt
from typing import Dict

class ExchangeConnector:
    def __init__(self, config):
        self.exchanges = {
            'coinex': ccxt.coinex(config.EXCHANGE_CREDS['coinex']),
            'gateio': ccxt.gateio(config.EXCHANGE_CREDS['gateio'])
        }
    
    def get_order_book(self, exchange: str, symbol: str) -> Dict:
        """Get normalized order book"""
        return self.exchanges[exchange].fetch_order_book(symbol)
    
    def execute_order(self, exchange: str, symbol: str, side: str, amount: float):
        """Execute trade with proper error handling"""
        try:
            return self.exchanges[exchange].create_order(
                symbol,
                'market',
                side,
                amount
            )
        except ccxt.InsufficientFunds as e:
            logger.error(f"Insufficient funds: {str(e)}")
            raise