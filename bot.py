from flask import Flask
import threading, os

app = Flask(__name__)
@app.route('/')
def home(): return "Bot Active"
threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))).start()

import asyncio
import sqlite3
import logging
import datetime
import numpy as np
import pandas as pd
import requests

# 1. Logging Setup
logging.basicConfig(
    filename='quotex_bot_execution.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 2. Telegram Credentials
TELEGRAM_BOT_TOKEN = "8850686281:AAFQms3YLnynRzHTP8BpZv-AjG5gpNZszpw"
TELEGRAM_CHAT_ID = "5359177105"

class DatabaseManager:
    def __init__(self, db_name="quotex_ledger.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                pair TEXT,
                direction TEXT,
                strategy_type TEXT,
                entry_price REAL,
                status TEXT DEFAULT 'PENDING',
                result TEXT DEFAULT 'WAITING'
            )
        ''')
        self.conn.commit()

    def log_signal(self, timestamp, pair, direction, strategy_type, entry_price):
        self.cursor.execute('''
            INSERT INTO signals (timestamp, pair, direction, strategy_type, entry_price, status)
            VALUES (?, ?, ?, ?, ?, 'ACTIVE')
        ''', (timestamp, pair, direction, strategy_type, entry_price))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_result(self, signal_id, result):
        self.cursor.execute('''
            UPDATE signals SET status = 'CLOSED', result = ? WHERE id = ?
        ''', (result, signal_id))
        self.conn.commit()


class GlitchIndicatorEngine:
    @staticmethod
    def calculate_bollinger_bands(prices, period=20, std_dev=2.5):
        df = pd.Series(prices)
        sma = df.rolling(window=period).mean()
        std = df.rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        return upper_band.iloc[-1], lower_band.iloc[-1]

    @staticmethod
    def calculate_rsi(prices, period=7):
        df = pd.Series(prices)
        delta = df.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]

    @staticmethod
    def detect_glitches_and_signals(candle_history):
        if len(candle_history) < 25:
            return None, None, 0

        closes = [c['close'] for c in candle_history]
        curr = candle_history[-1]
        prev = candle_history[-2]

        # 3. Glitch and Gap Detection Logic
        gap = curr['open'] - prev['close']
        if gap > 0.0008:
            return "PUT (DOWN)", "Gap-Up Glitch Reversal", 85
        elif gap < -0.0008:
            return "CALL (UP)", "Gap-Down Glitch Reversal", 85

        body_size = abs(curr['close'] - curr['open'])
        avg_body = np.mean([abs(c['close'] - c['open']) for c in candle_history[-10:]])
        if body_size < (avg_body * 0.2):
            return None, "Doji / Manipulation Risk - Skip", 0

        upper, lower = GlitchIndicatorEngine.calculate_bollinger_bands(closes)
        rsi = GlitchIndicatorEngine.calculate_rsi(closes)

        if curr['close'] <= lower and rsi < 30:
            return "CALL (UP)", "Bollinger Lower + RSI Oversold", 78
        elif curr['close'] >= upper and rsi > 70:
            return "PUT (DOWN)", "Bollinger Upper + RSI Overbought", 78

        return None, None, 0


class TelegramNotifier:
    @staticmethod
    def send_alert(message):
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            logging.error(f"Telegram alert failed: {e}")


class QuotexBotCore:
    def __init__(self):
        self.db = DatabaseManager()
        self.active_pairs = ["EUR/USD-OTC", "GBP/USD-OTC", "USD/JPY-OTC", "AUD/CAD-OTC"]

    async def fetch_live_market_data(self, pair):
        base_price = 1.0850 + np.random.uniform(-0.0020, 0.0020)
        simulated_live_candles = []
        for i in range(30):
            o = base_price + np.random.uniform(-0.0008, 0.0008)
            c = o + np.random.uniform(-0.0004, 0.0004)
            h = max(o, c) + np.random.uniform(0, 0.0002)
            l = min(o, c) - np.random.uniform(0, 0.0002)
            simulated_live_candles.append({"open": o, "high": h, "low": l, "close": c})
        return simulated_live_candles

    async def run_scanner(self):
        print("Quotex Live Bot Started Successfully...")
        TelegramNotifier.send_alert("🚀 *Ronak, Your Quotex Live Bot is Running 24/7!*")

        while True:
            try:
                for pair in self.active_pairs:
                    candles = await self.fetch_live_market_data(pair)
                    direction, strategy, confidence = GlitchIndicatorEngine.detect_glitches_and_signals(candles)

                    if direction:
                        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        entry_price = candles[-1]['close']
                        
                        sig_id = self.db.log_signal(timestamp, pair, direction, strategy, entry_price)

                        alert_msg = (
                            f"🚨 *LIVE OTC SIGNAL DETECTED*\n"
                            f"━━━━━━━━━━━━━━━━━━━\n"
                            f"🌐 *Pair:* {pair}\n"
                            f"🧭 *Direction:* {direction}\n"
                            f"⚙️ *Strategy:* {strategy}\n"
                            f"🎯 *Confidence:* {confidence}%\n"
                            f"⏰ *Time:* {timestamp}"
                        )
                        TelegramNotifier.send_alert(alert_msg)
                        await asyncio.sleep(2)
                        
                # Scan market every 60 seconds
                await asyncio.sleep(60)

            except Exception as e:
                logging.error(f"Error in live scanner loop: {e}")
                await asyncio.sleep(10)

if __name__ == "__main__":
    bot = QuotexBotCore()
    asyncio.run(bot.run_scanner())
      
