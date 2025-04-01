import ccxt

# Public access 
coinex = ccxt.coinex()
gateio = ccxt.gateio()
gateio.load_markets()
futures_symbols = [symbol for symbol in gateio.markets if gateio.markets[symbol]['type'] == 'swap' and gateio.markets[symbol]['settle'] == 'USDT']
print("Available USDT futures symbols:", futures_symbols)

try:
    coinex_orderbook = coinex.fetch_order_book('BTC/USDT')
    print("Coinex order book fetched successfully!")
    gateio_orderbook = gateio.fetch_order_book('BTC_USDT', params={'settle': 'usdt'})
    print("Gate.io order book fetched successfully!")
except Exception as e:
    print(f"Error fetching order books: {e}")