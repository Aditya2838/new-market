from dotenv import load_dotenv
load_dotenv()
import os
from kiteconnect import KiteConnect

kite = KiteConnect(api_key=os.getenv("KITE_API_KEY"))
kite.set_access_token(os.getenv("KITE_ACCESS_TOKEN"))
try:
    print("Profile:", kite.profile())
    candles = kite.historical_data(256265, "2024-06-01 09:15:00", "2024-06-01 15:30:00", "minute")
    print("Fetched", len(candles), "candles")
except Exception as e:
    print("Kite API error:", e)