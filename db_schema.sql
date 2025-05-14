-- PostgreSQL schema for arbitrage trading app

CREATE TABLE spreads (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    spot_exchange VARCHAR(50) NOT NULL,
    futures_exchange VARCHAR(50) NOT NULL,
    entry_spread NUMERIC(10,6) NOT NULL,
    exit_spread NUMERIC(10,6) NOT NULL,
    entry_opportunity BOOLEAN DEFAULT FALSE,
    exit_opportunity BOOLEAN DEFAULT FALSE,
    tradable_volume NUMERIC(20,8),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL, -- e.g. 'open', 'closed'
    entry_spread NUMERIC(10,6),
    current_spread NUMERIC(10,6),
    profit_loss NUMERIC(20,8),
    position_id BIGINT UNIQUE NOT NULL,
    volume NUMERIC(20,8),
    opened_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ
);

CREATE TABLE order_book_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    bid_price NUMERIC(20,8),
    bid_volume NUMERIC(20,8),
    ask_price NUMERIC(20,8),
    ask_volume NUMERIC(20,8),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    action VARCHAR(10) NOT NULL, -- e.g. 'enter', 'exit'
    symbol VARCHAR(20) NOT NULL,
    volume NUMERIC(20,8),
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status VARCHAR(20) -- e.g. 'success', 'error'
);

-- Indexes for performance
CREATE INDEX idx_spreads_symbol ON spreads(symbol);
CREATE INDEX idx_positions_symbol ON positions(symbol);
CREATE INDEX idx_order_book_symbol ON order_book_data(symbol);
CREATE INDEX idx_trades_symbol ON trades(symbol);
