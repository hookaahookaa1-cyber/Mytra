import os
import time
import io
import ccxt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import logging
import asyncio

from src.bot.risk_manager import RiskManager
from src.bot.strategies import InstitutionalStrategyManager
from src.bot.lifecycle import TradeLifecycleManager

class MasterTradingEngine:
    def __init__(self, is_demo=True, auto_mode=False):
        self.is_demo = is_demo
        self.auto_mode = auto_mode
        self.risk_manager = RiskManager()
        self.strategy_manager = InstitutionalStrategyManager()
        
        self.exchange_id = os.getenv("EXCHANGE_ID", "binance").lower()
        api_key = os.getenv("API_KEY", "")
        secret_key = os.getenv("SECRET_KEY", "")
        passphrase = os.getenv("PASSPHRASE", "")
        
        try:
            exchange_class = getattr(ccxt, self.exchange_id)
            config = {'apiKey': api_key, 'secret': secret_key, 'enableRateLimit': True}
            if passphrase:
                config['password'] = passphrase
                
            self.exchange = exchange_class(config)
            if self.is_demo and self.exchange.has['sandbox']:
                self.exchange.set_sandbox_mode(True)
                logging.info(f"🧪 Connected to [{self.exchange_id.upper}}] in DEMO mode.")
            else:
                logging.info(f"💰 Connected to [{self.exchange_id.upper}}] in LIVE mode.")
        except Exception as e:
            logging.error(f"❌ Failed to initialize exchange {self.exchange_id}: {e}")
            self.exchange = None

    def fetch_real_ohlcv(self, symbol="SOL/USDT", timeframe="15m", limit=100):
        if not self.exchange:
            return self.generate_mock_data()
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logging.error(f"Error fetching OHLCV for {symbol}: {e}")
            return self.generate_mock_data()

    def generate_mock_data(self):
        dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='15min')
        prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
        return pd.DataFrame({
            'timestamp': dates, 'open': prices, 'high': prices + 1, 'low': prices - 1, 'close': prices, 'volume': 20000
        })

    def generate_chart_image(self, df: pd.DataFrame) -> io.BytesIO:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(df['timestamp'], df['close'], label='Close Price', color='#00ffcc', linewidth=2)
        ax.set_title(f'Khtb Center - {self.exchange_id.upper()} 15m Chart', color='white', fontsize=14)
        ax.set_facecolor('#1a1a1a')
        fig.patch.set_facecolor('#111111')
        ax.tick_params(colors='white')
        ax.grid(True, color='#333333', linestyle='--', alpha=0.5)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', facecolor=fig.get_facecolor())
        buf.seek(0)
        plt.close(fig)
        return buf

    def evaluate_pair(self, symbol="SOL/USDT"):
        df_4h = self.fetch_real_ohlcv(symbol, "4h")
        df_1h = self.fetch_real_ohlcv(symbol, "1h")
        df_15m = self.fetch_real_ohlcv(symbol, "15m")

        analysis = self.strategy_manager.evaluate_altcoin_momentum(df_4h, df_1h, df_15m)
        if analysis.get("signal") != "HOLD":
            current_price = analysis.get("current_price")
            sl = self.risk_manager.find_nearest_swing_low(df_15m)
            
            balance = 1000.0
            try:
                if self.exchange:
                    acc = self.exchange.fetch_balance()
                    balance = acc['USDT']['free'] if 'USDT' in acc else 1000.0
            except Exception:
                pass

            units = self.risk_manager.calculate_position_size(balance, current_price, sl, leverage=10)
            return {
                "symbol": symbol, "action": analysis.get("signal"), "entry": current_price,
                "sl": sl, "tp1": current_price * 1.025, "tp2": current_price * 1.05,
                "units": units, "leverage": 10, "strategy": analysis.get("strategy_used"), "df_15m": df_15m
            }
        return None

    def execute_live_trade(self, pkg, custom_leverage=None):
        lev = custom_leverage or pkg['leverage']
        symbol = pkg['symbol']
        units = pkg['units']
        side = 'buy' if 'BUY' in pkg['action'] else 'sell'
        
        logging.info(f"🚀 [EXECUTION] {side.upper()} on {self.exchange_id.upper()} | {symbol} | Units: {units} | Lev: {lev}x")
        if not self.exchange:
            return True

        try:
            self.exchange.set_leverage(lev, symbol)
            self.exchange.create_order(symbol, 'market', side, units)
            lifecycle = TradeLifecycleManager(self.exchange, pkg)
            asyncio.create_task(lifecycle.monitor_and_manage())
            return True
        except Exception as e:
            logging.error(f"❌ Execution error: {e}")
            return False
