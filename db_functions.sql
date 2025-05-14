-- Function to insert order book data into order_book_data table
CREATE OR REPLACE FUNCTION insert_order_book(
    p_symbol VARCHAR,
    p_exchange VARCHAR,
    p_bid_price NUMERIC,
    p_bid_volume NUMERIC,
    p_ask_price NUMERIC,
    p_ask_volume NUMERIC,
    p_timestamp TIMESTAMPTZ
) RETURNS VOID AS $$
BEGIN
    INSERT INTO order_book_data (
        symbol,
        exchange,
        bid_price,
        bid_volume,
        ask_price,
        ask_volume,
        timestamp
    ) VALUES (
        p_symbol,
        p_exchange,
        p_bid_price,
        p_bid_volume,
        p_ask_price,
        p_ask_volume,
        p_timestamp
    );
END;
$$ LANGUAGE plpgsql;
