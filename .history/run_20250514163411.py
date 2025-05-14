from config.settings import Config
from src.web.app import create_app

config = Config()
app, socketio = create_app(config)

if __name__ == '__main__':
    socketio.run(app, host=config.HOST, port=config.PORT, debug=True)
