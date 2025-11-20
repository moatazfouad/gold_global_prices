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


class HistoricalOuncePriceResponse(BaseModel):
    date: str
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    adjClose: float | None
    volume: int | None
    unadjustedVolume: int | None
    change: float | None
    changePercent: float | None
    vwap: float | None
    label: str | None
    changeOverTime: float | None


@app.post("/gold-price", response_model=list[HistoricalOuncePriceResponse])
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

        if data.empty:
            raise HTTPException(status_code=404, detail="No data available for this date range")

        responses = []
        previous_close = None

        for idx, row in data.iterrows():
            close_price = float(row['Close'])
            open_price = float(row['Open'])
            low_price = float(row['Low'])
            high_price = float(row['High'])
            volume = int(row['Volume']) if 'Volume' in row else 0

            # Change vs previous close
            if previous_close is None:
                change = 0
                change_percent = 0
            else:
                change = close_price - previous_close
                change_percent = (change / previous_close) * 100 if previous_close != 0 else 0

            previous_close = close_price

            # VWAP: (high + low + close) / 3
            vwap = (high_price + low_price + close_price) / 3

            response = HistoricalOuncePriceResponse(
                date=idx.isoformat(),
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                adjClose=close_price,  # For simplicity, same as close
                volume=volume,
                unadjustedVolume=volume,
                change=round(change, 2),
                changePercent=round(change_percent, 2),
                vwap=round(vwap, 2),
                label=idx.strftime("%b %d, %Y"),
                changeOverTime=round(change / close_price if close_price != 0 else 0, 4)
            )

            responses.append(response)

        return responses

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- RUN SERVER ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
