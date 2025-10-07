"""
Nifty 50 Option Chain with Kite API for indicators
"""

from dotenv import load_dotenv
load_dotenv()
import pandas as pd
import requests
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import webbrowser
from pathlib import Path
import time
from kiteconnect import KiteConnect

def get_lot_size() -> int:
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

# Kite setup
KITE_API_KEY = os.getenv('KITE_API_KEY')
KITE_ACCESS_TOKEN = os.getenv('KITE_ACCESS_TOKEN')

def get_kite_client():
    """Initialize Kite client"""
    if not KITE_API_KEY or not KITE_ACCESS_TOKEN:
        raise ValueError("KITE_API_KEY and KITE_ACCESS_TOKEN must be set in .env file")
    kite = KiteConnect(api_key=KITE_API_KEY)
    kite.set_access_token(KITE_ACCESS_TOKEN)
    return kite

def _compute_ema(values, period):
    """Compute EMA using pandas"""
    return pd.Series(values).ewm(span=period, adjust=False).mean().iloc[-1]

def _compute_rsi(values, period=14):
    """Compute RSI using pandas"""
    series = pd.Series(values)
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.rolling(window=period, min_periods=period).mean()
    ma_down = down.rolling(window=period, min_periods=period).mean()
    rs = ma_up / ma_down
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def get_nifty50_indicators():
    """Fetch NIFTY indicators using Kite API"""
    try:
        print("Fetching NIFTY data from Kite...")
        kite = get_kite_client()
        
        # Fetch intraday historical data (1-minute candles for today)
        from datetime import datetime, timedelta
        to_date = datetime.now()
        from_date = to_date.replace(hour=9, minute=15, second=0, microsecond=0)
        
        # NIFTY 50 instrument token (you may need to verify this)
        nifty_token = 256265  # NSE:NIFTY 50
        
        candles = kite.historical_data(
            instrument_token=nifty_token,
            from_date=from_date,
            to_date=to_date,
            interval="minute"
        )
        
        if not candles:
            print("WARNING: No data received from Kite")
            return {
                "last": None, "ema9": None, "ema21": None,
                "rsi14": None, "vwap": None, "bias": None, "confidence": None
            }
        
        closes = [c['close'] for c in candles]
        volumes = [c['volume'] for c in candles]
        
        if not closes:
            print("WARNING: No close prices in Kite data")
            return {
                "last": None, "ema9": None, "ema21": None,
                "rsi14": None, "vwap": None, "bias": None, "confidence": None
            }
        
        ema9 = _compute_ema(closes, 9) if len(closes) >= 9 else None
        ema21 = _compute_ema(closes, 21) if len(closes) >= 21 else None
        rsi14 = _compute_rsi(closes, 14) if len(closes) >= 14 else None
        
        # Compute VWAP
        vwap = None
        total_volume = sum(volumes)
        if total_volume > 0:
            vwap = sum(c * v for c, v in zip(closes, volumes)) / total_volume
        
        last_price = closes[-1] if closes else None
        
        # Compute bias
        votes = 0
        total = 0
        if vwap is not None and last_price is not None:
            total += 1
            votes += 1 if last_price > vwap else -1
        if ema9 is not None and ema21 is not None:
            total += 1
            votes += 1 if ema9 > ema21 else -1
        if rsi14 is not None:
            total += 1
            if rsi14 >= 60:
                votes += 1
            elif rsi14 <= 40:
                votes -= 1
        
        bias = None
        if total > 0:
            if votes >= 2:
                bias = "Bullish"
            elif votes <= -2:
                bias = "Bearish"
            else:
                bias = "Neutral"
        
        result = {
            "last": last_price,
            "ema9": ema9,
            "ema21": ema21,
            "rsi14": rsi14,
            "vwap": vwap,
            "bias": bias,
            "confidence": abs(votes) if total > 0 else None
        }
        
        vwap_str = f"{vwap:.2f}" if vwap is not None else "N/A"
        ema9_str = f"{ema9:.2f}" if ema9 is not None else "N/A"
        ema21_str = f"{ema21:.2f}" if ema21 is not None else "N/A"
        rsi14_str = f"{rsi14:.2f}" if rsi14 is not None else "N/A"
        
        print(f"✓ Indicators: VWAP={vwap_str}, EMA9={ema9_str}, EMA21={ema21_str}, RSI={rsi14_str}")
        print(f"✓ Bias: {bias} (confidence: {abs(votes) if total > 0 else 0}/{total})")
        
        return result
        
    except Exception as e:
        print(f"ERROR fetching Kite data: {e}")
        import traceback
        traceback.print_exc()
        return {
            "last": None, "ema9": None, "ema21": None,
            "rsi14": None, "vwap": None, "bias": None, "confidence": None
        }

def get_daily_bias():
    """Compute daily bias using Kite API"""
    try:
        print("Fetching daily NIFTY data...")
        kite = get_kite_client()
        
        from datetime import datetime, timedelta
        to_date = datetime.now()
        from_date = to_date - timedelta(days=365)
        
        nifty_token = 256265  # NSE:NIFTY 50
        
        candles = kite.historical_data(
            instrument_token=nifty_token,
            from_date=from_date,
            to_date=to_date,
            interval="day"
        )
        
        if not candles:
            return {
                'ema20': None, 'ema50': None, 'ema200': None,
                'rsi14': None, 'last': None, 'bias': None, 'confidence': None
            }
        
        closes = [c['close'] for c in candles]
        
        if not closes:
            return {
                'ema20': None, 'ema50': None, 'ema200': None,
                'rsi14': None, 'last': None, 'bias': None, 'confidence': None
            }
        
        ema20 = _compute_ema(closes, 20) if len(closes) >= 20 else None
        ema50 = _compute_ema(closes, 50) if len(closes) >= 50 else None
        ema200 = _compute_ema(closes, 200) if len(closes) >= 200 else None
        rsi14 = _compute_rsi(closes, 14) if len(closes) >= 14 else None
        last_close = closes[-1]
        
        # Voting
        votes = 0
        total = 0
        if ema200 is not None:
            total += 1
            votes += 1 if last_close > ema200 else -1
        if ema20 is not None and ema50 is not None:
            total += 1
            votes += 1 if ema20 > ema50 else -1
        if rsi14 is not None:
            total += 1
            if rsi14 >= 55:
                votes += 1
            elif rsi14 <= 45:
                votes -= 1
        
        bias = None
        if total > 0:
            if votes >= 2:
                bias = "Bullish"
            elif votes <= -2:
                bias = "Bearish"
            else:
                bias = "Neutral"
        
        print(f"✓ Daily bias: {bias} (confidence: {abs(votes) if total > 0 else 0}/{total})")
        
        return {
            'ema20': ema20, 'ema50': ema50, 'ema200': ema200,
            'rsi14': rsi14, 'last': last_close, 'bias': bias,
            'confidence': abs(votes) if total > 0 else None
        }
        
    except Exception as e:
        print(f"ERROR fetching daily data: {e}")
        return {
            'ema20': None, 'ema50': None, 'ema200': None,
            'rsi14': None, 'last': None, 'bias': None, 'confidence': None
        }

def fetch_nifty_option_chain():
    """Fetches Nifty 50 option chain data from NSE website"""
    url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
    
    # Try nsepython first
    data = None
    try:
        from nsepython import nsefetch
        data = nsefetch(url)
        if not isinstance(data, dict):
            raise ValueError("Unexpected response type from nsefetch")
        print("✓ Fetched option chain via nsepython")
    except Exception as e:
        print(f"nsepython failed: {e}, trying requests...")
    
    # Fallback to requests
    if data is None:
        base_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/option-chain",
        }
        
        session = requests.Session()
        retry = Retry(
            total=3, backoff_factor=0.8,
            status_forcelist=[401, 403, 429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        try:
            session.get("https://www.nseindia.com", headers=base_headers, timeout=10)
            time.sleep(0.8)
            session.get("https://www.nseindia.com/option-chain", headers=base_headers, timeout=10)
            time.sleep(0.8)
            response = session.get(url, headers=base_headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            print("✓ Fetched option chain via requests")
        except Exception as e:
            raise Exception(f"Failed to fetch NSE data: {e}")
    
    # Parse expiries
    from datetime import datetime, timedelta
    
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
        while day.weekday() != 3:
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
    
    nifty_spot = data.get('records', {}).get('underlyingValue')
    
    # Get indicators via Kite
    print("\nFetching intraday indicators...")
    bias_info = get_nifty50_indicators()
    print("\nFetching daily indicators...")
    daily_info = get_daily_bias()
    
    nifty_vwap = bias_info.get('vwap')
    nifty_last_from_kite = bias_info.get('last')
    nifty_ema9 = bias_info.get('ema9')
    nifty_ema21 = bias_info.get('ema21')
    nifty_rsi14 = bias_info.get('rsi14')
    intraday_bias = bias_info.get('bias')
    bias_conf = bias_info.get('confidence')
    daily_bias = daily_info.get('bias')
    daily_conf = daily_info.get('confidence')
    
    # Prefer Kite last if available
    if nifty_last_from_kite is not None:
        try:
            nifty_spot = float(nifty_last_from_kite)
        except Exception:
            pass
    
    # Parse option chain records
    records_all = []
    for item in data['records']['data']:
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
    
    weekly_records.sort(key=lambda r: (r.get('strikePrice') is None, r.get('strikePrice')))
    monthly_records.sort(key=lambda r: (r.get('strikePrice') is None, r.get('strikePrice')))
    
    return {
        'weekly_expiry': nearest_weekly,
        'monthly_expiry': nearest_monthly,
        'weekly_records': weekly_records,
        'monthly_records': monthly_records,
        'nifty_spot': nifty_spot,
        'nifty_vwap': nifty_vwap,
        'nifty_ema9': nifty_ema9,
        'nifty_ema21': nifty_ema21,
        'nifty_rsi14': nifty_rsi14,
        'intraday_bias': intraday_bias,
        'bias_confidence': bias_conf,
        'daily_bias': daily_bias,
        'daily_confidence': daily_conf,
    }

def render_option_chain_html(records_bundle, output_path="option_chain.html", open_in_browser=True):
    """Render option chain to HTML - Add your HTML rendering implementation here"""
    pass

if __name__ == "__main__":
    print("=" * 60)
    print("Nifty 50 Option Chain with Kite API")
    print("=" * 60)
    
    has_opened = False
    try:
        while True:
            print(f"\n[{time.strftime('%H:%M:%S')}] Fetching data...")
            try:
                records = fetch_nifty_option_chain()
                
                # Quick indicator display
                indicators = records
                print(f"\n{'='*60}")
                print(f"NIFTY: {indicators.get('nifty_spot', 0):.2f}")
                
                vwap = indicators.get('nifty_vwap')
                print(f"VWAP: {vwap:.2f if vwap is not None else 'N/A'}")
                
                ema9 = indicators.get('nifty_ema9')
                ema21 = indicators.get('nifty_ema21')
                print(f"EMA9/21: {ema9:.2f if ema9 is not None else 'N/A'} / {ema21:.2f if ema21 is not None else 'N/A'}")
                
                rsi14 = indicators.get('nifty_rsi14')
                print(f"RSI14: {rsi14:.2f if rsi14 is not None else 'N/A'}")
                
                print(f"Intraday Bias: {indicators.get('intraday_bias', 'N/A')}")
                print(f"Daily Bias: {indicators.get('daily_bias', 'N/A')}")
                print(f"{'='*60}\n")
                
                # Render HTML (add back your full render_option_chain_html function)
                # render_option_chain_html(records, open_in_browser=(not has_opened))
                
                if not has_opened:
                    print("✓ Data fetched successfully")
                    has_opened = True
                else:
                    print("✓ Updated")
                    
            except Exception as e:
                print(f"ERROR: {e}")
                import traceback
                traceback.print_exc()
            
            print("\nWaiting 5 seconds... (Ctrl+C to stop)")
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n\nStopped.")