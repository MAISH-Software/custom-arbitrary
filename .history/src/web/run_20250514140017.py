from src.web.app import create_app

if __name__ == '__main__':
    # Provide your config dictionary here
    config = {
        # Add necessary config keys and values here
        # For example, 'WEB_SECRET': 'your_secret_key'
    }
    app, socketio = create_app(config)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
