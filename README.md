# Crypto Arbitrage Dashboard

This project provides a real-time dashboard for monitoring and executing arbitrage opportunities between CoinEx (spot) and Gate.io (futures) for BTC/USDT. It features automated trading, manual trading controls, and Telegram notifications.

## Features
- Real-time monitoring of entry and exit spreads with historical graphing.
- Automated arbitrage trading based on configurable spread thresholds.
- Manual trading via a web interface with color-coded buttons.
- Telegram notifications for trade executions.
- PostgreSQL database with TimescaleDB for spread history.

## Setup Instructions

### Prerequisites
- Python 3.8+
- PostgreSQL with TimescaleDB extension
- API keys for CoinEx and Gate.io
- Telegram bot token and chat ID

### Installation
1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd CrypArbSpot

2. Create a virtual environment and install  dependencies
 - python -m venv env
 - source env/bin/activate # On Windows: env\Scripts\activate
 - pip install -r requirements.txt
3. Set up the database
 - Create a PostgreSQL database and run:
 ```
 CREATE TABLE spreads (
    timestamp TIMESTAMPTZ NOT NULL,
    entry_spread DOUBLE PRECISION,
    exit_spread DOUBLE PRECISION
);
SELECT create_hypertable('spreads', 'timestamp');
```
4. Configure config.py:
- Add your CoinEx and Gate.io API keys (COINEX_ACCESS_ID, COINEX_SECRET_KEY, GATEIO_ACCESS_ID, GATEIO_SECRET_KEY).
- Set DATABASE_URL (e.g., postgresql://user:password@localhost:5432/dbname)
- Define SPRED_IN, SPRED_OUT, and LOT_SIZE (e.g., 100 USDT for buys, 0.001 BTC for sells).

### Running the Application
1. Start the Flask App
``` python app.py ```
2. Access the dashboard at http://127.0.0.1:5000

### Usage
- Automated Trading: The system executes trades when spreads exceed SPRED_IN(entry) or SPRED_OUT (exit).
- Manual Trading: Click "Enter Trade" (green) to buy spot and sell futures, or "Exit Trade" (red) to sell spot and buy futures
- Monitoring: View real-time spreads and historical data on the dashboard
- Notifications: Receive Telegram alerts for all trades

### Project Structure
- app.py: Main Flask application with SocketIO and background tasks.
- src/exchange/exchange_connections.py: Exchange API connections and spread calculations.
- src/arbitrage/trading.py: Trading functions for order placement
- src/notifications/telegram.py: Telegram notification logic
- templates/index.html: Web interface template
- config.py: Configuration settings.

### Known Issues
- Ensure sufficient funds in CoinEx and Gate.io accounts to avoid InsufficientFunds errors
- Adjust LOT_SIZE based on your trading strategy and account balance

## License
MIT license


