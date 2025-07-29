'''
Get data from EODHD API for S&P 500 companies.
This will create an "eodhd_data" directory with JSON files for each ticker.
Then use the "backfill_vector_db.py" script to insert the data into faiss vector database.
Make sure to export USE_SQLITE=true in terminal/bash before running the backfill function
So the code knows to use SQLite instead of Postgres. Postgres has not been fully integrated yet.
'''
import os, json, requests
from datetime import datetime
from typing import List
import pandas as pd

# --- Config ---
#EODHD_API_KEY = os.getenv("EODHD_API_KEY", "your-api-key")
EODHD_API_KEY = ' 6888359d906c44.03885468'
BASE_URL = "https://eodhd.com/api/news"
OUTPUT_DIR = "eodhd_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_eodhd_news(ticker: str, from_date: str, to_date: str, limit: int = 100) -> List[dict]:
    params = {
        "api_token": EODHD_API_KEY,
        "s": ticker,
        "from": from_date,
        "to": to_date,
        "limit": limit,
    }

    print(f"Fetching news for {ticker} from {from_date} to {to_date}...")
    response = requests.get(BASE_URL, params=params)
    if response.status_code != 200:
        print(f"⚠️ Error fetching data: {response.status_code} {response.text}")
        return []

    data = response.json()
    return data


def save_news_to_file(ticker: str, data: List[dict], from_date: str, to_date: str):
    safe_ticker = ticker.replace(".", "_")
    filename = f"{safe_ticker}_{from_date}_to_{to_date}.json"
    path = os.path.join(OUTPUT_DIR, filename)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved {len(data)} articles to {path}")


def fetch_and_store(ticker: str, from_date: str, to_date: str, limit: int = 100):
    data = fetch_eodhd_news(ticker, from_date, to_date, limit)
    if data:
        save_news_to_file(ticker, data, from_date, to_date)

#get ticker dictionary from wiki
def get_tickers() -> dict[str, str]:
    '''
    Scrap wikipedia page to get the current S&P 500 tickers and their CIKs.
    Returns a dictionary with tickers as keys and CIKs as values.
    Replace '.' with '-' to match the format used in SEC filings.

    INPUTS:
    -   None

    OUTPUTS:
    -   dict[str, str] - A dictionary mapping tickers to CIKs.
    '''

    # Define the URL for the S&P 500 companies list
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    tables = pd.read_html(url)
    df = tables[0]
    
    # Create a dictionary mapping tickers to CIKs
    tickers_ciks = dict(zip(df['Symbol'].str.replace('.', '-'), df['CIK']))
    # Ensure all tickers are uppercase
    tickers_ciks = {ticker.upper(): cik for ticker, cik in tickers_ciks.items()}
    #Make sure CIKs are strings
    tickers_ciks = {ticker: f"{int(cik):010d}" for ticker, cik in tickers_ciks.items()}

    return tickers_ciks

def main():
    #ticker_list = ["AAPL.US", "MSFT.US", "TSLA.US"]

    from_date = "2025-06-01"
    to_date = "2025-06-20"
    limit = 100  # Max per EODHD spec
    ticker_list = [ticker for ticker in get_tickers().keys()]
    for ticker in ticker_list:
        try:
            fetch_and_store(ticker, from_date, to_date, limit)
        except Exception as e:
            print(f"❌ Error processing {ticker}: {e}")


if __name__ == "__main__":
    main()