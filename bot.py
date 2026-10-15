import threading
import time
import os
import sqlite3
import requests
import numpy as np
import pandas as pd
from datetime import datetime
from flask import Flask, request

# --- CONFIGURATION & CREDENTIALS ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")

app = Flask(__name__)

# --- DATABASE SETUP FOR PERSISTENT TRACKING ---
def init_db():
    """Initialize SQLite database for tracking signals, wins, and losses persistently."""
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

init_db()

def log_signal_to_db(pair, direction, strategy, status="PENDING"):
    """Save generated signal into the database."""
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
    """Fetch win/loss and total signal statistics."""
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

# --- FLASK ROUTES FOR RENDER & UPTIMEROBOT ---
@app.route('/')
def home():
    return "Quotex OTC Fully Loaded Trading Bot is Running Live 24/7!"

@app.route('/health')
def health_check():
    """Health check endpoint to keep Render instance active."""
    return {"status": "healthy", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, 200

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    """Handle incoming Telegram commands (/stats, /status)."""
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
                response_text = "🟢 *Bot Status:* Online & Actively Scanning Breakouts, Breakdowns & Indicators 24/7."
                send_telegram_message_to_chat(chat_id, response_text)

        return "OK", 200
    except Exception as e:
        print(f"Webhook Error: {e}")
        return "Error", 400

def send_telegram_message(message):
    """Send signal alert to main Telegram chat."""
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
    """Send reply to specific chat ID for commands."""
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

# --- TRADING, BREAKOUT, BREAKDOWN & INDICATOR LOGIC ---
def analyze_market_and_indicators(prices):
    """
    Simulates or computes Bollinger Bands, RSI, Breakout, and Breakdown logic.
    Returns signal direction and strategy name if condition met, else None.
    """
    if len(prices) < 14:
        return None, None

    # Convert to pandas Series for calculations
    series = pd.Series(prices)
    
    # 1. RSI Calculation (14 period)
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    current_rsi = rsi.iloc[-1]

    # 2. Bollinger Bands Calculation (20 period, 2 std dev)
    sma = series.rolling(window=20).mean()
    std = series.rolling(window=20).std()
    upper_band = sma + (std * 2)
    lower_band = sma - (std * 2)
    
    current_price = series.iloc[-1]
    curr_upper = upper_band.iloc[-1]
    curr_lower = lower_band.iloc[-1]

    # 3. Breakout & Breakdown Strategy Logic
    # Breakout: Price crosses above upper Bollinger Band with RSI confirmation
    if current_price > curr_upper and current_rsi > 60:
        return "CALL", "Bollinger Breakout + RSI"
        
    # Breakdown: Price crosses below lower Bollinger Band with RSI confirmation
    elif current_price < curr_lower and current_rsi < 40:
        return "PUT", "Bollinger Breakdown + RSI"

    return None, None

def market_scanner_loop():
    """Continuous 24/7 background scanning loop for OTC markets."""
    print("Background Market Scanner Thread Started Successfully...")
    send_telegram_message("🚀 *Quotex Fully Loaded Bot* is LIVE 24/7 with Breakout, Breakdown & Indicator Strategies!")

    while True:
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S সিস্টेम वेळ')}] Scanning OTC market pairs for Breakouts & Breakdowns...")
            
            # --- Dummy / Live Price Feed simulation for testing indicators ---
            # (In production, replace this list with live fetched candle data from Quotex/API)
            simulated_prices = np.random.uniform(1.0800, 1.0950, 30).tolist()
            
            direction, strategy_name = analyze_market_and_indicators(simulated_prices)
            
            if direction and strategy_name:
                pair = "EURUSD-OTC"
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                # Format signal message for Telegram
                signal_msg = (
                    f"🚨 *QUOTEX OTC SIGNAL* 🚨\n\n"
                    f"• Pair: `{pair}`\n"
                    f"• Action: `{'🟢 CALL (UP)' if direction == 'CALL' else '🔴 PUT (DOWN)'}`\n"
                    f"• Strategy: `{strategy_name}`\n"
                    f"• Time: `{timestamp}`"
                )
                
                send_telegram_message(signal_msg)
                log_signal_to_db(pair, direction, strategy_name, "PENDING")
                print(f"Signal sent: {pair} - {direction} via {strategy_name}")

            # Scan interval (e.g., every 30 seconds)
            time.sleep(30)

        except Exception as e:
            print(f"Error in market scanner loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    # 1. Start market scanner on an independent background thread
    scanner_thread = threading.Thread(target=market_scanner_loop)
    scanner_thread.daemon = True
    scanner_thread.start()
    
    # 2. Start Flask web server for Render on port 10000
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
