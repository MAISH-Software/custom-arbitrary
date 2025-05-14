from unittest.mock import MagicMock, patch
from src.web.app import create_app
from flask_socketio import SocketIO

def run_mock_app():
    with patch('src.web.app.ArbitrageEngine') as MockArbitrageEngine:
        # Setup mock engine with more diverse mock data
        mock_engine = MockArbitrageEngine.return_value

        # Mock get_current_spreads with multiple entries
        mock_engine.get_current_spreads.return_value = [
            {'symbol': 'BTC/USDT', 'entry_spread': 0.5, 'exit_spread': 0.3, 'timestamp': None},
            {'symbol': 'ETH/USDT', 'entry_spread': 0.4, 'exit_spread': 0.25, 'timestamp': None},
            {'symbol': 'XRP/USDT', 'entry_spread': 0.6, 'exit_spread': 0.35, 'timestamp': None},
            {'symbol': 'ADA/USDT', 'entry_spread': 0.45, 'exit_spread': 0.2, 'timestamp': None}
        ]

        # Mock get_open_positions with multiple positions
        mock_engine.get_open_positions.return_value = [
            {
                'id': 1, 'symbol': 'BTC/USDT', 'status': 'open',
                'entry_spread': 0.5, 'current_spread': 0.6,
                'profit_loss': 1.2, 'position_id': 123, 'volume': 0.01
            },
            {
                'id': 2, 'symbol': 'ETH/USDT', 'status': 'open',
                'entry_spread': 0.4, 'current_spread': 0.5,
                'profit_loss': 0.9, 'position_id': 124, 'volume': 0.5
            },
            {
                'id': 3, 'symbol': 'XRP/USDT', 'status': 'open',
                'entry_spread': 0.6, 'current_spread': 0.65,
                'profit_loss': 0.3, 'position_id': 125, 'volume': 100
            }
        ]

        # Mock chart response
        mock_chart = MagicMock()
        mock_chart.to_json.return_value = '{"data": [{"x": [], "y": []}], "layout": {}}'
        mock_engine.generate_spread_chart.return_value = mock_chart

        # Create app with dummy config
        app, socketio = create_app({})

        # Inject mock engine into app and socketio
        app.engine = mock_engine
        socketio.engine = mock_engine

        # Run the app
        socketio.run(app, host='127.0.0.1', port=5000, debug=True)

if __name__ == '__main__':
    run_mock_app()
