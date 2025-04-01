from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import ccxt
from src.exchange.exchange_connections import get_coinex_spot_orderbook, get_gateio_futures_orderbook, calculate_entry_spread, calculate_exit_spread
from config import COINEX_ACCESS_ID, COINEX_SECRET_KEY, GATEIO_ACCESS_ID, GATEIO_SECRET_KEY, DATABASE_URL
from threading import Thread
from time import sleep, time
import plotly.graph_objs as go
import json
import psycopg2

app = Flask(__name__)

# Initialize CoinEx and Gate.io API clients
coinex = ccxt.coinex({
    'apiKey': COINEX_ACCESS_ID,
    'secret': COINEX_SECRET_KEY,
})

gateio = ccxt.gateio({
    'apiKey': GATEIO_ACCESS_ID,
    'secret': GATEIO_SECRET_KEY,
})

socketio = SocketIO(app)

# Database connection
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()


def place_spot_buy_order(amount):
    coinex.create_market_buy_order('BTC/USDT', amount)  # Adjust based on your API setup

def place_futures_sell_order(amount):
    gateio.create_market_sell_order('BTC/USDT:USDT', amount)

def place_spot_sell_order(amount):
    coinex.create_market_sell_order('BTC/USDT', amount)

def place_futures_buy_order(amount):
    gateio.create_market_buy_order('BTC/USDT:USDT', amount)

# Background task to continuously monitor spreads
def background_task():
    while True:
        try:
            coinex_ob = get_coinex_spot_orderbook()
            gateio_ob = get_gateio_futures_orderbook()
            entry_spread = calculate_entry_spread(coinex_ob, gateio_ob)
            exit_spread = calculate_exit_spread(coinex_ob, gateio_ob)
            timestamp = time()
            
            # Insert data into the database
            cur.execute(
                "INSERT INTO spreads (timestamp, entry_spread, exit_spread) VALUES (%s, %s, %s)",
                (timestamp, entry_spread, exit_spread)
            )
            conn.commit()

            # Send new data to all connected clients
            socketio.emit('new_data', {'entry_spread': entry_spread, 'exit_spread': exit_spread, 'timestamp': timestamp}, broadcast=True)

            # Trading logic
            lot_size = 0.001  # Adjust based on your API setup
            SPRED_IN = 0.5  # Adjust based on your strategy
            SPRED_OUT = 0.5  # Adjust based on your strategy

            if entry_spread > SPRED_IN:
                place_spot_buy_order(lot_size)
                place_futures_sell_order(lot_size)
                print("Entry order placed")
            elif exit_spread > SPRED_OUT:
                place_spot_sell_order(lot_size)
                place_futures_buy_order(lot_size)
                print("Exit order placed")

            sleep(5)
        except Exception as e:
            print(f"Error in background task: {e}")
            sleep(5)

# Route to display data
@app.route('/')
def index():
    # Fetch the latest 1000 records from the database
    cur.execute("SELECT * FROM spreads ORDER BY timestamp DESC LIMIT 1000")
    history = cur.fetchall()
    if history:
        timestamps = [row[0] for row in history]
        entry_spreads = [row[1] for row in history]
        exit_spreads = [row[2] for row in history]

        # Create Plotly graph
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=timestamps, y=entry_spreads, mode='lines', name='Entry Spread'))
        fig.add_trace(go.Scatter(x=timestamps, y=exit_spreads, mode='lines', name='Exit Spread'))
        fig.update_layout(title='Spread History', xaxis_title='Time', yaxis_title='Spread (%)')
        graph_json = fig.to_json()

        current_entry = history[0][1]
        current_exit = history[0][2]
    else:
        graph_json = None
        current_entry = 0
        current_exit = 0

    return render_template('index.html', entry_spread=current_entry, exit_spread=current_exit, graph_json=graph_json)

if __name__ == '__main__':
    thread = Thread(target=background_task)
    thread.start()
    socketio.run(app, debug=True)