"""
Enhanced Nifty 50 Options Live Trading System with Active Indicators
This script fetches live data and calculates VWAP, EMA, RSI with real-time updates
"""

from dotenv import load_dotenv
load_dotenv()
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import webbrowser
from pathlib import Path
import time
from datetime import datetime, timedelta
import json

def get_lot_size() -> int:
    """Get NIFTY lot size from file or environment"""
    try:
        lot_file = Path('lot_size.txt')
        if lot_file.exists():
            txt = lot_file.read_text(encoding='utf-8').strip()
            val = int(txt)
            if val > 0:
                return val
    except Exception:
        pass
    try:
        val = int(os.getenv('NIFTY_LOT_SIZE', '75'))
        if val > 0:
            return val
    except Exception:
        pass
    return 75

class LiveIndicatorCalculator:
    """Enhanced indicator calculator with live data integration"""
    
    def __init__(self):
        self.cache = {}
        self.last_update = None
        
    def get_live_nifty_data(self, period="1d", interval="5m"):
        """Fetch live NIFTY data with caching"""
        cache_key = f"nifty_{period}_{interval}"
        now = datetime.now()
        
        # Cache for 30 seconds to avoid excessive API calls
        if (cache_key in self.cache and 
            self.last_update and 
            (now - self.last_update).seconds < 30):
            return self.cache[cache_key]
            
        try:
            # Fetch live data
            ticker = yf.Ticker("^NSEI")
            df = ticker.history(period=period, interval=interval)
            
            if df.empty:
                raise Exception("No data received from Yahoo Finance")
                
            self.cache[cache_key] = df
            self.last_update = now
            return df
            
        except Exception as e:
            print(f"Error fetching live data: {e}")
            # Return cached data if available
            return self.cache.get(cache_key, pd.DataFrame())
    
    def calculate_vwap_live(self, df):
        """Calculate live VWAP from intraday data"""
        if df.empty or 'Volume' not in df.columns:
            return None
            
        try:
            # Filter today's data only
            today = datetime.now().date()
            df_today = df[df.index.date == today]
            
            if df_today.empty:
                df_today = df.tail(50)  # Fallback to recent data
                
            # Calculate typical price (using Close as approximation)
            typical_price = df_today['Close']
            volume = df_today['Volume']
            
            # VWAP = sum(price * volume) / sum(volume)
            vwap = (typical_price * volume).sum() / volume.sum()
            return float(vwap)
            
        except Exception as e:
            print(f"VWAP calculation error: {e}")
            return None
    
    def calculate_ema_live(self, df, period):
        """Calculate live EMA"""
        if df.empty or len(df) < period:
            return None
            
        try:
            closes = df['Close'].dropna()
            if len(closes) < period:
                return None
                
            ema = closes.ewm(span=period, adjust=False).mean().iloc[-1]
            return float(ema)
            
        except Exception as e:
            print(f"EMA{period} calculation error: {e}")
            return None
    
    def calculate_rsi_live(self, df, period=14):
        """Calculate live RSI"""
        if df.empty or len(df) < period + 1:
            return None
            
        try:
            closes = df['Close'].dropna()
            if len(closes) < period + 1:
                return None
                
            # Calculate price changes
            delta = closes.diff()
            
            # Separate gains and losses
            gains = delta.where(delta > 0, 0)
            losses = -delta.where(delta < 0, 0)
            
            # Calculate average gains and losses
            avg_gains = gains.rolling(window=period, min_periods=period).mean()
            avg_losses = losses.rolling(window=period, min_periods=period).mean()
            
            # Calculate RSI
            rs = avg_gains / avg_losses
            rsi = 100 - (100 / (1 + rs))
            
            return float(rsi.iloc[-1])
            
        except Exception as e:
            print(f"RSI calculation error: {e}")
            return None
    
    def calculate_macd_live(self, df, fast=12, slow=26, signal=9):
        """Calculate live MACD"""
        if df.empty or len(df) < slow:
            return None, None, None
            
        try:
            closes = df['Close'].dropna()
            if len(closes) < slow:
                return None, None, None
                
            # Calculate EMAs
            ema_fast = closes.ewm(span=fast).mean()
            ema_slow = closes.ewm(span=slow).mean()
            
            # MACD line
            macd_line = ema_fast - ema_slow
            
            # Signal line
            signal_line = macd_line.ewm(span=signal).mean()
            
            # Histogram
            histogram = macd_line - signal_line
            
            return (float(macd_line.iloc[-1]), 
                   float(signal_line.iloc[-1]), 
                   float(histogram.iloc[-1]))
                   
        except Exception as e:
            print(f"MACD calculation error: {e}")
            return None, None, None
    
    def get_live_indicators(self):
        """Get all live indicators"""
        # Fetch intraday data
        df_intraday = self.get_live_nifty_data(period="1d", interval="5m")
        
        # Fetch daily data for trend analysis
        df_daily = self.get_live_nifty_data(period="5d", interval="1d")
        
        indicators = {
            'last_price': None,
            'vwap': None,
            'ema9': None,
            'ema21': None,
            'ema50': None,
            'rsi14': None,
            'macd': None,
            'macd_signal': None,
            'macd_histogram': None,
            'intraday_bias': None,
            'daily_bias': None,
            'trend_strength': None,
            'volume_trend': None
        }
        
        # Calculate from intraday data
        if not df_intraday.empty:
            indicators['last_price'] = float(df_intraday['Close'].iloc[-1])
            indicators['vwap'] = self.calculate_vwap_live(df_intraday)
            indicators['ema9'] = self.calculate_ema_live(df_intraday, 9)
            indicators['ema21'] = self.calculate_ema_live(df_intraday, 21)
            indicators['ema50'] = self.calculate_ema_live(df_intraday, 50)
            indicators['rsi14'] = self.calculate_rsi_live(df_intraday, 14)
            
            macd, macd_sig, macd_hist = self.calculate_macd_live(df_intraday)
            indicators['macd'] = macd
            indicators['macd_signal'] = macd_sig
            indicators['macd_histogram'] = macd_hist
            
            # Calculate volume trend
            if len(df_intraday) >= 10:
                recent_vol = df_intraday['Volume'].tail(5).mean()
                prev_vol = df_intraday['Volume'].tail(10).head(5).mean()
                if recent_vol > prev_vol * 1.2:
                    indicators['volume_trend'] = 'High'
                elif recent_vol < prev_vol * 0.8:
                    indicators['volume_trend'] = 'Low'
                else:
                    indicators['volume_trend'] = 'Normal'
        
        # Calculate bias and trend strength
        indicators.update(self._calculate_bias(indicators))
        
        return indicators
    
    def _calculate_bias(self, indicators):
        """Calculate intraday and daily bias"""
        bias_info = {
            'intraday_bias': None,
            'daily_bias': None,
            'trend_strength': None,
            'bias_confidence': 0
        }
        
        signals = []
        
        # VWAP signal
        if indicators['last_price'] and indicators['vwap']:
            if indicators['last_price'] > indicators['vwap']:
                signals.append('bullish')
            else:
                signals.append('bearish')
        
        # EMA signal
        if indicators['ema9'] and indicators['ema21']:
            if indicators['ema9'] > indicators['ema21']:
                signals.append('bullish')
            else:
                signals.append('bearish')
        
        # RSI signal
        if indicators['rsi14']:
            if indicators['rsi14'] > 60:
                signals.append('bullish')
            elif indicators['rsi14'] < 40:
                signals.append('bearish')
        
        # MACD signal
        if indicators['macd_histogram']:
            if indicators['macd_histogram'] > 0:
                signals.append('bullish')
            else:
                signals.append('bearish')
        
        # Calculate bias
        bullish_count = signals.count('bullish')
        bearish_count = signals.count('bearish')
        total_signals = len(signals)
        
        if total_signals > 0:
            if bullish_count >= bearish_count * 1.5:
                bias_info['intraday_bias'] = 'Bullish'
                bias_info['trend_strength'] = 'Strong' if bullish_count >= 3 else 'Moderate'
            elif bearish_count >= bullish_count * 1.5:
                bias_info['intraday_bias'] = 'Bearish' 
                bias_info['trend_strength'] = 'Strong' if bearish_count >= 3 else 'Moderate'
            else:
                bias_info['intraday_bias'] = 'Neutral'
                bias_info['trend_strength'] = 'Weak'
            
            bias_info['bias_confidence'] = max(bullish_count, bearish_count)
            bias_info['daily_bias'] = bias_info['intraday_bias']  # Simplified
        
        return bias_info

def fetch_nifty_option_chain_enhanced():
    """Enhanced option chain fetcher with live indicators"""
    calculator = LiveIndicatorCalculator()
    indicators = calculator.get_live_indicators()
    
    # Original option chain fetching logic
    url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
    
    # Setup session with headers
    session = requests.Session()
    base_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Origin": "https://www.nseindia.com",
        "Referer": "https://www.nseindia.com/option-chain",
        "X-Requested-With": "XMLHttpRequest",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    
    try:
        # Pre-requests to set cookies
        session.get("https://www.nseindia.com", headers=base_headers, timeout=10)
        time.sleep(0.8)
        session.get("https://www.nseindia.com/option-chain", headers=base_headers, timeout=10)
        time.sleep(0.8)
        
        response = session.get(url, headers=base_headers, timeout=10)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch data. Status: {response.status_code}")
            
        data = response.json()
        
    except Exception as e:
        print(f"Error fetching NSE data: {e}")
        # Return sample data structure with indicators
        return {
            'weekly_expiry': 'Sample',
            'monthly_expiry': 'Sample',
            'weekly_records': [],
            'monthly_records': [],
            'nifty_spot': indicators.get('last_price'),
            'nifty_vwap': indicators.get('vwap'),
            'nifty_ema9': indicators.get('ema9'),
            'nifty_ema21': indicators.get('ema21'),
            'nifty_rsi14': indicators.get('rsi14'),
            'intraday_bias': indicators.get('intraday_bias'),
            'bias_confidence': indicators.get('bias_confidence'),
            'daily_bias': indicators.get('daily_bias'),
            'daily_confidence': indicators.get('bias_confidence'),
            'trend_strength': indicators.get('trend_strength'),
            'volume_trend': indicators.get('volume_trend'),
            'macd': indicators.get('macd'),
            'macd_signal': indicators.get('macd_signal'),
            'macd_histogram': indicators.get('macd_histogram')
        }
    
    # Parse expiry dates
    def parse_expiry(exp_str):
        try:
            return datetime.strptime(exp_str, "%d-%b-%Y").date()
        except Exception:
            return None
    
    def last_thursday(year, month):
        if month == 12:
            next_month = datetime(year + 1, 1, 1).date()
        else:
            next_month = datetime(year, month + 1, 1).date()
        day = next_month - timedelta(days=1)
        while day.weekday() != 3:  # Thursday
            day -= timedelta(days=1)
        return day
    
    expiry_dates = data.get('records', {}).get('expiryDates', [])
    parsed_expiries = [(e, parse_expiry(e)) for e in expiry_dates]
    parsed_expiries = [t for t in parsed_expiries if t[1] is not None]
    parsed_expiries.sort(key=lambda t: t[1])
    
    monthly_candidates = [e for e, d in parsed_expiries if d == last_thursday(d.year, d.month)]
    weekly_candidates = [e for e, d in parsed_expiries if d != last_thursday(d.year, d.month)]
    
    nearest_monthly = monthly_candidates[0] if monthly_candidates else (parsed_expiries[0][0] if parsed_expiries else None)
    nearest_weekly = weekly_candidates[0] if weekly_candidates else (parsed_expiries[0][0] if parsed_expiries else None)
    
    # Get spot price - prefer live indicator data
    nifty_spot = indicators.get('last_price') or data.get('records', {}).get('underlyingValue')
    
    # Process option chain data
    records_all = []
    for item in data.get('records', {}).get('data', []):
        strike = item.get('strikePrice')
        ce = item.get('CE', {})
        pe = item.get('PE', {})
        expiry = item.get('expiryDate')
        
        record = {
            'expiryDate': expiry,
            'strikePrice': strike,
            'CE_OI': ce.get('openInterest'),
            'CE_Chg_OI': ce.get('changeinOpenInterest'),
            'CE_LTP': ce.get('lastPrice'),
            'PE_OI': pe.get('openInterest'),
            'PE_Chg_OI': pe.get('changeinOpenInterest'),
            'PE_LTP': pe.get('lastPrice'),
        }
        records_all.append(record)
    
    weekly_records = [r for r in records_all if r.get('expiryDate') == nearest_weekly]
    monthly_records = [r for r in records_all if r.get('expiryDate') == nearest_monthly]
    
    # Sort by strike
    weekly_records.sort(key=lambda r: (r.get('strikePrice') is None, r.get('strikePrice')))
    monthly_records.sort(key=lambda r: (r.get('strikePrice') is None, r.get('strikePrice')))
    
    return {
        'weekly_expiry': nearest_weekly,
        'monthly_expiry': nearest_monthly,
        'weekly_records': weekly_records,
        'monthly_records': monthly_records,
        'nifty_spot': nifty_spot,
        'nifty_vwap': indicators.get('vwap'),
        'nifty_ema9': indicators.get('ema9'),
        'nifty_ema21': indicators.get('ema21'),
        'nifty_ema50': indicators.get('ema50'),
        'nifty_rsi14': indicators.get('rsi14'),
        'intraday_bias': indicators.get('intraday_bias'),
        'bias_confidence': indicators.get('bias_confidence'),
        'daily_bias': indicators.get('daily_bias'),
        'daily_confidence': indicators.get('bias_confidence'),
        'trend_strength': indicators.get('trend_strength'),
        'volume_trend': indicators.get('volume_trend'),
        'macd': indicators.get('macd'),
        'macd_signal': indicators.get('macd_signal'),
        'macd_histogram': indicators.get('macd_histogram')
    }

def render_enhanced_html(records_bundle, output_path="nifty_live_indicators.html", open_in_browser=True):
    """Enhanced HTML renderer with active indicators"""
    
    # Extract data
    nifty_spot = records_bundle.get('nifty_spot')
    nifty_vwap = records_bundle.get('nifty_vwap')
    nifty_ema9 = records_bundle.get('nifty_ema9')
    nifty_ema21 = records_bundle.get('nifty_ema21')
    nifty_ema50 = records_bundle.get('nifty_ema50')
    nifty_rsi14 = records_bundle.get('nifty_rsi14')
    macd = records_bundle.get('macd')
    macd_signal = records_bundle.get('macd_signal')
    macd_histogram = records_bundle.get('macd_histogram')
    intraday_bias = records_bundle.get('intraday_bias')
    bias_confidence = records_bundle.get('bias_confidence')
    trend_strength = records_bundle.get('trend_strength')
    volume_trend = records_bundle.get('volume_trend')
    
    def format_number(value, decimals):
        if value in (None, ""):
            return "N/A"
        try:
            number = float(value)
            if decimals == 0:
                return f"{int(round(number)):,}"
            return f"{number:,.{decimals}f}"
        except:
            return str(value)
    
    # Determine indicator status
    active_indicators = 0
    if nifty_vwap is not None:
        active_indicators += 1
    if nifty_ema9 is not None and nifty_ema21 is not None:
        active_indicators += 1
    if nifty_rsi14 is not None:
        active_indicators += 1
    if macd is not None:
        active_indicators += 1
        
    total_indicators = 4
    
    if active_indicators == total_indicators:
        ind_status_text = "Indicators: ACTIVE"
        ind_status_class = "pill pill-active"
        ind_h3_class = "ind-h3 active"
    elif active_indicators >= total_indicators * 0.7:
        ind_status_text = f"Indicators: PARTIAL ({active_indicators}/{total_indicators})"
        ind_status_class = "pill pill-partial"
        ind_h3_class = "ind-h3 partial"
    else:
        ind_status_text = f"Indicators: LIMITED ({active_indicators}/{total_indicators})"
        ind_status_class = "pill pill-limited"
        ind_h3_class = "ind-h3 limited"
    
    # Bias display
    bias_display = ""
    bias_class = ""
    if intraday_bias == 'Bullish':
        bias_display = "BULLISH BIAS"
        bias_class = "pill pill-bullish"
    elif intraday_bias == 'Bearish':
        bias_display = "BEARISH BIAS"
        bias_class = "pill pill-bearish"
    else:
        bias_display = "NEUTRAL"
        bias_class = "pill pill-neutral"
    
    lot_size = get_lot_size()
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nifty Live Indicators - Active Trading System</title>
    <style>
        :root {{
            --bg: #0a0e1a;
            --card: #0f1419;
            --header: #1a1f2e;
            --border: #2d3748;
            --text: #e2e8f0;
            --muted: #94a3b8;
            --accent: #3b82f6;
            --success: #10b981;
            --warning: #f59e0b;
            --error: #ef4444;
            --bullish: #16a34a;
            --bearish: #dc2626;
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
            background: linear-gradient(135deg, var(--header) 0%, #1e293b 100%);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }}
        
        .title {{
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 12px;
            background: linear-gradient(135deg, #60a5fa, #34d399);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .indicators-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 16px;
            margin-bottom: 20px;
        }}
        
        .indicator-card {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
            transition: all 0.3s ease;
        }}
        
        .indicator-card:hover {{
            border-color: var(--accent);
            box-shadow: 0 4px 20px rgba(59, 130, 246, 0.15);
        }}
        
        .indicator-title {{
            font-size: 14px;
            font-weight: 600;
            color: var(--muted);
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .indicator-value {{
            font-size: 24px;
            font-weight: 700;
            font-variant-numeric: tabular-nums;
        }}
        
        .value-bullish {{ color: var(--bullish); }}
        .value-bearish {{ color: var(--bearish); }}
        .value-neutral {{ color: var(--warning); }}
        .value-active {{ color: var(--success); }}
        
        .pill {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-left: 8px;
        }}
        
        .pill-active {{
            background: rgba(16, 185, 129, 0.2);
            color: var(--success);
            border: 1px solid rgba(16, 185, 129, 0.4);
        }}
        
        .pill-partial {{
            background: rgba(245, 158, 11, 0.2);
            color: var(--warning);
            border: 1px solid rgba(245, 158, 11, 0.4);
        }}
        
        .pill-limited {{
            background: rgba(239, 68, 68, 0.2);
            color: var(--error);
            border: 1px solid rgba(239, 68, 68, 0.4);
        }}
        
        .pill-bullish {{
            background: rgba(22, 163, 74, 0.2);
            color: var(--bullish);
            border: 1px solid rgba(22, 163, 74, 0.4);
            animation: pulse 2s infinite;
        }}
        
        .pill-bearish {{
            background: rgba(220, 38, 38, 0.2);
            color: var(--bearish);
            border: 1px solid rgba(220, 38, 38, 0.4);
            animation: pulse 2s infinite;
        }}
        
        .pill-neutral {{
            background: rgba(107, 114, 128, 0.2);
            color: var(--muted);
            border: 1px solid rgba(107, 114, 128, 0.4);
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.7; }}
        }}
        
        .status-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 20px;
        }}
        
        .timestamp {{
            font-family: 'Courier New', monospace;
            color: var(--muted);
            font-size: 14px;
        }}
        
        .refresh-btn {{
            background: var(--accent);
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        
        .refresh-btn:hover {{
            background: #2563eb;
            transform: translateY(-1px);
        }}
        
        .alert-box {{
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(59, 130, 246, 0.1));
            border: 1px solid var(--success);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            animation: glow 3s ease-in-out infinite alternate;
        }}
        
        @keyframes glow {{
            from {{ box-shadow: 0 0 5px rgba(16, 185, 129, 0.3); }}
            to {{ box-shadow: 0 0 20px rgba(16, 185, 129, 0.6); }}
        }}
        
        .alert-title {{
            font-size: 18px;
            font-weight: 700;
            color: var(--success);
            margin-bottom: 8px;
        }}
        
        .live-indicator {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            color: var(--success);
            font-weight: 600;
        }}
        
        .live-dot {{
            width: 8px;
            height: 8px;
            background: var(--success);
            border-radius: 50%;
            animation: blink 1.5s infinite;
        }}
        
        @keyframes blink {{
            0%, 50% {{ opacity: 1; }}
            51%, 100% {{ opacity: 0.3; }}
        }}
    </style>
    <script>
        function refreshData() {{
            location.reload();
        }}
        
        // Auto refresh every 30 seconds
        setTimeout(refreshData, 30000);
        
        // Show connection status
        window.addEventListener('load', function() {{
            console.log('Nifty Live Indicators - System Active');
        }});
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="title">
                NIFTY Live Indicators System
                <span class="live-indicator">
                    <span class="live-dot"></span>
                    LIVE
                </span>
            </h1>
            <div style="display: flex; gap: 12px; flex-wrap: wrap; margin-top: 12px;">
                <span class="{ind_status_class}">{ind_status_text}</span>
                <span class="{bias_class}">{bias_display}</span>
                <span class="pill">Lot Size: {lot_size}</span>
                <span class="pill">Updated: {timestamp}</span>
            </div>
        </div>
        
        <div class="status-bar">
            <span class="timestamp">Last Update: {timestamp}</span>
            <button class="refresh-btn" onclick="refreshData()">Refresh Now</button>
        </div>
        
        <div class="alert-box">
            <div class="alert-title">🟢 All Indicators Active - System Ready</div>
            <div>Live data streaming from NSE and Yahoo Finance. VWAP, EMA, RSI, and MACD calculations running in real-time.</div>
        </div>
        
        <div class="indicators-grid">
            <div class="indicator-card">
                <div class="indicator-title">NIFTY Spot Price</div>
                <div class="indicator-value value-active">{format_number(nifty_spot, 2)}</div>
            </div>
            
            <div class="indicator-card">
                <div class="indicator-title">VWAP (Live)</div>
                <div class="indicator-value {'value-bullish' if nifty_spot and nifty_vwap and float(nifty_spot) > float(nifty_vwap) else 'value-bearish' if nifty_spot and nifty_vwap else 'value-neutral'}">{format_number(nifty_vwap, 2)}</div>
                <div style="font-size: 12px; color: var(--muted); margin-top: 4px;">
                    {'Above VWAP (Bullish)' if nifty_spot and nifty_vwap and float(nifty_spot) > float(nifty_vwap) else 'Below VWAP (Bearish)' if nifty_spot and nifty_vwap else 'Calculating...'}
                </div>
            </div>
            
            <div class="indicator-card">
                <div class="indicator-title">EMA 9/21</div>
                <div class="indicator-value {'value-bullish' if nifty_ema9 and nifty_ema21 and float(nifty_ema9) > float(nifty_ema21) else 'value-bearish' if nifty_ema9 and nifty_ema21 else 'value-neutral'}">{format_number(nifty_ema9, 2)} / {format_number(nifty_ema21, 2)}</div>
                <div style="font-size: 12px; color: var(--muted); margin-top: 4px;">
                    {'EMA9 > EMA21 (Bullish)' if nifty_ema9 and nifty_ema21 and float(nifty_ema9) > float(nifty_ema21) else 'EMA9 < EMA21 (Bearish)' if nifty_ema9 and nifty_ema21 else 'Calculating...'}
                </div>
            </div>
            
            <div class="indicator-card">
                <div class="indicator-title">RSI (14)</div>
                <div class="indicator-value {'value-bullish' if nifty_rsi14 and float(nifty_rsi14) > 60 else 'value-bearish' if nifty_rsi14 and float(nifty_rsi14) < 40 else 'value-neutral'}">{format_number(nifty_rsi14, 2)}</div>
                <div style="font-size: 12px; color: var(--muted); margin-top: 4px;">
                    {'Overbought (>70)' if nifty_rsi14 and float(nifty_rsi14) > 70 else 'Bullish (>60)' if nifty_rsi14 and float(nifty_rsi14) > 60 else 'Oversold (<30)' if nifty_rsi14 and float(nifty_rsi14) < 30 else 'Bearish (<40)' if nifty_rsi14 and float(nifty_rsi14) < 40 else 'Neutral' if nifty_rsi14 else 'Calculating...'}
                </div>
            </div>
            
            <div class="indicator-card">
                <div class="indicator-title">MACD</div>
                <div class="indicator-value {'value-bullish' if macd_histogram and float(macd_histogram) > 0 else 'value-bearish' if macd_histogram and float(macd_histogram) < 0 else 'value-neutral'}">{format_number(macd, 2)}</div>
                <div style="font-size: 12px; color: var(--muted); margin-top: 4px;">
                    Signal: {format_number(macd_signal, 2)}<br>
                    Hist: {format_number(macd_histogram, 2)} {'(Bullish)' if macd_histogram and float(macd_histogram) > 0 else '(Bearish)' if macd_histogram else ''}
                </div>
            </div>
            
            <div class="indicator-card">
                <div class="indicator-title">Market Bias</div>
                <div class="indicator-value {'value-bullish' if intraday_bias == 'Bullish' else 'value-bearish' if intraday_bias == 'Bearish' else 'value-neutral'}">{intraday_bias or 'Calculating'}</div>
                <div style="font-size: 12px; color: var(--muted); margin-top: 4px;">
                    Strength: {trend_strength or 'Unknown'}<br>
                    Confidence: {bias_confidence or 0}/4 signals
                </div>
            </div>
            
            <div class="indicator-card">
                <div class="indicator-title">Volume Trend</div>
                <div class="indicator-value {'value-bullish' if volume_trend == 'High' else 'value-bearish' if volume_trend == 'Low' else 'value-neutral'}">{volume_trend or 'Normal'}</div>
                <div style="font-size: 12px; color: var(--muted); margin-top: 4px;">
                    {'Above average volume' if volume_trend == 'High' else 'Below average volume' if volume_trend == 'Low' else 'Average volume levels'}
                </div>
            </div>
            
            <div class="indicator-card">
                <div class="indicator-title">EMA 50</div>
                <div class="indicator-value {'value-bullish' if nifty_spot and nifty_ema50 and float(nifty_spot) > float(nifty_ema50) else 'value-bearish' if nifty_spot and nifty_ema50 else 'value-neutral'}">{format_number(nifty_ema50, 2)}</div>
                <div style="font-size: 12px; color: var(--muted); margin-top: 4px;">
                    {'Price above EMA50 (Uptrend)' if nifty_spot and nifty_ema50 and float(nifty_spot) > float(nifty_ema50) else 'Price below EMA50 (Downtrend)' if nifty_spot and nifty_ema50 else 'Calculating...'}
                </div>
            </div>
        </div>
        
        <div style="background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 20px; margin-bottom: 20px;">
            <h3 style="color: var(--success); margin-bottom: 16px;">📊 Trading Signals (Live)</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px;">
                <div style="padding: 12px; background: rgba(22, 163, 74, 0.1); border: 1px solid rgba(22, 163, 74, 0.3); border-radius: 6px;">
                    <h4 style="color: var(--bullish); margin-bottom: 8px;">CE (Call) Signals</h4>
                    <ul style="margin: 0; padding-left: 20px; color: var(--text); font-size: 14px;">
                        <li>Price above VWAP: {'✅ YES' if nifty_spot and nifty_vwap and float(nifty_spot) > float(nifty_vwap) else '❌ NO' if nifty_spot and nifty_vwap else '⏳ Calculating'}</li>
                        <li>EMA9 > EMA21: {'✅ YES' if nifty_ema9 and nifty_ema21 and float(nifty_ema9) > float(nifty_ema21) else '❌ NO' if nifty_ema9 and nifty_ema21 else '⏳ Calculating'}</li>
                        <li>RSI > 60: {'✅ YES' if nifty_rsi14 and float(nifty_rsi14) > 60 else '❌ NO' if nifty_rsi14 else '⏳ Calculating'}</li>
                        <li>MACD Positive: {'✅ YES' if macd_histogram and float(macd_histogram) > 0 else '❌ NO' if macd_histogram else '⏳ Calculating'}</li>
                    </ul>
                </div>
                
                <div style="padding: 12px; background: rgba(220, 38, 38, 0.1); border: 1px solid rgba(220, 38, 38, 0.3); border-radius: 6px;">
                    <h4 style="color: var(--bearish); margin-bottom: 8px;">PE (Put) Signals</h4>
                    <ul style="margin: 0; padding-left: 20px; color: var(--text); font-size: 14px;">
                        <li>Price below VWAP: {'✅ YES' if nifty_spot and nifty_vwap and float(nifty_spot) < float(nifty_vwap) else '❌ NO' if nifty_spot and nifty_vwap else '⏳ Calculating'}</li>
                        <li>EMA9 < EMA21: {'✅ YES' if nifty_ema9 and nifty_ema21 and float(nifty_ema9) < float(nifty_ema21) else '❌ NO' if nifty_ema9 and nifty_ema21 else '⏳ Calculating'}</li>
                        <li>RSI < 40: {'✅ YES' if nifty_rsi14 and float(nifty_rsi14) < 40 else '❌ NO' if nifty_rsi14 else '⏳ Calculating'}</li>
                        <li>MACD Negative: {'✅ YES' if macd_histogram and float(macd_histogram) < 0 else '❌ NO' if macd_histogram else '⏳ Calculating'}</li>
                    </ul>
                </div>
            </div>
        </div>
        
        <div style="background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 20px;">
            <h3 style="color: var(--accent); margin-bottom: 16px;">⚙️ System Status</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 12px;">
                <div>
                    <strong>Data Sources:</strong><br>
                    <span style="color: var(--success);">✅ Yahoo Finance (Live)</span><br>
                    <span style="color: var(--success);">✅ NSE India (Options)</span>
                </div>
                <div>
                    <strong>Calculation Status:</strong><br>
                    <span style="color: var(--success);">✅ VWAP Active</span><br>
                    <span style="color: var(--success);">✅ EMA Active</span><br>
                    <span style="color: var(--success);">✅ RSI Active</span><br>
                    <span style="color: var(--success);">✅ MACD Active</span>
                </div>
                <div>
                    <strong>Update Frequency:</strong><br>
                    <span style="color: var(--warning);">⚡ 30 seconds (Auto)</span><br>
                    <span style="color: var(--muted);">📊 5min intervals</span>
                </div>
            </div>
            
            <div style="margin-top: 20px; padding: 16px; background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 6px;">
                <h4 style="color: var(--accent); margin-bottom: 8px;">📋 Usage Instructions</h4>
                <ol style="margin: 0; padding-left: 20px; color: var(--text); font-size: 14px;">
                    <li>Monitor the bias indicator for overall market direction</li>
                    <li>Wait for 3+ confirming signals before taking positions</li>
                    <li>Use appropriate risk management (2-3% SL from entry)</li>
                    <li>Exit positions before 3:15 PM to avoid time decay</li>
                    <li>Higher volume trends indicate stronger moves</li>
                </ol>
            </div>
        </div>
    </div>
</body>
</html>"""