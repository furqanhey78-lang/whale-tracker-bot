import os
import time
import threading
import requests
import yfinance as yf
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enables cross-origin requests from your GitHub Pages frontend

@app.route("/")
def health_check():
    return "SUPRIM Institutional Terminal Backend is live 24/7!"

# Keep-alive loop to prevent Render free tier from sleeping
def keep_alive():
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    if not render_url:
        print("⚠️ RENDER_EXTERNAL_URL not found. Self-ping disabled.")
        return

    print(f"💓 Keep-alive worker initialized for: {render_url}")
    while True:
        try:
            response = requests.get(render_url)
            print(f"💓 Self-ping sent. Status: {response.status_code}")
        except Exception as e:
            print(f"Self-ping error: {e}")
        time.sleep(300)

# Live Screener API Endpoint using yfinance
@app.route("/api/screener")
def get_screener_data():
    tickers = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "PLTR", "BTC-USD", "ETH-USD", "SOL-USD"]
    screener_results = []
    
    try:
        data = yf.download(tickers, period="1d", group_by="ticker", threads=True)
        for ticker in tickers:
            try:
                df = data[ticker] if len(tickers) > 1 else data
                if df.empty or len(df.dropna()) == 0:
                    continue
                latest = df.iloc[-1]
                prev = df.iloc[-2] if len(df) > 1 else latest
                
                price = float(latest["Close"])
                prev_close = float(prev["Close"])
                change_pct = ((price - prev_close) / prev_close) * 100
                volume = int(latest["Volume"])
                
                t_obj = yf.Ticker(ticker)
                info = t_obj.info
                name = info.get("shortName", ticker)
                sector = info.get("sector", "Cryptocurrency" if "-USD" in ticker else "Technology")
                market_cap = info.get("marketCap", 0)
                pe_ratio = info.get("trailingPE", "N/A")
                
                screener_results.append({
                    "symbol": ticker.replace("-USD", ""),
                    "name": name,
                    "sector": sector,
                    "price": round(price, 2),
                    "change": round(change_pct, 2),
                    "volume": f"{volume:,.0f}",
                    "cap": f"${market_cap:,.0f}" if market_cap else "N/A",
                    "pe": round(pe_ratio, 2) if isinstance(pe_ratio, (int, float)) else pe_ratio
                })
            except Exception as ex:
                print(f"Error processing {ticker}: {ex}")
                
        return jsonify(screener_results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Background thread to pull Binance Open Interest metrics
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
        time.sleep(60)

if __name__ == "__main__":
    # Start background threads
    threading.Thread(target=keep_alive, daemon=True).start()
    threading.Thread(target=run_derivatives_tracker, daemon=True).start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
