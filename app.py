import os
import time
import threading
import requests
import yfinance as yf
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Curated Smart-Money & Institutional Wallet Dictionary (Your Moat)
SMART_WALLETS = {
    "0x28c6c06298d514db089934071355e5743bf21d60": "Binance Hot Wallet 14 (Exchange Flow)",
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549": "Binance Cold / Institutional Reserve",
    "0xdbf5e9c5206d0db70a90108bf936da60221dc080": "Wintermute Market Maker",
    "0xf584f8728b874a6a5c7a8d4d387c9aae9172d621": "Jump Trading Institutional Desk",
    "0xae2fc483527b8ef99eb5d9b44875f005ba1fae13": "jaredfromsubway.eth (MEV Whale)"
}

SEEN_TXS = set()
SEEN_OPTIONS = set()

@app.route("/")
def health():
    return "SUPRIM Alert Engine Live"

def send_suprim_discord_alert(title, description, color=2712319, fields=None):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("⚠️ DISCORD_WEBHOOK_URL not set in Render Environment Variables.")
        return

    embed = {
        "title": title,
        "description": description,
        "color": color,
        "fields": fields or [],
        "footer": {"text": "SUPRIM Institutional Alert Engine • Real-Time Signal"}
    }
    try:
        requests.post(webhook_url, json={"username": "SUPRIM Alerts", "embeds": [embed]}, timeout=10)
    except Exception as e:
        print(f"Discord webhook error: {e}")

# 1. Crypto Smart-Money Wallet Monitor
def monitor_crypto_whales():
    etherscan_key = os.getenv("ETHERSCAN_API_KEY", "")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    while True:
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
                        direction = "OUTFLOW 🔴" if tx.get("from", "").lower() == address.lower() else "INFLOW 🟢"
                        
                        send_suprim_discord_alert(
                            title=f"🐋 SMART MONEY MOVE: {eth_val:,.2f} ETH",
                            description=f"**Entity:** `{label}`\n**Direction:** {direction}",
                            color=15158332 if "OUTFLOW" in direction else 3066993,
                            fields=[
                                {"name": "Amount", "value": f"{eth_val:,.2f} ETH", "inline": True},
                                {"name": "Etherscan", "value": f"[View Tx ↗](https://etherscan.io/tx/{tx_hash})", "inline": True}
                            ]
                        )

                        if supabase_url and supabase_key:
                            requests.post(
                                f"{supabase_url}/rest/v1/whale_txs",
                                json={
                                    "wallet_name": label,
                                    "eth_amount": round(eth_val, 2),
                                    "tx_hash": tx_hash,
                                    "tx_from": tx.get("from"),
                                    "tx_to": tx.get("to")
                                },
                                headers={
                                    "apikey": supabase_key,
                                    "Authorization": f"Bearer {supabase_key}",
                                    "Content-Type": "application/json"
                                }
                            )
            except Exception as e:
                print(f"Whale scan error: {e}")
            time.sleep(2)
        time.sleep(45)

# 2. Unusual Stock Options Sweep Scanner
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
                            strike = row["strike"]
                            last_price = row["lastPrice"]
                            premium = vol * last_price * 100

                            if premium >= 50000:
                                send_suprim_discord_alert(
                                    title=f"🚨 UNUSUAL OPTIONS SWEEP: ${ticker}",
                                    description=f"Massive volume spike detected on **{ticker} ${strike} {opt_type}** ({nearest_exp})",
                                    color=3447003,
                                    fields=[
                                        {"name": "Est. Premium", "value": f"${premium:,.0f}", "inline": True},
                                        {"name": "Vol / OI", "value": f"{vol:,} / {oi:,}", "inline": True}
                                    ]
                                )
            except Exception as e:
                print(f"Options scan error for {ticker}: {e}")
            time.sleep(3)
        time.sleep(180)

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
    threading.Thread(target=keep_alive, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
