import os
import time
import threading
import requests
import yfinance as yf
from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

SMART_WALLETS = {
    "0x28c6c06298d514db089934071355e5743bf21d60": "Binance Hot Wallet 14 (Exchange Flow)",
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549": "Binance Cold / Institutional Reserve",
    "0xdbf5e9c5206d0db70a90108bf936da60221dc080": "Wintermute Market Maker",
    "0xf584f8728b874a6a5c7a8d4d387c9aae9172d621": "Jump Trading Institutional Desk",
    "0xae2fc483527b8ef99eb5d9b44875f005ba1fae13": "jaredfromsubway.eth (MEV Whale)"
}

SEEN_TXS = set()
SEEN_OPTIONS = set()
SEEN_INSIDERS = set()

@app.route("/")
def health():
    return "SUPRIM Institutional Alert Engine Live"

def log_and_broadcast_alert(category, asset, headline, usd_value, details, source_url, color=2712319):
    # 1. Push to Discord Webhook
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if webhook_url:
        embed = {
            "title": f"[{category}] {asset} — ${usd_value:,.0f}",
            "description": f"**{headline}**\n{details}",
            "color": color,
            "fields": [{"name": "Verification", "value": f"[View Source ↗]({source_url})", "inline": True}] if source_url else [],
            "footer": {"text": "SUPRIM Alert Engine • Real-Time Signal"}
        }
        try:
            requests.post(webhook_url, json={"username": "SUPRIM Alerts", "embeds": [embed]}, timeout=10)
        except Exception as e:
            print(f"Discord error: {e}")

    # 2. Save to Supabase for the Live Website Feed
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if supabase_url and supabase_key:
        try:
            requests.post(
                f"{supabase_url}/rest/v1/suprim_alerts",
                json={
                    "category": category,
                    "asset": asset,
                    "headline": headline,
                    "usd_value": round(float(usd_value), 2),
                    "details": details,
                    "source_url": source_url
                },
                headers={
                    "apikey": supabase_key,
                    "Authorization": f"Bearer {supabase_key}",
                    "Content-Type": "application/json"
                },
                timeout=10
            )
        except Exception as e:
            print(f"Supabase insert error: {e}")

# Engine 1: Crypto Smart-Money Whales
def monitor_crypto_whales():
    etherscan_key = os.getenv("ETHERSCAN_API_KEY", "")
    while True:
        try:
            eth_price = yf.Ticker("ETH-USD").fast_info.get("lastPrice", 3100)
        except Exception:
            eth_price = 3100

        for address, label in SMART_WALLETS.items():
            try:
                url = f"https://api.etherscan.io/v2/api?chainid=1&module=account&action=txlist&address={address}&startblock=0&endblock=99999999&page=1&offset=5&sort=desc&apikey={etherscan_key}"
                res = requests.get(url, timeout=10).json()
                txs = res.get("result", [])
                if not isinstance(txs, list):
                    continue

                for tx in txs:
                    tx_hash = tx.get("hash")
                    eth_val = int(tx.get("value", 0)) / 10**18
                    if tx_hash not in SEEN_TXS and eth_val >= 25.0:
                        SEEN_TXS.add(tx_hash)
                        usd_val = eth_val * eth_price
                        direction = "OUTFLOW 🔴" if tx.get("from", "").lower() == address.lower() else "INFLOW 🟢"
                        log_and_broadcast_alert(
                            category="CRYPTO WHALE",
                            asset="ETH",
                            headline=f"{label} ({direction})",
                            usd_value=usd_val,
                            details=f"Moved {eth_val:,.2f} ETH on Ethereum Mainnet",
                            source_url=f"https://etherscan.io/tx/{tx_hash}",
                            color=15158332 if "OUTFLOW" in direction else 3066993
                        )
            except Exception as e:
                print(f"Whale scan error: {e}")
            time.sleep(2)
        time.sleep(45)

# Engine 2: Unusual Stock Options Sweeps
def monitor_stock_options():
    watchlist = ["NVDA", "TSLA", "AAPL", "PLTR", "AMD", "COIN", "MSTR", "SPY"]
    while True:
        for ticker in watchlist:
            try:
                stock = yf.Ticker(ticker)
                expirations = stock.options
                if not expirations:
                    continue
                nearest_exp = expirations[0]
                chain = stock.option_chain(nearest_exp)

                for opt_type, df in [("CALL 🟢", chain.calls), ("PUT 🔴", chain.puts)]:
                    unusual = df[(df["volume"] > 2000) & (df["volume"] > df["openInterest"] * 3)]
                    for _, row in unusual.iterrows():
                        contract = row["contractSymbol"]
                        if contract not in SEEN_OPTIONS:
                            SEEN_OPTIONS.add(contract)
                            vol = int(row["volume"])
                            oi = int(row["openInterest"])
                            premium = vol * (row["lastPrice"] or 0) * 100
                            if premium >= 50000:
                                log_and_broadcast_alert(
                                    category="OPTIONS SWEEP",
                                    asset=f"${ticker}",
                                    headline=f"${ticker} ${row['strike']} {opt_type} ({nearest_exp})",
                                    usd_value=premium,
                                    details=f"Vol: {vol:,} vs OI: {oi:,} ({round(vol/max(oi,1), 1)}x spike)",
                                    source_url=f"https://finance.yahoo.com/quote/{ticker}/options",
                                    color=3447003
                                )
            except Exception as e:
                print(f"Options scan error ({ticker}): {e}")
            time.sleep(3)
        time.sleep(180)

# Engine 3: Corporate Insider Open-Market Purchases (Finnhub)
def monitor_corporate_insiders():
    finnhub_key = os.getenv("FINNHUB_API_KEY")
    if not finnhub_key:
        print("⚠️ FINNHUB_API_KEY not set.")
        return

    watchlist = ["NVDA", "TSLA", "AAPL", "PLTR", "AMD", "COIN", "MSTR", "META", "AMZN", "MSFT"]
    while True:
        for ticker in watchlist:
            try:
                url = f"https://finnhub.io/api/v1/stock/insider-transactions?symbol={ticker}&token={finnhub_key}"
                res = requests.get(url, timeout=10).json()
                for tx in res.get("data", [])[:5]:
                    if tx.get("transactionCode") == "P":
                        shares = abs(tx.get("change", 0))
                        price = tx.get("transactionPrice", 0) or 0
                        total_usd = shares * price
                        filing_id = f"{ticker}_{tx.get('name')}_{tx.get('filingDate')}_{shares}"

                        if total_usd >= 50000 and filing_id not in SEEN_INSIDERS:
                            SEEN_INSIDERS.add(filing_id)
                            log_and_broadcast_alert(
                                category="INSIDER BUY",
                                asset=f"${ticker}",
                                headline=f"{tx.get('name')} — Form 4 Open-Market Buy",
                                usd_value=total_usd,
                                details=f"Bought {shares:,} shares @ ${price:,.2f} (Filed {tx.get('filingDate')})",
                                source_url=f"https://www.sec.gov/edgar/searchedgar/companysearch",
                                color=15844367
                            )
            except Exception as e:
                print(f"Finnhub error ({ticker}): {e}")
            time.sleep(2)
        time.sleep(300)

def keep_alive():
    url = os.getenv("RENDER_EXTERNAL_URL")
    while url:
        try:
            requests.get(url, timeout=10)
        except Exception:
            pass
        time.sleep(300)

if __name__ == "__main__":
    threading.Thread(target=monitor_crypto_whales, daemon=True).start()
    threading.Thread(target=monitor_stock_options, daemon=True).start()
    threading.Thread(target=monitor_corporate_insiders, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
