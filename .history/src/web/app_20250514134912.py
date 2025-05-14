from flask import Flask
from flask_socketio import SocketIO
from src.arbitrage.engine import ArbitrageEngine
from src.web.routes import bp as main_blueprint



def create_app(config):
    app = Flask(__name__)
    app.config.from_mapping(
     #   SECRET_KEY=config.get('WEB_SECRET', 'dev_key'),
        ENGINE_CONFIG=config,
    )

    engine = ArbitrageEngine(config)
    app.engine = engine 

    # Initialize SocketIO
    socketio = SocketIO(app, cors_allowed_origins='*')

    @socketio.on('manual_trade')
    def handle_manual_trade(data):
        action = data['action']
        symbol = data['symbol']
        try:
            if action == 'enter':
                engine.execute_manual_exit_trade(symbol)
                socketio.emit('trade_response', {'status': 'success', 'message': f'Entered trade for {symbol}'})
            elif action == 'exit':
                engine._execute_exit_trade(symbol)
                socketio.emit('trade_response', {'status': 'success', 'message': f'Exited trade for {symbol}'})
        except Exception as e:
            socketio.emit('trade_response', {'status': 'error', 'message': str(e)})

        # Handle manual trade event
        print(f"Manual trade data received: {data}")
        # You can add your logic here to process the manual trade

    @socketio.on('request_initial_data')
    def handle_request_initial_data():
        trading_pairs = [s['symbol'] for s in engine.get_current_spreads()] if engine.get_current_spreads() else []
        active_positions = engine.get_open_positions() if hasattr(engine, 'get_open_positions') else []
        socketio.emit('trading_pairs', trading_pairs)
        socketio.emit('positions_update', {'positions': active_positions})

    @socketio.on('request_symbol_data')
    def handle_request_symbol_data(data):
        symbol = data.get('symbol', 'BTC/USDT')
        spreads = engine.get_current_spreads()
        spread_data = next((s for s in spreads if s['symbol'] == symbol), None) if spreads else None
        chart = engine.generate_spread_chart(symbol, 24) if spread_data else None

        if spread_data:
            socketio.emit('spread_update', {
                'symbol': symbol,
                'entry_spread': spread_data['entry_spread'],
                'exit_spread': spread_data['exit_spread'],
                'timestamp': spread_data.get('timestamp')
            })
        if chart:
            socketio.emit('chart_data', {'symbol': symbol, 'chart_json': chart.to_json()})

    # Register blueprints
    app.register_blueprint(main_blueprint)
    socketio.engine = engine 


    return app, socketio
