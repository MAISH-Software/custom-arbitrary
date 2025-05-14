import unittest
from unittest.mock import patch, MagicMock
from src.web.app import create_app
import json

class TestRoutesWithMockData(unittest.TestCase):
    def setUp(self):
        # Create app with dummy config
        self.app, self.socketio = create_app({})
        self.client = self.app.test_client()

    @patch('src.web.routes.ArbitrageEngine')
    def test_get_positions_open(self, MockArbitrageEngine):
        # Setup mock for get_open_positions
        mock_engine = MockArbitrageEngine.return_value
        mock_engine.get_open_positions.return_value = [
            {'id': 1, 'symbol': 'BTC/USDT', 'status': 'open', 'entry_price': 30000}
        ]

        response = self.client.get('/api/positions?status=open')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['symbol'], 'BTC/USDT')
        self.assertEqual(data[0]['status'], 'open')

    @patch('src.web.routes.ArbitrageEngine')
    def test_get_positions_closed(self, MockArbitrageEngine):
        # Setup mock for get_closed_positions
        mock_engine = MockArbitrageEngine.return_value
        mock_engine.get_closed_positions.return_value = [
            {'id': 2, 'symbol': 'ETH/USDT', 'status': 'closed', 'exit_price': 2000}
        ]

        response = self.client.get('/api/positions?status=closed&days=7')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['symbol'], 'ETH/USDT')
        self.assertEqual(data[0]['status'], 'closed')

    @patch('src.web.routes.current_app')
    def test_dashboard_with_mock_data(self, mock_current_app):
        # Mock engine and its methods
        mock_engine = MagicMock()
        mock_engine.get_current_spreads.return_value = [
            {'symbol': 'BTC/USDT', 'entry_spread': 0.5, 'exit_spread': 0.3}
        ]
        mock_engine.get_open_positions.return_value = [
            {'id': 1, 'symbol': 'BTC/USDT', 'status': 'open'}
        ]
        mock_current_app.engine = mock_engine

        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'BTC/USDT', response.data)

if __name__ == '__main__':
    unittest.main()
