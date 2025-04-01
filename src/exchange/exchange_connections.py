import ccxt
from config import COINEX_ACCESS_ID, COINEX_SECRET_KEY, GATEIO_ACCESS_ID, GATEIO_SECRET_KEY

# Coinex connection (Spot market)
coinex = ccxt.coinex({
    'apiKey': COINEX_ACCESS_ID,
    'secret': COINEX_SECRET_KEY,
    'enableRateLimit': True,
})

# Gate.io connection (Futures market)
gateio = ccxt.gateio({
    'apiKey': GATEIO_ACCESS_ID,
    'secret': GATEIO_SECRET_KEY,
    'enableRateLimit': True,
})

def get_coinex_spot_orderbook(symbol='BTC/USDT'):
    """Fetch the order book for BTC/USDT on Coinex spot market"""
    return coinex.fetch_order_book(symbol)

def get_gateio_futures_orderbook(symbol='BTC_USD'):
    """Fetch the order book for BTC_USD on Gate.io futures market"""
    return gateio.fetch_order_book(symbol, params={'settle': 'usdt'})


def calculate_entry_spread(coinex_orderbook, gateio_orderbook):
    """Calculate entry spread: (BID_futures - ASK_spot) / ASK_spot * 100"""
    spot_ask = coinex_orderbook['asks'][0][0]    # Best ask price on spot
    futures_bid = gateio_orderbook['bids'][0][0] # Best bid price on futures
    spread = (futures_bid - spot_ask) / spot_ask * 100
    return spread

def calculate_exit_spread(coinex_orderbook, gateio_orderbook):
    """Calculate exit spread: (BID_spot - ASK_futures) / ASK_futures * 100"""
    spot_bid = coinex_orderbook['bids'][0][0]    # Best bid price on spot
    futures_ask = gateio_orderbook['asks'][0][0] # Best ask price on futures
    spread = (spot_bid - futures_ask) / futures_ask * 100
    return spread
