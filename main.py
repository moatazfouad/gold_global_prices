from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yfinance as yf
from datetime import datetime
import os
import uvicorn

app = FastAPI()

class GoldRequest(BaseModel):
    symbol: str = "GC=F"
    start_date: str  # format "YYYY-MM-DD"
    end_date: str    # format "YYYY-MM-DD"

class GoldResponse(BaseModel):
    symbol: str
    name: str
    price: float
    changePercentage: float
    change: float
    volume: int
    dayLow: float
    dayHigh: float
    yearHigh: float
    yearLow: float
    marketCap: float | None
    priceAvg50: float
    priceAvg200: float
    exchange: str
    open: float
    previousClose: float
    timestamp: int

@app.post("/gold-price", response_model=list[GoldResponse])
async def get_gold_price_range(request: GoldRequest):
    try:
        # Validate date format
        try:
            start_dt = datetime.strptime(request.start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(request.end_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Dates must be in YYYY-MM-DD format")
        
        ticker = yf.Ticker(request.symbol)
        data = ticker.history(start=request.start_date, end=request.end_date)
        info = ticker.info

        if data.empty:
            raise HTTPException(status_code=404, detail="No data available for this date range")

        responses = []
        previous_close = None

        for idx, row in data.iterrows():
            close_price = float(row['Close'])
            open_price = float(row['Open'])
            low = float(row['Low'])
            high = float(row['High'])
            volume = int(row['Volume']) if 'Volume' in row else 0

            if previous_close is None:
                change = 0
                change_percentage = 0
            else:
                change = close_price - previous_close
                change_percentage = (change / previous_close) * 100 if previous_close != 0 else 0

            previous_close = close_price

            response = GoldResponse(
                symbol=request.symbol,
                name=info.get('shortName', 'Gold'),
                price=close_price,
                changePercentage=round(change_percentage, 2),
                change=round(change, 2),
                volume=volume,
                dayLow=low,
                dayHigh=high,
                yearHigh=float(info.get('fiftyTwoWeekHigh', 0)),
                yearLow=float(info.get('fiftyTwoWeekLow', 0)),
                marketCap=float(info.get('marketCap')) if info.get('marketCap') else None,
                priceAvg50=float(info.get('fiftyDayAverage', 0)),
                priceAvg200=float(info.get('twoHundredDayAverage', 0)),
                exchange=info.get('exchange', 'COMEX'),
                open=open_price,
                previousClose=previous_close,
                timestamp=int(idx.timestamp())
            )

            responses.append(response)

        return responses

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- RUN SERVER ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
