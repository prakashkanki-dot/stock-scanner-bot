import yfinance as yf
from telegram import Bot
import asyncio
import pandas as pd
import requests
import numpy as np
from io import StringIO
from datetime import datetime

# =====================================================
# TELEGRAM CONFIG
# =====================================================

BOT_TOKEN = "8665952511:AAFiX3USVN6qgPws8y-J6-mEyUZmRXcqpYQ"
CHAT_ID = "1391074551"

# =====================================================
# GET COMPLETE NSE MARKET
# =====================================================

def get_all_nse_stocks():

    url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers)

    df = pd.read_csv(StringIO(response.text))

    stocks = []

    for symbol in df["SYMBOL"]:

        if isinstance(symbol, str):

            if (
                "-" not in symbol
                and "&" not in symbol
                and len(symbol) > 1
            ):

                stocks.append(symbol + ".NS")

    return stocks

# =====================================================
# NIFTY BENCHMARK
# =====================================================

print("Loading Nifty Data...")

nifty_df = yf.download(
    "^NSEI",
    period="6mo",
    interval="1d",
    progress=False,
    auto_adjust=True
)

nifty_close = nifty_df["Close"].squeeze()

# =====================================================
# MARKET CAP CLASSIFICATION
# =====================================================

def get_market_cap_category(stock):

    try:

        info = yf.Ticker(stock).info

        market_cap = info.get("marketCap", 0)

        if market_cap >= 200000000000:
            return "Large Cap"

        elif market_cap >= 50000000000:
            return "Mid Cap"

        else:
            return "Small Cap"

    except:
        return None

# =====================================================
# RSI
# =====================================================

def calculate_rsi(close, period=14):

    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    return rsi

# =====================================================
# ATR
# =====================================================

def calculate_atr(df, period=14):

    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.rolling(period).mean()

    return atr

# =====================================================
# SUPERTREND
# =====================================================

def calculate_supertrend(df, period=10, multiplier=3):

    hl2 = (df["High"] + df["Low"]) / 2

    atr = calculate_atr(df, period)

    lowerband = hl2 - (multiplier * atr)

    return lowerband

# =====================================================
# MACD
# =====================================================

def calculate_macd(close):

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()

    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()

    return macd, signal

# =====================================================
# VWAP
# =====================================================

def calculate_vwap(df):

    tp = (df["High"] + df["Low"] + df["Close"]) / 3

    vwap = (tp * df["Volume"]).cumsum() / df["Volume"].cumsum()

    return vwap

# =====================================================
# CANDLESTICK PATTERN
# =====================================================

def bullish_engulfing(df):

    if len(df) < 2:
        return False

    prev_open = df["Open"].iloc[-2]
    prev_close = df["Close"].iloc[-2]

    curr_open = df["Open"].iloc[-1]
    curr_close = df["Close"].iloc[-1]

    return (
        prev_close < prev_open
        and curr_close > curr_open
        and curr_close > prev_open
        and curr_open < prev_close
    )

# =====================================================
# ANALYZE STOCK
# =====================================================

def analyze_stock(stock):

    try:

        df = yf.download(
            stock,
            period="6mo",
            interval="1d",
            progress=False,
            auto_adjust=True
        )

        if df.empty or len(df) < 100:
            return None

        close = df["Close"].squeeze()
        high = df["High"].squeeze()
        low = df["Low"].squeeze()
        volume = df["Volume"].squeeze()

        price = float(close.iloc[-1])

        score = 0
        reasons = []

        # BREAKOUT
        recent_high = float(high.tail(20).max())

        if price >= recent_high * 0.97:
            score += 2
            reasons.append("📈 Breakout")

        # 52 WEEK HIGH
        high_52 = float(high.max())

        if price >= high_52 * 0.95:
            score += 2
            reasons.append("🚀 Near 52W High")

        # VOLUME SPIKE
        avg_volume = float(volume.tail(20).mean())
        latest_volume = float(volume.iloc[-1])

        if latest_volume > avg_volume * 1.5:
            score += 2
            reasons.append("📊 Volume Spike")

        # RSI
        rsi = calculate_rsi(close)

        latest_rsi = rsi.iloc[-1]

        if 55 <= latest_rsi <= 70:
            score += 1
            reasons.append("🔥 Strong RSI")

        # MACD
        macd, signal = calculate_macd(close)

        if macd.iloc[-1] > signal.iloc[-1]:
            score += 2
            reasons.append("⚡ MACD Bullish")

        # VWAP
        vwap = calculate_vwap(df)

        if price > vwap.iloc[-1]:
            score += 1
            reasons.append("✅ Above VWAP")

        # SUPERTREND
        supertrend = calculate_supertrend(df)

        if price > supertrend.iloc[-1]:
            score += 2
            reasons.append("🟢 Supertrend Bullish")

        # ATR
        atr = calculate_atr(df)

        atr_percent = (atr.iloc[-1] / price) * 100

        if atr_percent > 2:
            score += 1
            reasons.append("📉 Good Volatility")

        # RELATIVE STRENGTH
        stock_return = (
            (close.iloc[-1] - close.iloc[-20])
            / close.iloc[-20]
        ) * 100

        nifty_return = (
            (nifty_close.iloc[-1] - nifty_close.iloc[-20])
            / nifty_close.iloc[-20]
        ) * 100

        if stock_return > nifty_return:
            score += 2
            reasons.append("🏆 Outperforming Nifty")

        # CONSOLIDATION
        recent_low = float(low.tail(20).min())

        if (recent_high - recent_low) / recent_low < 0.18:
            score += 1
            reasons.append("📦 Consolidation")

        # MOMENTUM
        if price > close.tail(5).mean():
            score += 1
            reasons.append("🚀 Momentum")

        # 20 DMA
        dma20 = close.tail(20).mean()

        if price > dma20:
            score += 1
            reasons.append("✅ Above 20 DMA")

        # CANDLESTICK
        if bullish_engulfing(df):
            score += 2
            reasons.append("🕯 Bullish Engulfing")

        # FINAL FILTER
        if score >= 10:

            return {
                "stock": stock.replace(".NS", ""),
                "price": round(price, 2),
                "score": score,
                "reasons": reasons
            }

    except:
        return None

    return None

# =====================================================
# LOAD MARKET
# =====================================================

print("Loading Complete NSE Market...")

all_stocks = get_all_nse_stocks()

print(f"Total Stocks: {len(all_stocks)}")

# =====================================================
# SCAN COMPLETE MARKET
# =====================================================

results = []

for stock in all_stocks:

    print(f"Scanning {stock}")

    result = analyze_stock(stock)

    if result:

        cap = get_market_cap_category(stock)

        if cap:

            result["cap"] = cap
            results.append(result)

# =====================================================
# SORT BEST STOCKS
# =====================================================

results = sorted(
    results,
    key=lambda x: x["score"],
    reverse=True
)

large = [x for x in results if x["cap"] == "Large Cap"][:2]
mid = [x for x in results if x["cap"] == "Mid Cap"][:2]
small = [x for x in results if x["cap"] == "Small Cap"][:2]

final_list = large + mid + small

# =====================================================
# TELEGRAM SEND
# =====================================================

async def send():

    bot = Bot(token=BOT_TOKEN)

    today = datetime.now().strftime("%d-%m-%Y")

    if not final_list:

        msg = (
            f"📅 {today}\n\n"
            "❌ No Strong Stocks Found Today"
        )

    else:

        msg = (
            f"🔥 AI MARKET SCANNER PICKS 🔥\n"
            f"📅 {today}\n\n"
        )

        for x in final_list:

            msg += (
                f"🚀 {x['stock']} ({x['cap']})\n"
                f"💰 Price: ₹{x['price']}\n"
                f"⭐ Score: {x['score']}\n"
                + "\n".join(x["reasons"])
                + "\n\n"
            )

    await bot.send_message(
        chat_id=CHAT_ID,
        text=msg
    )

# =====================================================
# RUN
# =====================================================

asyncio.run(send())
