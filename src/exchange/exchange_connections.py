import ccxt
from config import COINEX_ACCESS_ID, COINEX_SECRET_KEY, GATEIO_ACCESS_ID, GATEIO_SECRET_KEY, SPRED_IN, SPRED_OUT
from time import sleep

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

def get_gateio_futures_orderbook(symbol='BTC/USDT:USDT'):
    """Fetch the order book for BTC_USDT on Gate.io futures market"""
    return gateio.fetch_order_book(symbol)


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

def monitor_arbitrage():
    while True:
        try:
            coinex_ob = get_coinex_spot_orderbook()
            gateio_ob = get_gateio_futures_orderbook()
            entry_spread = calculate_entry_spread(coinex_ob, gateio_ob)
            exit_spread = calculate_exit_spread(coinex_ob, gateio_ob)

            print(f"Entry spread: {entry_spread:.2f}% | Exit spread: {exit_spread:.2f}%")

            if entry_spread > SPRED_IN:
                print("Arbitrage Opportunity detected! Buy Spot, Sell Futures")
            elif exit_spread > SPRED_OUT:
                print("Arbitrage Opportunity detected! Sell Spot, Buy Futures")

            sleep(5)
        except Exception as e:
            print(f"Error in arbitrage loop: {e}")
            sleep(5)

if __name__ == '__main__':
    monitor_arbitrage()