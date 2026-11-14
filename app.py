import os
import time
import threading
import requests
from flask import Flask

app = Flask(__name__)

@app.route("/")
def health_check():
    return "Whale Bot is running 24/7 in the cloud!"

def run_bot():
    ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "97NPEGHCAB541Z54C5HS46I4MY68JT1JSW")
    DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1571224981495357610/73iNSJys6jCs7f_qRkBFH9IzJk2QmDzwI6JI2jVgH_9hlONCVmYB5R12wmMmbXVGg_6N")

    WHALE_WATCHLIST = {
        "Binance Hot Wallet": "0x28C6c06298d514Db089934071355E5743bf21d60",
        "Kraken Hot Wallet": "0x2098C222d3780D21B8516F54D742617f695276e0",
        "Tether Treasury": "0x63a99E256C82BFA3b890833F9C7D4f92d6e3e5E6",
        "Coinbase Prime": "0xcd531ae9efcce479654c4926dec5f6209531ca7b",
        "Jump Trading": "0xf584f8728b874a6a5c7a8d4d387c9aae9172d621"
    }

    print("🚀 Starting Expanded Multi-Wallet Whale Tracker...")
    seen_txs = set()

    while True:
        for wallet_name, address in WHALE_WATCHLIST.items():
            try:
                url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&page=1&offset=3&sort=desc&apikey={ETHERSCAN_API_KEY}"
                response = requests.get(url).json()
                
                if response.get("status") == "1":
                    for tx in response["result"]:
                        tx_hash = tx["hash"]
                        if tx_hash not in seen_txs:
                            seen_txs.add(tx_hash)
                            eth_amount = int(tx["value"]) / 10**18
                            
                            if eth_amount > 20:
                                discord_payload = {
                                    "content": f"🚨 **WHALE MOVEMENT: {wallet_name}** 🚨\n"
                                               f"• **Amount:** `{eth_amount:,.2f} ETH`\n"
                                               f"• **From:** `{tx['from'][:10]}...`\n"
                                               f"• **To:** `{tx['to'][:10]}...`\n"
                                               f"• **Link:** https://etherscan.io/tx/{tx_hash}`"
                                }
                                requests.post(DISCORD_WEBHOOK_URL, json=discord_payload)
                                print(f"✅ Alert sent for {wallet_name}: {eth_amount:,.2f} ETH")
                time.sleep(2)
            except Exception as e:
                print(f"Error checking {wallet_name}: {e}")
                
        time.sleep(30)

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
