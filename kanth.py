import os
import sys
import time
import json
import logging
import webbrowser
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import deque
from kiteconnect import KiteConnect

# ============================================================================
# CONFIGURATION
# ============================================================================

KITE_API_KEY = os.getenv('KITE_API_KEY', 'kq9r5pzkp8lc0m8o')
KITE_ACCESS_TOKEN = os.getenv('KITE_ACCESS_TOKEN', 'PQgjlOUGEVLoHUnvbo33YJ7zbyjQkhBt')
REFRESH_INTERVAL = int(os.getenv('REFRESH_INTERVAL', '5'))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class TechnicalIndicators:
    vwap: Optional[float] = None
    ema9: Optional[float] = None
    ema21: Optional[float] = None
    ema50: Optional[float] = None
    rsi14: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    atr14: Optional[float] = None
    adx: Optional[float] = None

@dataclass
class MarketBias:
    bias: Optional[str] = None
    confidence: int = 0
    strength: str = "Weak"
    signals: List[str] = None
    
    def __post_init__(self):
        if self.signals is None:
            self.signals = []

@dataclass
class OptionData:
    strike: float
    ce_oi: Optional[int] = None
    ce_chg_oi: Optional[int] = None
    ce_ltp: Optional[float] = None
    ce_iv: Optional[float] = None
    ce_volume: Optional[int] = None
    ce_delta: Optional[float] = None
    ce_gamma: Optional[float] = None
    ce_theta: Optional[float] = None
    ce_vega: Optional[float] = None
    pe_oi: Optional[int] = None
    pe_chg_oi: Optional[int] = None
    pe_ltp: Optional[float] = None
    pe_iv: Optional[float] = None
    pe_volume: Optional[int] = None
    pe_delta: Optional[float] = None
    pe_gamma: Optional[float] = None
    pe_theta: Optional[float] = None
    pe_vega: Optional[float] = None
    pcr: Optional[float] = None
    max_pain: Optional[float] = None

# ============================================================================
# TECHNICAL ANALYSIS ENGINE
# ============================================================================

class TechnicalAnalyzer:
    """Advanced technical analysis with multiple indicators"""
    
    @staticmethod
    def compute_vwap(candles: List[Dict]) -> Tuple[Optional[float], Optional[float]]:
        """Compute Volume Weighted Average Price"""
        total_pv = 0.0
        total_v = 0.0
        last_price = None
        
        for c in candles:
            close = c.get('close')
            volume = c.get('volume')
            if close is None or volume in (None, 0):
                continue
            try:
                close = float(close)
                volume = float(volume)
                total_pv += close * volume
                total_v += volume
                last_price = close
            except Exception:
                continue
                
        if total_v <= 0:
            return None, last_price
        return total_pv / total_v, last_price
    
    @staticmethod
    def compute_ema(values: List[float], period: int) -> Optional[float]:
        """Compute Exponential Moving Average"""
        if not values or period <= 0 or len(values) < period:
            return None
            
        k = 2.0 / (period + 1.0)
        ema_val = None
        
        for v in values:
            try:
                v = float(v)
                if ema_val is None:
                    ema_val = v
                else:
                    ema_val = (v - ema_val) * k + ema_val
            except Exception:
                continue
        return ema_val
    
    @staticmethod
    def compute_sma(values: List[float], period: int) -> Optional[float]:
        """Compute Simple Moving Average"""
        if not values or len(values) < period:
            return None
        return sum(values[-period:]) / period
    
    @staticmethod
    def compute_rsi(values: List[float], period: int = 14) -> Optional[float]:
        """Compute Relative Strength Index"""
        if not values or len(values) < period + 1:
            return None
            
        gains = []
        losses = []
        
        for i in range(1, len(values)):
            try:
                change = float(values[i]) - float(values[i-1])
                gains.append(max(change, 0.0))
                losses.append(max(-change, 0.0))
            except Exception:
                continue
                
        if len(gains) < period:
            return None
            
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
        if avg_loss == 0:
            return 100.0
            
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))
    
    @staticmethod
    def compute_macd(values: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[Optional[float], Optional[float]]:
        """Compute MACD and Signal line"""
        if not values or len(values) < slow:
            return None, None
            
        ema_fast = TechnicalAnalyzer.compute_ema(values, fast)
        ema_slow = TechnicalAnalyzer.compute_ema(values, slow)
        
        if ema_fast is None or ema_slow is None:
            return None, None
            
        macd = ema_fast - ema_slow
        
        # Compute signal line (9-period EMA of MACD)
        macd_values = [macd]
        signal_line = TechnicalAnalyzer.compute_ema(macd_values, signal)
        
        return macd, signal_line
    
    @staticmethod
    def compute_bollinger_bands(values: List[float], period: int = 20, std_dev: float = 2.0) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Compute Bollinger Bands"""
        if not values or len(values) < period:
            return None, None, None
            
        sma = TechnicalAnalyzer.compute_sma(values, period)
        if sma is None:
            return None, None, None
            
        recent = values[-period:]
        variance = sum((x - sma) ** 2 for x in recent) / period
        std = variance ** 0.5
        
        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        
        return upper, sma, lower
    
    @staticmethod
    def compute_atr(candles: List[Dict], period: int = 14) -> Optional[float]:
        """Compute Average True Range"""
        if not candles or len(candles) < period + 1:
            return None
            
        true_ranges = []
        for i in range(1, len(candles)):
            try:
                high = float(candles[i].get('high', 0))
                low = float(candles[i].get('low', 0))
                prev_close = float(candles[i-1].get('close', 0))
                
                tr = max(
                    high - low,
                    abs(high - prev_close),
                    abs(low - prev_close)
                )
                true_ranges.append(tr)
            except Exception:
                continue
                
        if len(true_ranges) < period:
            return None
            
        return sum(true_ranges[-period:]) / period
    
    @staticmethod
    def compute_adx(candles: List[Dict], period: int = 14) -> Optional[float]:
        """Compute Average Directional Index"""
        if not candles or len(candles) < period + 1:
            return None
            
        plus_dm = []
        minus_dm = []
        
        for i in range(1, len(candles)):
            try:
                high = float(candles[i].get('high', 0))
                low = float(candles[i].get('low', 0))
                prev_high = float(candles[i-1].get('high', 0))
                prev_low = float(candles[i-1].get('low', 0))
                
                up_move = high - prev_high
                down_move = prev_low - low
                
                plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0)
                minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0)
            except Exception:
                continue
                
        if len(plus_dm) < period:
            return None
            
        atr = TechnicalAnalyzer.compute_atr(candles, period)
        if not atr or atr == 0:
            return None
            
        plus_di = (sum(plus_dm[-period:]) / period / atr) * 100
        minus_di = (sum(minus_dm[-period:]) / period / atr) * 100
        
        dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100 if (plus_di + minus_di) != 0 else 0
        
        return dx

    @staticmethod
    def analyze_full(candles: List[Dict], closes: List[float]) -> TechnicalIndicators:
        """Perform complete technical analysis"""
        indicators = TechnicalIndicators()
        
        if not candles or not closes:
            return indicators
            
        # Price-based indicators
        indicators.vwap, _ = TechnicalAnalyzer.compute_vwap(candles)
        indicators.ema9 = TechnicalAnalyzer.compute_ema(closes, 9)
        indicators.ema21 = TechnicalAnalyzer.compute_ema(closes, 21)
        indicators.ema50 = TechnicalAnalyzer.compute_ema(closes, 50)
        indicators.rsi14 = TechnicalAnalyzer.compute_rsi(closes, 14)
        
        # MACD
        indicators.macd, indicators.macd_signal = TechnicalAnalyzer.compute_macd(closes)
        
        # Bollinger Bands
        indicators.bb_upper, indicators.bb_middle, indicators.bb_lower = TechnicalAnalyzer.compute_bollinger_bands(closes)
        
        # Volatility & Trend
        indicators.atr14 = TechnicalAnalyzer.compute_atr(candles, 14)
        indicators.adx = TechnicalAnalyzer.compute_adx(candles, 14)
        
        return indicators

# ============================================================================
# MARKET BIAS ANALYZER
# ============================================================================

class BiasAnalyzer:
    """Enhanced market bias determination with multiple timeframes"""
    
    @staticmethod
    def analyze_intraday(indicators: TechnicalIndicators, last_price: Optional[float]) -> MarketBias:
        """Analyze intraday bias with enhanced logic"""
        bias = MarketBias()
        votes = 0
        signals = []
        
        # VWAP analysis
        if indicators.vwap is not None and last_price is not None:
            if last_price > indicators.vwap:
                votes += 1
                signals.append("Price > VWAP (Bullish)")
            else:
                votes -= 1
                signals.append("Price < VWAP (Bearish)")
        
        # EMA crossover
        if indicators.ema9 is not None and indicators.ema21 is not None:
            if indicators.ema9 > indicators.ema21:
                votes += 1
                signals.append("EMA9 > EMA21 (Bullish)")
            else:
                votes -= 1
                signals.append("EMA9 < EMA21 (Bearish)")
        
        # RSI levels
        if indicators.rsi14 is not None:
            if indicators.rsi14 >= 60:
                votes += 1
                signals.append(f"RSI {indicators.rsi14:.1f} (Overbought/Strong)")
            elif indicators.rsi14 <= 40:
                votes -= 1
                signals.append(f"RSI {indicators.rsi14:.1f} (Oversold/Weak)")
            else:
                signals.append(f"RSI {indicators.rsi14:.1f} (Neutral)")
        
        # MACD
        if indicators.macd is not None and indicators.macd_signal is not None:
            if indicators.macd > indicators.macd_signal:
                votes += 1
                signals.append("MACD > Signal (Bullish)")
            else:
                votes -= 1
                signals.append("MACD < Signal (Bearish)")
        
        # Bollinger Bands
        if all([indicators.bb_upper, indicators.bb_lower, last_price]):
            if last_price > indicators.bb_upper:
                votes += 1
                signals.append("Price > BB Upper (Strong Bullish)")
            elif last_price < indicators.bb_lower:
                votes -= 1
                signals.append("Price < BB Lower (Strong Bearish)")
        
        # Determine bias
        total_signals = len([s for s in [indicators.vwap, indicators.ema9, indicators.rsi14, indicators.macd] if s is not None])
        
        if total_signals > 0:
            if votes >= 2:
                bias.bias = "Bullish"
                bias.strength = "Strong" if votes >= 3 else "Moderate"
            elif votes <= -2:
                bias.bias = "Bearish"
                bias.strength = "Strong" if votes <= -3 else "Moderate"
            else:
                bias.bias = "Neutral"
                bias.strength = "Weak"
            
            bias.confidence = min(abs(votes), total_signals)
            bias.signals = signals
        
        return bias
    
    @staticmethod
    def analyze_daily(indicators: TechnicalIndicators, last_price: Optional[float]) -> MarketBias:
        """Analyze daily/swing bias"""
        bias = MarketBias()
        votes = 0
        signals = []
        
        # EMA 50 trend
        if indicators.ema50 is not None and last_price is not None:
            if last_price > indicators.ema50:
                votes += 1
                signals.append("Price > EMA50 (Uptrend)")
            else:
                votes -= 1
                signals.append("Price < EMA50 (Downtrend)")
        
        # EMA 9/21 crossover
        if indicators.ema9 is not None and indicators.ema21 is not None:
            if indicators.ema9 > indicators.ema21:
                votes += 1
                signals.append("EMA9 > EMA21 (Short-term Bullish)")
            else:
                votes -= 1
                signals.append("EMA9 < EMA21 (Short-term Bearish)")
        
        # RSI
        if indicators.rsi14 is not None:
            if indicators.rsi14 >= 55:
                votes += 1
                signals.append(f"RSI {indicators.rsi14:.1f} (Bullish)")
            elif indicators.rsi14 <= 45:
                votes -= 1
                signals.append(f"RSI {indicators.rsi14:.1f} (Bearish)")
        
        # ADX for trend strength
        if indicators.adx is not None:
            if indicators.adx > 25:
                signals.append(f"ADX {indicators.adx:.1f} (Strong Trend)")
            else:
                signals.append(f"ADX {indicators.adx:.1f} (Weak Trend)")
        
        total_signals = 3
        
        if votes >= 2:
            bias.bias = "Bullish"
            bias.strength = "Strong" if votes >= 3 else "Moderate"
        elif votes <= -2:
            bias.bias = "Bearish"
            bias.strength = "Strong" if votes <= -3 else "Moderate"
        else:
            bias.bias = "Neutral"
            bias.strength = "Weak"
        
        bias.confidence = min(abs(votes), total_signals)
        bias.signals = signals
        
        return bias

# ============================================================================
# OPTION CHAIN METRICS
# ============================================================================

class OptionMetrics:
    """Calculate advanced option chain metrics"""
    
    @staticmethod
    def calculate_pcr(records: List[Dict]) -> float:
        """Calculate Put-Call Ratio"""
        total_pe_oi = sum(r.get('PE_OI', 0) or 0 for r in records)
        total_ce_oi = sum(r.get('CE_OI', 0) or 0 for r in records)
        
        if total_ce_oi == 0:
            return 0.0
        return total_pe_oi / total_ce_oi
    
    @staticmethod
    def calculate_max_pain(records: List[Dict], spot: float) -> Optional[float]:
        """Calculate Max Pain strike"""
        if not records or not spot:
            return None
            
        pain_map = {}
        
        for rec in records:
            strike = rec.get('strikePrice')
            ce_oi = rec.get('CE_OI', 0) or 0
            pe_oi = rec.get('PE_OI', 0) or 0
            
            if not strike:
                continue
                
            total_pain = 0
            
            # Calculate pain at this strike
            for test_rec in records:
                test_strike = test_rec.get('strikePrice')
                test_ce_oi = test_rec.get('CE_OI', 0) or 0
                test_pe_oi = test_rec.get('PE_OI', 0) or 0
                
                if not test_strike:
                    continue
                    
                # CE holders lose if price > strike
                if strike > test_strike:
                    total_pain += test_ce_oi * (strike - test_strike)
                    
                # PE holders lose if price < strike
                if strike < test_strike:
                    total_pain += test_pe_oi * (test_strike - strike)
            
            pain_map[strike] = total_pain
        
        if not pain_map:
            return None
            
        return min(pain_map.items(), key=lambda x: x[1])[0]
    
    @staticmethod
    def identify_support_resistance(records: List[Dict], spot: float) -> Dict:
        """Identify key support and resistance levels"""
        if not records or not spot:
            return {}
            
        # Find strikes with highest OI
        ce_oi_strikes = sorted(
            [(r.get('strikePrice'), r.get('CE_OI', 0) or 0) for r in records if r.get('CE_OI')],
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        pe_oi_strikes = sorted(
            [(r.get('strikePrice'), r.get('PE_OI', 0) or 0) for r in records if r.get('PE_OI')],
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        resistance_levels = [s for s, _ in ce_oi_strikes if s > spot]
        support_levels = [s for s, _ in pe_oi_strikes if s < spot]
        
        return {
            'resistance': resistance_levels[:2],
            'support': support_levels[:2]
        }

# ============================================================================
# KITE DATA FETCHER
# ============================================================================

class KiteDataFetcher:
    """Handles all Kite Connect API interactions"""
    
    def __init__(self, api_key: str, access_token: str):
        self.kite = KiteConnect(api_key=api_key)
        self.kite.set_access_token(access_token)
        self.instrument_token = 256265  # NIFTY 50
        
    def fetch_intraday_data(self) -> Tuple[List[Dict], List[float], Optional[float]]:
        """Fetch intraday minute candles"""
        try:
            today = datetime.now().date()
            start_dt = datetime.combine(today, datetime.min.time().replace(hour=9, minute=15))
            end_dt = datetime.now()
            
            data = self.kite.historical_data(
                self.instrument_token, start_dt, end_dt,
                interval="minute", continuous=False, oi=False
            )
            
            candles = []
            closes = []
            last_price = None
            
            for item in data:
                c = item.get('close')
                v = item.get('volume')
                h = item.get('high')
                l = item.get('low')
                
                if c is None or v in (None, 0):
                    continue
                    
                try:
                    c = float(c)
                    v = float(v)
                    h = float(h) if h else c
                    l = float(l) if l else c
                    
                    closes.append(c)
                    candles.append({'close': c, 'volume': v, 'high': h, 'low': l})
                    last_price = c
                except Exception:
                    continue
            
            return candles, closes, last_price
            
        except Exception as e:
            logger.error(f"Error fetching intraday data: {e}")
            return [], [], None
    
    def fetch_daily_data(self, days: int = 400) -> Tuple[List[Dict], List[float]]:
        """Fetch daily candles"""
        try:
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=days)
            
            data = self.kite.historical_data(
                self.instrument_token, start_dt, end_dt,
                interval="day", continuous=False, oi=False
            )
            
            candles = []
            closes = []
            
            for item in data:
                c = item.get('close')
                h = item.get('high')
                l = item.get('low')
                
                if c is None:
                    continue
                    
                try:
                    c = float(c)
                    h = float(h) if h else c
                    l = float(l) if l else c
                    
                    closes.append(c)
                    candles.append({'close': c, 'high': h, 'low': l})
                except Exception:
                    continue
            
            return candles, closes
            
        except Exception as e:
            logger.error(f"Error fetching daily data: {e}")
            return [], []
    
    def fetch_spot_price(self) -> Optional[float]:
        """Fetch current NIFTY spot price"""
        try:
            quotes = self.kite.quote(["NSE:NIFTY 50"])
            return quotes.get("NSE:NIFTY 50", {}).get("last_price")
        except Exception as e:
            logger.error(f"Error fetching spot price: {e}")
            return None
    
    def fetch_option_chain(self):
        """Fetch complete option chain data"""
        try:
            # Get spot price
            spot = self.fetch_spot_price()
            
            # Get intraday analysis
            intraday_candles, intraday_closes, last_price = self.fetch_intraday_data()
            if last_price:
                spot = last_price
            
            intraday_indicators = TechnicalAnalyzer.analyze_full(intraday_candles, intraday_closes)
            intraday_bias = BiasAnalyzer.analyze_intraday(intraday_indicators, last_price)
            
            # Get daily analysis
            daily_candles, daily_closes = self.fetch_daily_data()
            daily_indicators = TechnicalAnalyzer.analyze_full(daily_candles, daily_closes)
            daily_bias = BiasAnalyzer.analyze_daily(daily_indicators, daily_closes[-1] if daily_closes else None)
            
            # Get instruments
            instruments = self.kite.instruments("NFO")
            nifty_options = [
                i for i in instruments
                if i['name'] == 'NIFTY' and i['instrument_type'] in ['CE', 'PE']
            ]
            
            # Get expiries
            expiries = sorted(list(set([i['expiry'] for i in nifty_options])))
            
            def is_monthly_expiry(exp_date):
                if exp_date.month == 12:
                    next_month = datetime(exp_date.year + 1, 1, 1).date()
                else:
                    next_month = datetime(exp_date.year, exp_date.month + 1, 1).date()
                last_day = next_month - timedelta(days=1)
                while last_day.weekday() != 3:
                    last_day -= timedelta(days=1)
                return exp_date == last_day
            
            monthly_expiries = [e for e in expiries if is_monthly_expiry(e)]
            weekly_expiries = [e for e in expiries if not is_monthly_expiry(e)]
            
            nearest_weekly = weekly_expiries[0] if weekly_expiries else expiries[0]
            nearest_monthly = monthly_expiries[0] if monthly_expiries else expiries[0]
            
            # Build option records
            def build_records(expiry):
                opts = [i for i in nifty_options if i['expiry'] == expiry]
                strikes = sorted(list(set([i['strike'] for i in opts])))
                
                # Filter strikes around spot
                if spot:
                    strikes = [s for s in strikes if abs(s - spot) <= 1000]
                
                records = []
                for strike in strikes:
                    ce = next((i for i in opts if i['strike'] == strike and i['instrument_type'] == 'CE'), None)
                    pe = next((i for i in opts if i['strike'] == strike and i['instrument_type'] == 'PE'), None)
                    
                    ce_token = f"NFO:{ce['tradingsymbol']}" if ce else None
                    pe_token = f"NFO:{pe['tradingsymbol']}" if pe else None
                    
                    tokens = [t for t in [ce_token, pe_token] if t]
                    quote_data = self.kite.quote(tokens) if tokens else {}
                    
                    ce_data = quote_data.get(ce_token, {}) if ce_token else {}
                    pe_data = quote_data.get(pe_token, {}) if pe_token else {}
                    
                    # Calculate OI change
                    ce_oi = ce_data.get('oi', 0)
                    pe_oi = pe_data.get('oi', 0)
                    
                    record = {
                        'strikePrice': strike,
                        'CE_OI': ce_oi,
                        'CE_Chg_OI': ce_data.get('oi_day_high', 0) - ce_data.get('oi_day_low', 0) if ce_data.get('oi_day_high') else 0,
                        'CE_LTP': ce_data.get('last_price'),
                        'CE_Volume': ce_data.get('volume'),
                        'CE_IV': ce_data.get('last_price', 0) / spot * 100 if spot and ce_data.get('last_price') else None,
                        'PE_OI': pe_oi,
                        'PE_Chg_OI': pe_data.get('oi_day_high', 0) - pe_data.get('oi_day_low', 0) if pe_data.get('oi_day_high') else 0,
                        'PE_LTP': pe_data.get('last_price'),
                        'PE_Volume': pe_data.get('volume'),
                        'PE_IV': pe_data.get('last_price', 0) / spot * 100 if spot and pe_data.get('last_price') else None,
                    }
                    records.append(record)
                
                return records
            
            weekly_records = build_records(nearest_weekly)
            monthly_records = build_records(nearest_monthly)
            
            # Calculate metrics
            pcr_weekly = OptionMetrics.calculate_pcr(weekly_records)
            pcr_monthly = OptionMetrics.calculate_pcr(monthly_records)
            max_pain_weekly = OptionMetrics.calculate_max_pain(weekly_records, spot)
            max_pain_monthly = OptionMetrics.calculate_max_pain(monthly_records, spot)
            sr_levels = OptionMetrics.identify_support_resistance(weekly_records, spot)
            
            return {
                'timestamp': datetime.now().isoformat(),
                'weekly_expiry': nearest_weekly.strftime("%d-%b-%Y"),
                'monthly_expiry': nearest_monthly.strftime("%d-%b-%Y"),
                'weekly_records': weekly_records,
                'monthly_records': monthly_records,
                'nifty_spot': spot,
                'intraday_indicators': asdict(intraday_indicators),
                'daily_indicators': asdict(daily_indicators),
                'intraday_bias': asdict(intraday_bias),
                'daily_bias': asdict(daily_bias),
                'pcr_weekly': pcr_weekly,
                'pcr_monthly': pcr_monthly,
                'max_pain_weekly': max_pain_weekly,
                'max_pain_monthly': max_pain_monthly,
                'support_resistance': sr_levels,
            }
            
        except Exception as e:
            logger.error(f"Error fetching option chain: {e}")
            raise

# ============================================================================
# HTML RENDERER
# ============================================================================

class HTMLRenderer:
    """Enhanced HTML rendering with modern UI"""
    
    @staticmethod
    def get_lot_size() -> int:
        """Get NIFTY lot size"""
        try:
            lot_file = Path('lot_size.txt')
            if lot_file.exists():
                return int(lot_file.read_text().strip())
        except Exception:
            pass
        try:
            val = int(os.getenv('NIFTY_LOT_SIZE', '75'))
            if val > 0:
                return val
        except Exception:
            pass
        return 75
    
    @staticmethod
    def format_number(value, decimals: int = 2) -> str:
        """Format numbers with proper decimals"""
        if value in (None, ""):
            return ""
        try:
            number = float(value)
            if decimals == 0:
                return f"{int(round(number)):,}"
            return f"{number:,.{decimals}f}"
        except Exception:
            return str(value)
    
    @staticmethod
    def render_html(data: Dict, output_path: str = "option_chain_v2.html", open_browser: bool = True):
        """Render complete HTML dashboard"""
        
        # Extract data
        spot = data.get('nifty_spot')
        weekly_expiry = data.get('weekly_expiry')
        monthly_expiry = data.get('monthly_expiry')
        weekly_records = data.get('weekly_records', [])
        monthly_records = data.get('monthly_records', [])
        
        intraday_ind = data.get('intraday_indicators', {})
        daily_ind = data.get('daily_indicators', {})
        intraday_bias_data = data.get('intraday_bias', {})
        daily_bias_data = data.get('daily_bias', {})
        
        pcr_weekly = data.get('pcr_weekly', 0)
        pcr_monthly = data.get('pcr_monthly', 0)
        max_pain_weekly = data.get('max_pain_weekly')
        max_pain_monthly = data.get('max_pain_monthly')
        sr_levels = data.get('support_resistance', {})
        
        lot_size = HTMLRenderer.get_lot_size()
        
        # Build indicator status
        has_vwap = intraday_ind.get('vwap') is not None
        has_ema = intraday_ind.get('ema9') is not None and intraday_ind.get('ema21') is not None
        has_rsi = intraday_ind.get('rsi14') is not None
        has_macd = intraday_ind.get('macd') is not None
        ind_count = sum([has_vwap, has_ema, has_rsi, has_macd])
        
        if ind_count >= 4:
            ind_status = "All Active"
            ind_class = "pill-ok"
        elif ind_count > 0:
            ind_status = "Partial Active"
            ind_class = "pill-partial"
        else:
            ind_status = "Inactive"
            ind_class = "pill-off"
        
        # Bias info
        intraday_bias = intraday_bias_data.get('bias')
        intraday_conf = intraday_bias_data.get('confidence', 0)
        intraday_strength = intraday_bias_data.get('strength', 'Weak')
        
        daily_bias = daily_bias_data.get('bias')
        daily_conf = daily_bias_data.get('confidence', 0)
        daily_strength = daily_bias_data.get('strength', 'Weak')
        
        # Recommendation
        rec_text = ""
        rec_class = ""
        if intraday_bias == 'Bullish':
            rec_text = "Recommend: CE"
            rec_class = "pill-ce"
        elif intraday_bias == 'Bearish':
            rec_text = "Recommend: PE"
            rec_class = "pill-pe"
        
        # Build table rows
        def build_table_rows(records):
            rows = []
            for rec in records:
                strike = rec.get('strikePrice', 0)
                ce_ltp = rec.get('CE_LTP', 0) or 0
                pe_ltp = rec.get('PE_LTP', 0) or 0
                
                entry_ce = ce_ltp if ce_ltp else ""
                exit_ce = round(ce_ltp * 1.05, 2) if ce_ltp else ""
                sl_ce = round(ce_ltp * 0.97, 2) if ce_ltp else ""
                
                entry_pe = pe_ltp if pe_ltp else ""
                exit_pe = round(pe_ltp * 1.05, 2) if pe_ltp else ""
                sl_pe = round(pe_ltp * 0.97, 2) if pe_ltp else ""
                
                ce_chg_oi = rec.get('CE_Chg_OI', 0)
                pe_chg_oi = rec.get('PE_Chg_OI', 0)
                
                signal = "HOLD"
                row_class = ""
                
                # Signal logic
                if spot and intraday_ind.get('vwap'):
                    vwap_bullish = spot > intraday_ind['vwap']
                    
                    if ce_chg_oi > 0 and pe_chg_oi <= 0 and vwap_bullish:
                        signal = "BUY CE"
                        row_class = "row-buy-ce"
                    elif pe_chg_oi > 0 and ce_chg_oi <= 0 and not vwap_bullish:
                        signal = "BUY PE"
                        row_class = "row-buy-pe"
                
                row = f'''
                <tr class="{row_class}" data-strike="{strike}" data-signal="{signal}">
                    <td class="strike-cell">{HTMLRenderer.format_number(strike, 0)}</td>
                    <td>{HTMLRenderer.format_number(rec.get('CE_OI'), 0)}</td>
                    <td class="{"pos" if ce_chg_oi > 0 else "neg" if ce_chg_oi < 0 else ""}">{HTMLRenderer.format_number(ce_chg_oi, 0)}</td>
                    <td>{HTMLRenderer.format_number(ce_ltp, 2)}</td>
                    <td>{HTMLRenderer.format_number(rec.get('CE_Volume'), 0)}</td>
                    <td>{HTMLRenderer.format_number(rec.get('CE_IV'), 1)}</td>
                    <td>{HTMLRenderer.format_number(entry_ce, 2)}</td>
                    <td>{HTMLRenderer.format_number(exit_ce, 2)}</td>
                    <td>{HTMLRenderer.format_number(sl_ce, 2)}</td>
                    <td>{HTMLRenderer.format_number(rec.get('PE_OI'), 0)}</td>
                    <td class="{"pos" if pe_chg_oi > 0 else "neg" if pe_chg_oi < 0 else ""}">{HTMLRenderer.format_number(pe_chg_oi, 0)}</td>
                    <td>{HTMLRenderer.format_number(pe_ltp, 2)}</td>
                    <td>{HTMLRenderer.format_number(rec.get('PE_Volume'), 0)}</td>
                    <td>{HTMLRenderer.format_number(rec.get('PE_IV'), 1)}</td>
                    <td>{HTMLRenderer.format_number(entry_pe, 2)}</td>
                    <td>{HTMLRenderer.format_number(exit_pe, 2)}</td>
                    <td>{HTMLRenderer.format_number(sl_pe, 2)}</td>
                    <td class="signal-cell {"pos" if signal == "BUY CE" else "neg" if signal == "BUY PE" else ""}">{signal}</td>
                </tr>
                '''
                rows.append(row)
            return ''.join(rows)
        
        weekly_rows = build_table_rows(weekly_records)
        monthly_rows = build_table_rows(monthly_records)
        
        # Top trades
        def rank_trades(records):
            ce_trades = []
            pe_trades = []
            
            for rec in records:
                strike = rec.get('strikePrice', 0)
                ce_ltp = rec.get('CE_LTP', 0) or 0
                pe_ltp = rec.get('PE_LTP', 0) or 0
                ce_chg = rec.get('CE_Chg_OI', 0) or 0
                pe_chg = rec.get('PE_Chg_OI', 0) or 0
                
                if spot and strike:
                    dist = abs(strike - spot)
                    ce_score = (ce_chg / 1000) - (dist / 50)
                    pe_score = (pe_chg / 1000) - (dist / 50)
                    
                    if ce_score > 0:
                        ce_trades.append({
                            'strike': strike,
                            'ltp': ce_ltp,
                            'score': ce_score,
                            'exit': round(ce_ltp * 1.05, 2),
                            'sl': round(ce_ltp * 0.97, 2)
                        })
                    
                    if pe_score > 0:
                        pe_trades.append({
                            'strike': strike,
                            'ltp': pe_ltp,
                            'score': pe_score,
                            'exit': round(pe_ltp * 1.05, 2),
                            'sl': round(pe_ltp * 0.97, 2)
                        })
            
            ce_trades.sort(key=lambda x: x['score'], reverse=True)
            pe_trades.sort(key=lambda x: x['score'], reverse=True)
            
            return ce_trades[:5], pe_trades[:5]
        
        weekly_ce_top, weekly_pe_top = rank_trades(weekly_records)
        monthly_ce_top, monthly_pe_top = rank_trades(monthly_records)
        
        def trade_list_html(trades, side):
            if not trades:
                return '<li class="no-trades">No strong setups currently</li>'
            
            items = []
            for t in trades:
                items.append(f'''
                <li>
                    <span class="strike-badge">{HTMLRenderer.format_number(t["strike"], 0)}</span>
                    <span class="side-badge {side.lower()}">{side}</span>
                    Entry: <strong>{HTMLRenderer.format_number(t["ltp"], 2)}</strong> · 
                    Exit: {HTMLRenderer.format_number(t["exit"], 2)} · 
                    SL: {HTMLRenderer.format_number(t["sl"], 2)} · 
                    Lot: {lot_size} · 
                    Score: {HTMLRenderer.format_number(t["score"], 1)}
                </li>
                ''')
            return ''.join(items)
        
        # Signals list
        intraday_signals = intraday_bias_data.get('signals', [])
        daily_signals = daily_bias_data.get('signals', [])
        
        signals_html = ''
        if intraday_signals:
            signals_html = '<ul class="signals-list">' + ''.join([f'<li>{s}</li>' for s in intraday_signals]) + '</ul>'
        
        daily_signals_html = ''
        if daily_signals:
            daily_signals_html = '<ul class="signals-list">' + ''.join([f'<li>{s}</li>' for s in daily_signals]) + '</ul>'
        
        # Generate HTML
        html = f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Advanced Nifty 50 Option Chain Analyzer</title>
    <style>
        :root {{
            --bg: #0a0e1a;
            --card: #0f1420;
            --header: #13182a;
            --border: #1e2639;
            --text: #e5e7eb;
            --muted: #9ca3af;
            --accent: #3b82f6;
            --pos: #10b981;
            --neg: #ef4444;
            --neutral: #f59e0b;
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
            padding: 24px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 4px 20px rgba(59, 130, 246, 0.3);
        }}
        
        h1 {{
            font-size: 28px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .subtitle {{
            color: rgba(255, 255, 255, 0.8);
            font-size: 14px;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin: 16px 0;
        }}
        
        .metric-card {{
            background: rgba(255, 255, 255, 0.1);
            padding: 12px 16px;
            border-radius: 8px;
            backdrop-filter: blur(10px);
        }}
        
        .metric-label {{
            font-size: 12px;
            color: rgba(255, 255, 255, 0.7);
            margin-bottom: 4px;
        }}
        
        .metric-value {{
            font-size: 20px;
            font-weight: 600;
            font-variant-numeric: tabular-nums;
        }}
        
        .pill {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-left: 8px;
        }}
        
        .pill-ok {{ background: rgba(16, 185, 129, 0.2); color: var(--pos); border: 1px solid var(--pos); }}
        .pill-partial {{ background: rgba(245, 158, 11, 0.2); color: var(--neutral); border: 1px solid var(--neutral); }}
        .pill-off {{ background: rgba(107, 114, 128, 0.2); color: var(--muted); border: 1px solid var(--muted); }}
        .pill-ce {{ background: rgba(16, 185, 129, 0.2); color: var(--pos); border: 1px solid var(--pos); }}
        .pill-pe {{ background: rgba(239, 68, 68, 0.2); color: var(--neg); border: 1px solid var(--neg); }}
        
        .card {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }}
        
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border);
        }}
        
        .card-title {{
            font-size: 18px;
            font-weight: 600;
        }}
        
        .bias-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-bottom: 20px;
        }}
        
        .bias-card {{
            background: var(--card);
            border: 2px solid var(--border);
            border-radius: 12px;
            padding: 20px;
        }}
        
        .bias-card.bullish {{ border-color: var(--pos); }}
        .bias-card.bearish {{ border-color: var(--neg); }}
        .bias-card.neutral {{ border-color: var(--neutral); }}
        
        .bias-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}
        
        .bias-title {{
            font-size: 16px;
            font-weight: 600;
            color: var(--muted);
        }}
        
        .bias-value {{
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 8px;
        }}
        
        .bias-value.bullish {{ color: var(--pos); }}
        .bias-value.bearish {{ color: var(--neg); }}
        .bias-value.neutral {{ color: var(--neutral); }}
        
        .confidence-bar {{
            height: 6px;
            background: var(--border);
            border-radius: 3px;
            overflow: hidden;
            margin: 8px 0;
        }}
        
        .confidence-fill {{
            height: 100%;
            transition: width 0.3s ease;
        }}
        
        .confidence-fill.bullish {{ background: var(--pos); }}
        .confidence-fill.bearish {{ background: var(--neg); }}
        .confidence-fill.neutral {{ background: var(--neutral); }}
        
        .signals-list {{
            list-style: none;
            font-size: 13px;
            color: var(--muted);
        }}
        
        .signals-list li {{
            padding: 6px 0;
            border-bottom: 1px solid var(--border);
        }}
        
        .signals-list li:last-child {{
            border-bottom: none;
        }}
        
        .trades-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 16px;
            margin-bottom: 20px;
        }}
        
        .trades-column {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
        }}
        
        .trades-column.ce {{ border-left: 3px solid var(--pos); }}
        .trades-column.pe {{ border-left: 3px solid var(--neg); }}
        
        .trades-title {{
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .trades-title.ce {{ color: var(--pos); }}
        .trades-title.pe {{ color: var(--neg); }}
        
        .trades-column ul {{
            list-style: none;
        }}
        
        .trades-column li {{
            padding: 10px;
            margin-bottom: 8px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 6px;
            font-size: 13px;
            line-height: 1.6;
        }}
        
        .trades-column li.no-trades {{
            color: var(--muted);
            font-style: italic;
            text-align: center;
        }}
        
        .strike-badge {{
            display: inline-block;
            background: var(--accent);
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 13px;
        }}
        
        .side-badge {{
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: 700;
        }}
        
        .side-badge.ce {{ background: var(--pos); color: white; }}
        .side-badge.pe {{ background: var(--neg); color: white; }}
        
        .table-container {{
            overflow-x: auto;
            border-radius: 8px;
            border: 1px solid var(--border);
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        
        thead {{
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        
        thead th {{
            background: var(--header);
            color: var(--muted);
            font-weight: 600;
            text-align: right;
            padding: 12px 10px;
            border-bottom: 2px solid var(--border);
            white-space: nowrap;
        }}
        
        tbody td {{
            padding: 10px;
            border-bottom: 1px solid var(--border);
            text-align: right;
            font-variant-numeric: tabular-nums;
        }}
        
        tbody tr:hover {{
            background: rgba(59, 130, 246, 0.05);
        }}
        
        tbody tr.row-buy-ce {{
            background: rgba(16, 185, 129, 0.08);
        }}
        
        tbody tr.row-buy-pe {{
            background: rgba(239, 68, 68, 0.08);
        }}
        
        .strike-cell {{
            font-weight: 600;
            color: var(--accent);
        }}
        
        .signal-cell {{
            font-weight: 600;
        }}
        
        .pos {{ color: var(--pos); }}
        .neg {{ color: var(--neg); }}
        
        .btn {{
            background: var(--accent);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.2s;
        }}
        
        .btn:hover {{
            background: #2563eb;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
        }}
        
        .toolbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }}
        
        .toast-container {{
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
            display: flex;
            flex-direction: column;
            gap: 10px;
            max-width: 400px;
        }}
        
        .toast {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
            animation: slideIn 0.3s ease;
        }}
        
        @keyframes slideIn {{
            from {{
                transform: translateX(400px);
                opacity: 0;
            }}
            to {{
                transform: translateX(0);
                opacity: 1;
            }}
        }}
        
        .toast.ce {{ border-left: 4px solid var(--pos); }}
        .toast.pe {{ border-left: 4px solid var(--neg); }}
        
        .toast-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}
        
        .toast-title {{
            font-weight: 600;
            font-size: 14px;
        }}
        
        .toast-title.ce {{ color: var(--pos); }}
        .toast-title.pe {{ color: var(--neg); }}
        
        .toast-close {{
            cursor: pointer;
            color: var(--muted);
            font-size: 18px;
            line-height: 1;
        }}
        
        .toast-body {{
            font-size: 13px;
            color: var(--muted);
        }}
        
        .scroll-top {{
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: var(--accent);
            color: white;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 4px 16px rgba(59, 130, 246, 0.4);
            opacity: 0;
            pointer-events: none;
            transition: all 0.3s;
        }}
        
        .scroll-top.visible {{
            opacity: 1;
            pointer-events: all;
        }}
        
        .scroll-top:hover {{
            transform: translateY(-3px);
            box-shadow: 0 6px 20px rgba(59, 130, 246, 0.6);
        }}
        
        .indicators-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 16px;
        }}
        
        .indicator-box {{
            background: rgba(255, 255, 255, 0.03);
            padding: 12px;
            border-radius: 6px;
            border-left: 3px solid var(--accent);
        }}
        
        .indicator-name {{
            font-size: 12px;
            color: var(--muted);
            margin-bottom: 4px;
        }}
        
        .indicator-value {{
            font-size: 18px;
            font-weight: 600;
        }}
        
        .tabs {{
            display: flex;
            gap: 8px;
            margin-bottom: 16px;
            border-bottom: 2px solid var(--border);
        }}
        
        .tab {{
            padding: 12px 24px;
            cursor: pointer;
            border: none;
            background: transparent;
            color: var(--muted);
            font-weight: 600;
            border-bottom: 2px solid transparent;
            margin-bottom: -2px;
            transition: all 0.2s;
        }}
        
        .tab.active {{
            color: var(--accent);
            border-bottom-color: var(--accent);
        }}
        
        .tab-content {{
            display: none;
        }}
        
        .tab-content.active {{
            display: block;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>
                🎯 Advanced Nifty 50 Option Chain Analyzer
                <span class="pill {ind_class}">{ind_status}</span>
            </h1>
            <div class="subtitle">Real-time analysis with advanced technical indicators</div>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">NIFTY Spot</div>
                    <div class="metric-value">{HTMLRenderer.format_number(spot, 2)}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">PCR (Weekly)</div>
                    <div class="metric-value">{HTMLRenderer.format_number(pcr_weekly, 3)}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Max Pain (Weekly)</div>
                    <div class="metric-value">{HTMLRenderer.format_number(max_pain_weekly, 0)}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Lot Size</div>
                    <div class="metric-value">{lot_size}</div>
                </div>
            </div>
        </div>
        
        <div class="bias-grid">
            <div class="bias-card {intraday_bias.lower() if intraday_bias else "neutral"}">
                <div class="bias-header">
                    <div class="bias-title">📊 Intraday Bias</div>
                    {f'<span class="{rec_class} pill">{rec_text}</span>' if rec_text else ''}
                </div>
                <div class="bias-value {intraday_bias.lower() if intraday_bias else "neutral"}">
                    {intraday_bias or "Neutral"} ({intraday_strength})
                </div>
                <div class="confidence-bar">
                    <div class="confidence-fill {intraday_bias.lower() if intraday_bias else "neutral"}" 
                         style="width: {intraday_conf * 33.33}%"></div>
                </div>
                <small>Confidence: {intraday_conf}/3</small>
                {signals_html}
            </div>
            
            <div class="bias-card {daily_bias.lower() if daily_bias else "neutral"}">
                <div class="bias-header">
                    <div class="bias-title">📈 Daily/Swing Bias</div>
                </div>
                <div class="bias-value {daily_bias.lower() if daily_bias else "neutral"}">
                    {daily_bias or "Neutral"} ({daily_strength})
                </div>
                <div class="confidence-bar">
                    <div class="confidence-fill {daily_bias.lower() if daily_bias else "neutral"}" 
                         style="width: {daily_conf * 33.33}%"></div>
                </div>
                <small>Confidence: {daily_conf}/3</small>
                {daily_signals_html}
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">
                <div class="card-title">🎯 Top Trade Recommendations - Weekly ({weekly_expiry})</div>
            </div>
            <div class="trades-grid">
                <div class="trades-column ce">
                    <div class="trades-title ce">🟢 Best CE Trades</div>
                    <ul>{trade_list_html(weekly_ce_top, 'CE')}</ul>
                </div>
                <div class="trades-column pe">
                    <div class="trades-title pe">🔴 Best PE Trades</div>
                    <ul>{trade_list_html(weekly_pe_top, 'PE')}</ul>
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">
                <div class="card-title">🎯 Top Trade Recommendations - Monthly ({monthly_expiry})</div>
            </div>
            <div class="trades-grid">
                <div class="trades-column ce">
                    <div class="trades-title ce">🟢 Best CE Trades</div>
                    <ul>{trade_list_html(monthly_ce_top, 'CE')}</ul>
                </div>
                <div class="trades-column pe">
                    <div class="trades-title pe">🔴 Best PE Trades</div>
                    <ul>{trade_list_html(monthly_pe_top, 'PE')}</ul>
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">
                <div class="card-title">📊 Technical Indicators</div>
            </div>
            <div class="indicators-grid">
                <div class="indicator-box">
                    <div class="indicator-name">VWAP</div>
                    <div class="indicator-value">{HTMLRenderer.format_number(intraday_ind.get('vwap'), 2) if intraday_ind.get('vwap') else 'N/A'}</div>
                </div>
                <div class="indicator-box">
                    <div class="indicator-name">EMA 9 / 21</div>
                    <div class="indicator-value">{HTMLRenderer.format_number(intraday_ind.get('ema9'), 2) if intraday_ind.get('ema9') else 'N/A'} / {HTMLRenderer.format_number(intraday_ind.get('ema21'), 2) if intraday_ind.get('ema21') else 'N/A'}</div>
                </div>
                <div class="indicator-box">
                    <div class="indicator-name">RSI (14)</div>
                    <div class="indicator-value">{HTMLRenderer.format_number(intraday_ind.get('rsi14'), 2) if intraday_ind.get('rsi14') else 'N/A'}</div>
                </div>
                <div class="indicator-box">
                    <div class="indicator-name">MACD</div>
                    <div class="indicator-value">{HTMLRenderer.format_number(intraday_ind.get('macd'), 2) if intraday_ind.get('macd') else 'N/A'}</div>
                </div>
                <div class="indicator-box">
                    <div class="indicator-name">Bollinger Bands</div>
                    <div class="indicator-value" style="font-size: 14px;">
                        U: {HTMLRenderer.format_number(intraday_ind.get('bb_upper'), 2) if intraday_ind.get('bb_upper') else 'N/A'}<br>
                        L: {HTMLRenderer.format_number(intraday_ind.get('bb_lower'), 2) if intraday_ind.get('bb_lower') else 'N/A'}
                    </div>
                </div>
                <div class="indicator-box">
                    <div class="indicator-name">ATR (14) / ADX</div>
                    <div class="indicator-value">{HTMLRenderer.format_number(intraday_ind.get('atr14'), 2) if intraday_ind.get('atr14') else 'N/A'} / {HTMLRenderer.format_number(intraday_ind.get('adx'), 2) if intraday_ind.get('adx') else 'N/A'}</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="toolbar">
                <div class="tabs" id="expiryTabs">
                    <button class="tab active" data-tab="weekly">Weekly ({weekly_expiry})</button>
                    <button class="tab" data-tab="monthly">Monthly ({monthly_expiry})</button>
                </div>
                <button class="btn" onclick="refreshData()">🔄 Refresh</button>
            </div>
            
            <div id="weekly" class="tab-content active">
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Strike</th>
                                <th>CE OI</th>
                                <th>CE Δ OI</th>
                                <th>CE LTP</th>
                                <th>CE Vol</th>
                                <th>CE IV%</th>
                                <th>Entry</th>
                                <th>Exit</th>
                                <th>SL</th>
                                <th>PE OI</th>
                                <th>PE Δ OI</th>
                                <th>PE LTP</th>
                                <th>PE Vol</th>
                                <th>PE IV%</th>
                                <th>Entry</th>
                                <th>Exit</th>
                                <th>SL</th>
                                <th>Signal</th>
                            </tr>
                        </thead>
                        <tbody>
                            {weekly_rows}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div id="monthly" class="tab-content">
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Strike</th>
                                <th>CE OI</th>
                                <th>CE Δ OI</th>
                                <th>CE LTP</th>
                                <th>CE Vol</th>
                                <th>CE IV%</th>
                                <th>Entry</th>
                                <th>Exit</th>
                                <th>SL</th>
                                <th>PE OI</th>
                                <th>PE Δ OI</th>
                                <th>PE LTP</th>
                                <th>PE Vol</th>
                                <th>PE IV%</th>
                                <th>Entry</th>
                                <th>Exit</th>
                                <th>SL</th>
                                <th>Signal</th>
                            </tr>
                        </thead>
                        <tbody>
                            {monthly_rows}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">
                <div class="card-title">📚 Trading Guide</div>
            </div>
            <div style="color: var(--muted); font-size: 14px; line-height: 1.8;">
                <h3 style="color: var(--text); margin-bottom: 12px;">Entry Rules</h3>
                <ul style="margin-left: 20px; margin-bottom: 20px;">
                    <li>✅ Enter when BUY CE/PE signal appears with bias confirmation</li>
                    <li>✅ Preferred entry windows: 09:30-11:00 AM or 13:30-15:00</li>
                    <li>✅ Verify OI buildup: CE OI rising = bullish | PE OI rising = bearish</li>
                    <li>✅ Use VWAP as dynamic support/resistance</li>
                    <li>✅ Check daily bias alignment for stronger conviction</li>
                </ul>
                
                <h3 style="color: var(--text); margin-bottom: 12px;">Exit Strategy</h3>
                <ul style="margin-left: 20px; margin-bottom: 20px;">
                    <li>🎯 Target: 5% profit (adjust based on volatility)</li>
                    <li>🛑 Stoploss: 3% loss (strict adherence required)</li>
                    <li>⏰ Time-based exit: Close all positions by 15:10-15:20</li>
                    <li>📊 Trail SL once 3% profit achieved</li>
                </ul>
                
                <h3 style="color: var(--text); margin-bottom: 12px;">Risk Management</h3>
                <ul style="margin-left: 20px;">
                    <li>💰 Risk only 1-2% of capital per trade</li>
                    <li>📉 Max 3 trades per day (avoid overtrading)</li>
                    <li>⚠️ High PCR (>1.3) = Market bottom | Low PCR (<0.7) = Market top</li>
                    <li>🎲 Never average losing positions</li>
                    <li>📱 Set price alerts for entry/exit levels</li>
                </ul>
            </div>
        </div>
    </div>
    
    <div class="toast-container" id="toastContainer"></div>
    <div class="scroll-top" id="scrollTop">↑</div>
    
    <script>
        // Tab switching
        document.querySelectorAll('.tab').forEach(tab => {{
            tab.addEventListener('click', () => {{
                const target = tab.dataset.tab;
                
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                
                tab.classList.add('active');
                document.getElementById(target).classList.add('active');
            }});
        }});
        
        // Scroll to top
        const scrollTop = document.getElementById('scrollTop');
        window.addEventListener('scroll', () => {{
            if (window.scrollY > 300) {{
                scrollTop.classList.add('visible');
            }} else {{
                scrollTop.classList.remove('visible');
            }}
        }});
        
        scrollTop.addEventListener('click', () => {{
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }});
        
        // Refresh data
        function refreshData() {{
            location.reload();
        }}
        
        // Auto refresh
        setTimeout(() => {{
            refreshData();
        }}, {REFRESH_INTERVAL * 1000});
        
        // Signal detection and alerts
        function showToast(type, strike, entry, exit, sl) {{
            const container = document.getElementById('toastContainer');
            const toast = document.createElement('div');
            toast.className = `toast ${{type.toLowerCase()}}`;
            
            const typeText = type === 'CE' ? '🟢 BUY CE' : '🔴 BUY PE';
            const typeClass = type === 'CE' ? 'ce' : 'pe';
            
            toast.innerHTML = `
                <div class="toast-header">
                    <div class="toast-title ${{typeClass}}">${{typeText}} Alert</div>
                    <span class="toast-close" onclick="this.parentElement.parentElement.remove()">×</span>
                </div>
                <div class="toast-body">
                    <strong>Strike:</strong> ${{strike}}<br>
                    <strong>Entry:</strong> ${{entry}} | <strong>Exit:</strong> ${{exit}} | <strong>SL:</strong> ${{sl}}
                </div>
            `;
            
            container.appendChild(toast);
            
            setTimeout(() => {{
                toast.style.animation = 'slideIn 0.3s ease reverse';
                setTimeout(() => toast.remove(), 300);
            }}, 7000);
        }}
        
        // Check for new signals on page load
        function scanForSignals() {{
            const alerted = JSON.parse(localStorage.getItem('alerted_strikes') || '{{}}');
            const today = new Date().toDateString();
            
            if (alerted.date !== today) {{
                localStorage.setItem('alerted_strikes', JSON.stringify({{ date: today, strikes: [] }}));
                alerted.strikes = [];
            }}
            
            document.querySelectorAll('tbody tr').forEach(row => {{
                const signal = row.dataset.signal;
                const strike = row.dataset.strike;
                
                if ((signal === 'BUY CE' || signal === 'BUY PE') && !alerted.strikes.includes(strike)) {{
                    const cells = row.querySelectorAll('td');
                    const entry = signal === 'BUY CE' ? cells[6].textContent : cells[14].textContent;
                    const exit = signal === 'BUY CE' ? cells[7].textContent : cells[15].textContent;
                    const sl = signal === 'BUY CE' ? cells[8].textContent : cells[16].textContent;
                    
                    showToast(signal.split(' ')[1], strike, entry, exit, sl);
                    alerted.strikes.push(strike);
                    localStorage.setItem('alerted_strikes', JSON.stringify(alerted));
                }}
            }});
        }}
        
        // Run scan after delay
        setTimeout(scanForSignals, 1000);
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'r' && e.ctrlKey) {{
                e.preventDefault();
                refreshData();
            }}
            if (e.key === 'Escape') {{
                document.querySelectorAll('.toast').forEach(t => t.remove());
            }}
        }});
    </script>
</body>
</html>
'''
        
        # Write to file
        output_file = Path(output_path).resolve()
        output_file.write_text(html, encoding='utf-8')
        
        if open_browser:
            webbrowser.open(output_file.as_uri())
        
        logger.info(f"✓ HTML dashboard created: {output_file}")

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application loop"""
    logger.info("=" * 60)
    logger.info("Advanced Nifty 50 Option Chain Analyzer v2.0")
    logger.info("=" * 60)
    logger.info(f"API Key: {KITE_API_KEY[:10]}...")
    logger.info(f"Refresh Interval: {REFRESH_INTERVAL}s")
    logger.info("=" * 60)
    
    fetcher = KiteDataFetcher(KITE_API_KEY, KITE_ACCESS_TOKEN)
    browser_opened = False
    
    try:
        while True:
            try:
                logger.info("Fetching option chain data...")
                data = fetcher.fetch_option_chain()
                
                if data:
                    HTMLRenderer.render_html(
                        data,
                        output_path="option_chain_v2.html",
                        open_browser=not browser_opened
                    )
                    
                    if not browser_opened:
                        logger.info("✓ Dashboard opened in browser")
                        browser_opened = True
                    else:
                        logger.info("✓ Dashboard updated")
                    
                    # Log key metrics
                    spot = data.get('nifty_spot')
                    intraday_bias = data.get('intraday_bias', {}).get('bias')
                    daily_bias = data.get('daily_bias', {}).get('bias')
                    pcr = data.get('pcr_weekly', 0)
                    
                    logger.info(f"NIFTY: {spot:.2f} | Intraday: {intraday_bias} | Daily: {daily_bias} | PCR: {pcr:.3f}")
                else:
                    logger.warning("No data received")
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
            
            logger.info(f"Next refresh in {REFRESH_INTERVAL}s...")
            time.sleep(REFRESH_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("\n" + "=" * 60)
        logger.info("Application stopped by user")
        logger.info("=" * 60)
        sys.exit(0)

if __name__ == "__main__":
    main()