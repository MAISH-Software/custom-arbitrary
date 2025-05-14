import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    HOST = os.getenv("APP_HOST", "0.0.0.0")
    PORT = int(os.getenv("APP_PORT", 5000))

    DB_URL = os.getenv("DATABASE_URL", 'postgresql://postgres:gordonpsql@localhost:5432/crypto_arbitrage')

    EXCHANGE_CREDS = {
        'coinex': {
            'apiKey': os.getenv("COINEX_ACCESS_ID"),
            'secret': os.getenv("COINEX_SECRET_KEY")
        },
        'gateio': {
            'apiKey': os.getenv("GATEIO_ACCESS_ID"),
            'secret': os.getenv("GATEIO_SECRET_KEY")
        }
    }
    TRADING_PARAMS = {
        'spread_in': float(os.getenv("SPREAD_IN", 0.5)),
        'spread_out': float(os.getenv("SPREAD_OUT", 0.2)),
        'lot_min': float(os.getenv("LOT_MIN", 250.0)),
        'lot_max': float(os.getenv("LOT_MAX", 1000.0)),
        'auto_trade': os.getenv("AUTO_TRADE", "true").lower() == 'true',
    }

    # Trading Pairs (dynamically configurable)
    TRADING_PAIRS = [
        {
            "symbol": "BTC/USDT",
            "spot_exchange": "coinex",
            "futures_exchange": "gateio",
            "spot_symbol": "BTCUSDT",
            "futures_symbol": "BTC_USDT"
        }
        # Add more pairs here or load dynamically if needed
    ]

    # Monitoring
    MONITORING = {
        "check_interval_seconds": int(os.getenv("CHECK_INTERVAL_SECONDS", 60))
    }

    NOTIFICATIONS = {
        'telegram': {
            'token': os.getenv("TELEGRAM_BOT_TOKEN"),
            'chat_id': os.getenv("TELEGRAM_CHAT_ID")
        },
        'twilio': {
            'account_sid': os.getenv("TWILIO_ACCOUNT_SID"),
            'auth_token': os.getenv("TWILIO_AUTH_TOKEN"),
            'phone_number': os.getenv("TWILIO_PHONE_NUMBER")
        },
        'enabled': os.getenv("NOTIFICATIONS_ENABLED", "true").lower() == 'true',
        'type': os.getenv("NOTIFICATION_TYPE", "telegram")
    }

    # Maintenance
    MAINTENANCE = {
        'interval_hours': int(os.getenv("MAINTENANCE_INTERVAL_HOURS", 24)),
        'data_retention_days': int(os.getenv("DATA_RETENTION_DAYS", 90))
    }

    WEB_INTERFACE = {
    'enabled': os.getenv("WEB_INTERFACE_ENABLED", "true").lower() == 'true'
    }
