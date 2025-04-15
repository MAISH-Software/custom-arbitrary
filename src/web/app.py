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

    # Register blueprints
    app.register_blueprint(main_blueprint)
    socketio.engine = engine 


    return app, socketio