from flask import Blueprint, current_app, render_template, jsonify, request
from flask_socketio import SocketIO
from config.settings import Config
from src.arbitrage.engine import ArbitrageEngine
import json 

bp = Blueprint('main', __name__)
config = Config()

@bp.route('/')
def dashboard():
    engine = current_app.engine
    spreads = engine.get_current_spreads()
    chart = engine.generate_spread_chart('BTC/USDT', 24) if spreads else None

    # Extract spreads for BTC/USDT (will make this dynamic)
    btc_spread = next((s for s in spreads if s['symbol'] == 'BTC/USDT'), None)
    entry_spread = btc_spread['entry_spread'] if btc_spread else 0
    exit_spread = btc_spread['exit_spread'] if btc_spread else 0

    # Additional data for frontend rendering
    trading_pairs = [s['symbol'] for s in spreads] if spreads else []
    symbol = 'BTC/USDT'
    last_updated = None  # Could be set to current time or from engine if available
    active_positions = engine.get_open_positions() if hasattr(engine, 'get_open_positions') else []

    return render_template('index.html',
                            entry_spread=entry_spread,
                            exit_spread=exit_spread,
                            chart_json=json.dumps(chart.to_json()) if chart else '{}',
                            trading_pairs=trading_pairs,
                            symbol=symbol,
                            last_updated=last_updated,
                            active_positions=active_positions)

@bp.route('/api/positions', methods=['GET'])
def get_positions():
    engine = ArbitrageEngine()
    status = request.args.get('status', 'open')
    
    if status == 'open':
        positions = engine.get_open_positions()
    else:
        days = int(request.args.get('days', 7))
        positions = engine.get_closed_positions(days)
    
    return jsonify(positions)
