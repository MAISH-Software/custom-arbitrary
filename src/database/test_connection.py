import psycopg2
from config import DATABASE_URL


try:
    conn = psycopg2.connect(DATABASE_URL)
    print("Database connection successful!")
    conn.close()
except Exception as e:
    print(f"Error: {e}")