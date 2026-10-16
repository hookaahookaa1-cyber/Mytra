import pandas as pd
import numpy as np
import logging

class RiskManager:
    def __init__(self, max_risk_per_trade=0.01, min_order_usdt=5.0, window=5, buffer_percent=0.002):
        self.max_risk_per_trade = max_risk_per_trade
        self.min_order_usdt = min_order_usdt  # الحد الأدنى للأمر لتفادي رفض المنصة للمحافظ الصغيرة
        self.window = window
        self.buffer_percent = buffer_percent

    def find_nearest_swing_low(self, df: pd.DataFrame) -> float:
        try:
            if df is None or len(df) < self.window:
                return float(df['low'].iloc[-1] * 0.98) if df is not None and not df.empty else 0.0

            df['is_swing_low'] = df['low'] == df['low'].rolling(window=self.window, center=True).min()
            swing_lows = df[df['is_swing_low']]['low']
            nearest_low = swing_lows.iloc[-1] if not swing_lows.empty else df['low'].tail(self.window).min()
            return float(nearest_low * (1 - self.buffer_percent))
        except Exception as e:
            logging.error(f"Error calculating swing low: {e}")
            return float(df['low'].iloc[-1] * 0.98)

    def calculate_position_size(self, account_balance: float, entry_price: float, stop_loss_price: float, leverage: int = 10) -> float:
        risk_amount = account_balance * self.max_risk_per_trade
        price_risk = abs(entry_price - stop_loss_price)
        
        position_value = (risk_amount / price_risk) * entry_price if price_risk > 0 else self.min_order_usdt
        if position_value < self.min_order_usdt:
            position_value = self.min_order_usdt  # حماية المحافظ الصغيرة برفع حجم العقد للحد الأدنى للمنصة

        return float(position_value / entry_price)
