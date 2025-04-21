from flask import Flask
from flask_socketio import SocketIO
from arbitrage.engine import ArbitrageEngine
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

    # Register blueprints
    app.register_blueprint(main_blueprint)
    socketio.engine = engine 


    return app, socketio