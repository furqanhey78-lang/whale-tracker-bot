import os
import time
import threading
import requests
from flask import Flask

app = Flask(__name__)

@app.route("/")
def health_check():
    return "Derivatives & Whale Terminal Backend is live 24/7!"

# Keep-alive loop to prevent Render free tier from sleeping
def keep_alive():
    # Render automatically injects this environment variable into web services
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    if not render_url:
        print("⚠️ RENDER_EXTERNAL_URL not found. Self-ping disabled.")
        return

    print(f"💓 Keep-alive worker initialized for: {render_url}")
    while True:
        try:
            response = requests.get(render_url)
            print(f"💓 Self-ping sent successfully. Status: {response.status_code}")
        except Exception as e:
            print(f"Self-ping error: {e}")
        time.sleep(300) # Ping every 5 minutes (300 seconds)

def run_derivatives_tracker():
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

    print("🚀 Starting Derivatives Data Ingestion Engine...")

    while True:
        try:
            response = requests.get("https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT")
            if response.status_code == 200:
                data = response.json()
                symbol = data.get("symbol")
                open_interest = float(data.get("openInterest", 0))
                
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
            
        time.sleep(60) # Poll Binance every minute

if __name__ == "__main__":
    # Start Binance data tracker background thread
    bot_thread = threading.Thread(target=run_derivatives_tracker, daemon=True)
    bot_thread.start()
    
    # Start self-ping keep-alive background thread
    ping_thread = threading.Thread(target=keep_alive, daemon=True)
    ping_thread.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
