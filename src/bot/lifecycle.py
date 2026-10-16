import asyncio
import logging
import pandas as pd
from src.bot.risk_manager import RiskManager

class TradeLifecycleManager:
    """
    تدير الصفقة بإجمالي 100% من البوزيشن بدون جني أرباح جزئي:
    1. قبل TP1: رفع SL تحت أقرب قاع وإلغاء TP1 للاحتفاظ بكامل الكمية.
    2. قبل TP2: رفع SL تحت أقرب قاع تاريخي وإلغاء TP2.
    3. بعد TP2: تشغيل Trailing Stop متحرك وقريب جداً من السعر الحالي (Profit Chasing).
    """
    def __init__(self, exchange, trade_package):
        self.exchange = exchange
        self.pkg = trade_package
        self.current_sl = trade_package['sl']
        self.stage = "INITIAL"

    async def monitor_and_manage(self):
        symbol = self.pkg['symbol']
        tp1 = self.pkg['tp1']
        tp2 = self.pkg['tp2']

        logging.info(f"🛡️ [Lifecycle] Monitoring 100% Position Ride for {symbol}...")

        while True:
            try:
                await asyncio.sleep(10)
                ticker = self.exchange.fetch_ticker(symbol)
                current_price = ticker['last']
                
                df_ohlcv = self.exchange.fetch_ohlcv(symbol, '15m', limit=50)
                df = pd.DataFrame(df_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                risk_mgr = RiskManager()
                nearest_low = risk_mgr.find_nearest_swing_low(df)

                # المرحلة 1: الاقتراب من TP1 (تأمين الستوب لوز تحت القاع وإلغاء الـ TP الجزئي)
                if self.stage == "INITIAL" and current_price >= tp1 * 0.992:
                    logging.info(f"🎯 [TP1 Structural Lock] Moving SL under swing low for {symbol} & keeping 100% position.")
                    self.current_sl = max(self.current_sl, nearest_low)
                    self.stage = "PASSED_TP1_PRE"

                # المرحلة 2: الاقتراب من TP2 (تأمين إضافي تحت قاع تاريخي وإلغاء TP2)
                elif self.stage == "PASSED_TP1_PRE" and current_price >= tp2 * 0.992:
                    logging.info(f"🚀 [TP2 Structural Lock] Upgrading SL before TP2 for {symbol}.")
                    self.current_sl = max(self.current_sl, nearest_low)
                    self.stage = "PASSED_TP2_PRE"

                # المرحلة 3: بعد TP2 (مطاردة الأرباح / Trailing متحرك بقريب من السعر)
                elif self.stage == "PASSED_TP2_PRE" and current_price > tp2:
                    tight_sl = current_price * 0.99
                    if tight_sl > self.current_sl:
                        self.current_sl = tight_sl
                        logging.info(f"🔥 [Profit Chasing] Trailing SL updated to {self.current_sl} for {symbol}")
                        self.stage = "TRAILING_ACTIVE"

            except Exception as e:
                logging.error(f"Error in Lifecycle Monitor for {symbol}: {e}")
                await asyncio.sleep(15)
