import pandas as pd
import pandas_ta as ta
import logging

class InstitutionalStrategyManager:
    def __init__(self, volume_surge_multiplier=1.8):
        self.volume_surge_multiplier = volume_surge_multiplier

    def evaluate_altcoin_momentum(self, df_4h: pd.DataFrame, df_1h: pd.DataFrame, df_15m: pd.DataFrame) -> dict:
        try:
            df_4h['sma_50'] = ta.sma(df_4h['close'], length=50)
            macro_trend = "BULLISH" if df_4h['close'].iloc[-1] > df_4h['sma_50'].iloc[-1] else "BEARISH"

            df_1h['rsi'] = ta.rsi(df_1h['close'], length=14)
            df_1h['vol_sma'] = df_1h['volume'].rolling(window=20).mean()
            
            is_volume_surge = df_1h['volume'].iloc[-1] >= (df_1h['vol_sma'].iloc[-1] * self.volume_surge_multiplier)
            recent_high = df_15m['high'].tail(20).max()
            current_price = df_15m['close'].iloc[-1]

            signal = "HOLD"
            strategy_used = "NONE"

            if current_price >= recent_high * 0.995 and is_volume_surge and macro_trend == "BULLISH":
                signal = "BUY_MOMENTUM_BREAKOUT"
                strategy_used = "ADVENTURER_100_PERCENT_RIDING"

            return {
                "macro_trend": macro_trend,
                "is_volume_surge": is_volume_surge,
                "rsi": df_1h['rsi'].iloc[-1],
                "signal": signal,
                "strategy_used": strategy_used,
                "current_price": current_price
            }
        except Exception as e:
            logging.error(f"Error in strategy evaluation: {e}")
            return {"signal": "HOLD", "strategy_used": "ERROR"}
