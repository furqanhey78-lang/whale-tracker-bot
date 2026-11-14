import os
import time
import threading
import requests
import yfinance as yf
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS so your GitHub Pages frontend can talk to Render

@app.route("/")
def health_check():
    return "SUPRIM Terminal Backend is live 24/7!"

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

# Live Screener API Endpoint
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
                
                # Fetch basic fundamentals if available
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

if __name__ == "__main__":
    # Start keep-alive thread
    ping_thread = threading.Thread(target=keep_alive, daemon=True)
    ping_thread.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
