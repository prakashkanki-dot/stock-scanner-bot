import yfinance as yf
from telegram import Bot
import asyncio

BOT_TOKEN = "8665952511:AAFiX3USVN6qgPws8y-J6-mEyUZmRXcqpYQ"
CHAT_ID = "1391074551"

stocks = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "LT.NS",
    "ITC.NS",
    "BHARTIARTL.NS"
]

results = []

for stock in stocks:

    try:

        print(f"Checking {stock}")

        df = yf.download(
            stock,
            period="3mo",
            interval="1d",
            progress=False,
            auto_adjust=True
        )

        if df.empty:
            continue

        # IMPORTANT FIX
        close_prices = df["Close"].squeeze()
        high_prices = df["High"].squeeze()
        low_prices = df["Low"].squeeze()
        volume_data = df["Volume"].squeeze()

        current_price = round(close_prices.iloc[-1], 2)

        recent_high = high_prices.tail(20).max()

        recent_low = low_prices.tail(20).min()

        latest_volume = volume_data.iloc[-1]

        avg_volume = volume_data.tail(20).mean()

        score = 0
        reasons = []

        # =========================
        # BREAKOUT
        # =========================

        if current_price >= recent_high * 0.95:

            score += 2
            reasons.append("📈 Near Breakout")

        # =========================
        # VOLUME
        # =========================

        if latest_volume >= avg_volume * 1.1:

            score += 2
            reasons.append("📊 Volume Spike")

        # =========================
        # CONSOLIDATION
        # =========================

        range_percent = (
            (recent_high - recent_low)
            / recent_low
        )

        if range_percent < 0.20:

            score += 1
            reasons.append("📦 Consolidation")

        # =========================
        # MOMENTUM
        # =========================

        avg_close_5 = close_prices.tail(5).mean()

        if current_price > avg_close_5:

            score += 1
            reasons.append("🚀 Positive Momentum")

        print(f"{stock} Score = {score}")

        # =========================
        # FINAL FILTER
        # =========================

        if score >= 3:

            results.append({
                "stock": stock,
                "price": current_price,
                "score": score,
                "reasons": reasons
            })

    except Exception as e:

        print(f"ERROR in {stock}")
        print(e)

# =========================
# SORT RESULTS
# =========================

results = sorted(
    results,
    key=lambda x: x["score"],
    reverse=True
)

top_results = results[:5]

# =========================
# TELEGRAM MESSAGE
# =========================

async def send_message():

    bot = Bot(token=BOT_TOKEN)

    if top_results:

        final_message = "🔥 TOP STOCK SETUPS 🔥\n\n"

        for item in top_results:

            final_message += (
                f"🚀 {item['stock']}\n"
                f"💰 Price: ₹{item['price']}\n"
                f"⭐ Score: {item['score']}/6\n"
                + "\n".join(item["reasons"])
                + "\n\n"
            )

    else:

        final_message = (
            "❌ No Good Stocks Found Today"
        )

    await bot.send_message(
        chat_id=CHAT_ID,
        text=final_message
    )

asyncio.run(send_message())
