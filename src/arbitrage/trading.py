import ccxt
from config import COINEX_ACCESS_ID, COINEX_SECRET_KEY, GATEIO_ACCESS_ID, GATEIO_SECRET_KEY

coinex = ccxt.coinex({'apiKey': COINEX_ACCESS_ID, 'secret': COINEX_SECRET_KEY})
gateio = ccxt.gateio({'apiKey': GATEIO_ACCESS_ID, 'secret': GATEIO_SECRET_KEY})

def place_spot_buy_order(cost):
    return coinex.create_market_buy_order('BTC/USDT', cost, params={'createMarketBuyOrderRequiresPrice': False})

def place_futures_sell_order(amount):
    return gateio.create_market_sell_order('BTC/USDT:USDT', amount)

def place_spot_sell_order(amount):
    balance = coinex.fetch_balance()
    available_btc = balance['BTC']['free']
    if available_btc >= amount:
        return coinex.create_market_sell_order('BTC/USDT', amount)
    else:
        print("Insufficient BTC balance: {available_btc} < {amount}")
        return None

def place_futures_buy_order(amount):
    return gateio.create_market_buy_order('BTC/USDT:USDT', amount)