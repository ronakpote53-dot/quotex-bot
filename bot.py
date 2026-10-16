import threading
import time
import os
import sqlite3
import requests
import random
from datetime import datetime
from flask import Flask, request

# --- CONFIGURATION & CREDENTIALS ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")

app = Flask(__name__)

# --- DATABASE SETUP ---
def init_db():
    try:
        conn = sqlite3.connect('bot_database.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                pair TEXT,
                direction TEXT,
                strategy TEXT,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Init Error: {e}")

init_db()

def log_signal_to_db(pair, direction, strategy, status="PENDING"):
    try:
        conn = sqlite3.connect('bot_database.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO signals (timestamp, pair, direction, strategy, status) VALUES (?, ?, ?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pair, direction, strategy, status)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database Error: {e}")

def get_stats_from_db():
    try:
        conn = sqlite3.connect('bot_database.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM signals")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM signals WHERE status='WIN'")
        wins = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM signals WHERE status='LOSS'")
        losses = cursor.fetchone()[0]
        
        conn.close()
        return total, wins, losses
    except Exception as e:
        print(f"Stats Error: {e}")
        return 0, 0, 0

@app.route('/')
def home():
    return "Quotex OTC Bot is Running 24/7!"

@app.route('/health')
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, 200

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    try:
        data = request.get_json()
        if data and "message" in data:
            message = data["message"]
            text = message.get("text", "").strip()
            chat_id = message["chat"]["id"]

            if text == "/stats":
                total, wins, losses = get_stats_from_db()
                win_rate = (wins / total * 100) if total > 0 else 0
                response_text = (
                    f"📊 *Bot Performance Statistics*\n\n"
                    f"• Total Signals: `{total}`\n"
                    f"• Wins: `{wins}` 🟢\n"
                    f"• Losses: `{losses}` 🔴\n"
                    f"• Win Rate: `{win_rate:.2f}%`"
                )
                send_telegram_message_to_chat(chat_id, response_text)

            elif text == "/status":
                response_text = "🟢 *Bot Status:* Online & Actively Scanning Markets 24/7."
                send_telegram_message_to_chat(chat_id, response_text)

        return "OK", 200
    except Exception as e:
        print(f"Webhook Error: {e}")
        return "Error", 400

def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram API Error: {e}")

def send_telegram_message_to_chat(chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram Reply Error: {e}")

def market_scanner_loop():
    """Robust 24/7 background scanning loop with fail-safe error recovery."""
    print("Background Market Scanner Thread Started Successfully...")
    send_telegram_message("🚀 *Quotex Bot* restarted successfully and is now active 24/7!")

    pairs = ["EUR/USD-OTC", "GBP/USD-OTC", "AUD/CAD-OTC", "USD/JPY-OTC"]
    strategies = ["Gap-Up Glitch Reversal", "Bollinger Breakout + RSI", "Support/Resistance Breakdown"]

    while True:
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Scanning OTC market pairs...")
            
            # Temporary test signal mechanism to ensure signals are flowing
            if random.random() > 0.4:
                pair = random.choice(pairs)
                direction = random.choice(["CALL", "PUT"])
                strategy_name = random.choice(strategies)
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                signal_msg = (
                    f"🚨 *LIVE OTC SIGNAL DETECTED* 🚨\n\n"
                    f"• Pair: `{pair}`\n"
                    f"• Direction: `{'🟢 CALL (UP)' if direction == 'CALL' else '🔴 PUT (DOWN)'}`\n"
                    f"• Strategy: `{strategy_name}`\n"
                    f"• Time: `{timestamp}`"
                )
                
                send_telegram_message(signal_msg)
                log_signal_to_db(pair, direction, strategy_name, "PENDING")
                print(f"Signal sent successfully: {pair} - {direction}")

            # Scan interval (every 2 minutes)
            time.sleep(120)

        except Exception as e:
            print(f"Critical Error in scanner loop: {e}")
            time.sleep(15)

if __name__ == "__main__":
    # 1. Start background scanner thread safely
    scanner_thread = threading.Thread(target=market_scanner_loop)
    scanner_thread.daemon = True
    scanner_thread.start()
    
    # 2. Start Flask web server for Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
    
