import threading
from src.arbitrage.engine import ArbitrageEngine
from config.settings import Config 
from src.web.app import create_app 

def run_application():
    # Initialize configuration
    config = Config()
    app, socketio = create_app(config)
    engine = ArbitrageEngine(config)
    engine.socketio = socketio

    # Start web server in separate thread
    web_thread = threading.Thread(
        target=socketio.run,
        args=(app,),
        kwargs={
            'host': Config.HOST,
            'port': Config.PORT,
            'use_reloader': False
    })
    web_thread.start()

    # Start the arbitrage engine
    engine.start_monitoring()

    # Keep the main thread alive
    web_thread.join()

if __name__ == "__main__":
    run_application()