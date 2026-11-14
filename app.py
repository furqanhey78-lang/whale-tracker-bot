import os
import time
import threading
import requests
from flask import Flask

app = Flask(__name__)

@app.route("/")
def health_check():
    return "Derivatives & Whale Terminal Backend is live 24/7!"

def run_derivatives_tracker():
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

    print("🚀 Starting Derivatives Data Ingestion Engine...")

    while True:
        try:
            # Fetch global Bitcoin futures Open Interest from public exchange endpoints
            response = requests.get("https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT")
            if response.status_code == 200:
                data = response.json()
                symbol = data.get("symbol")
                open_interest = float(data.get("openInterest", 0))
                
                # Log or push to Supabase time-series table
                if SUPABASE_URL and SUPABASE_KEY:
                    sb_url = f"{SUPABASE_URL}/rest/v1/derivatives_metrics"
                    sb_headers = {
                        "apikey": SUPABASE_KEY,
                        "Authorization": f"Bearer {SUPABASE_KEY}",
                        "Content-Type": "application/json",
                        "Prefer": "return=minimal"
                    }
                    sb_data = {
                        "symbol": symbol,
                        "metric_type": "open_interest",
                        "value": open_interest
                    }
                    requests.post(sb_url, json=sb_data, headers=sb_headers)
                print(f"✅ Logged OI for {symbol}: {open_interest:,.2f}")

        except Exception as e:
            print(f"Error fetching derivatives data: {e}")
            
        time.sleep(60) # Poll every minute

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_derivatives_tracker, daemon=True)
    bot_thread.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
