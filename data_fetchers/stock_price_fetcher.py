import requests
import json
import time
from datetime import datetime, timedelta
from models.database import get_db_session, StockPrice
from sqlalchemy import and_

class StockPriceFetcher:
    def __init__(self, api_key='KWL2J50Q32KS3YSM'):
        self.api_key = api_key
        self.session = get_db_session()
        
    def get_stock_price(self, ticker, date):
        """
        Get stock price for a specific ticker and date.
        First checks the database, then fetches from API if needed.
        
        Args:
            ticker: Stock ticker symbol
            date: datetime.date object
            
        Returns:
            dict with open_price and close_price, or None if not available
        """
        # Check database first
        stock_price = self.session.query(StockPrice).filter(
            and_(StockPrice.ticker == ticker, StockPrice.date == date)
        ).first()
        
        if stock_price:
            return {
                'open': stock_price.open_price,
                'close': stock_price.close_price,
                'high': stock_price.high_price,
                'low': stock_price.low_price,
                'volume': stock_price.volume
            }
        
        # If not in database, fetch from API
        self._fetch_and_store_stock_data(ticker)
        
        # Try again from database
        stock_price = self.session.query(StockPrice).filter(
            and_(StockPrice.ticker == ticker, StockPrice.date == date)
        ).first()
        
        if stock_price:
            return {
                'open': stock_price.open_price,
                'close': stock_price.close_price,
                'high': stock_price.high_price,
                'low': stock_price.low_price,
                'volume': stock_price.volume
            }
        
        return None
    
    def _fetch_and_store_stock_data(self, ticker, max_retries=3):
        """
        Fetch stock data from Alpha Vantage and store in database
        """
        # First check if we already have data for this ticker
        existing_count = self.session.query(StockPrice).filter(
            StockPrice.ticker == ticker
        ).count()
        
        if existing_count > 0:  # If we have ANY data, we've already fetched everything
            print(f"Already have {existing_count} days of data for {ticker}, skipping API call")
            return
        
        print(f"Fetching price data for {ticker} from API...")
        url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ticker}&outputsize=full&apikey={self.api_key}'
        
        for retry in range(max_retries):
            try:
                response = requests.get(url)
                data = response.json()
                
                if 'Error Message' in data:
                    print(f"Error: Invalid ticker symbol {ticker}")
                    return
                
                if 'Note' in data:
                    print(f"API limit reached. Waiting 60 seconds...")
                    time.sleep(60)
                    continue
                
                if 'Time Series (Daily)' not in data:
                    print(f"Unexpected response format for {ticker}")
                    return
                
                # Parse and store the data
                time_series = data['Time Series (Daily)']
                
                added_count = 0
                for date_str, price_data in time_series.items():
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    
                    # Only store data for our target period (2022-03-01 to 2024-03-01)
                    if date_obj < datetime(2022, 3, 1).date() or date_obj > datetime(2024, 3, 1).date():
                        continue
                    
                    # Check if we already have this data
                    existing = self.session.query(StockPrice).filter(
                        and_(StockPrice.ticker == ticker, StockPrice.date == date_obj)
                    ).first()
                    
                    if not existing:
                        stock_price = StockPrice(
                            ticker=ticker,
                            date=date_obj,
                            open_price=float(price_data['1. open']),
                            close_price=float(price_data['4. close']),
                            high_price=float(price_data['2. high']),
                            low_price=float(price_data['3. low']),
                            volume=float(price_data['5. volume'])
                        )
                        self.session.add(stock_price)
                        added_count += 1
                
                self.session.commit()
                print(f"Successfully stored {added_count} new price records for {ticker}")
                
                return
                
            except Exception as e:
                print(f"Error fetching data for {ticker}: {e}")
                if retry < max_retries - 1:
                    time.sleep(5)
                    continue
                else:
                    raise
    
    def get_price_range(self, ticker, start_date, end_date):
        """
        Get stock prices for a date range
        """
        prices = self.session.query(StockPrice).filter(
            and_(
                StockPrice.ticker == ticker,
                StockPrice.date >= start_date,
                StockPrice.date <= end_date
            )
        ).order_by(StockPrice.date).all()
        
        if not prices:
            # Try fetching from API
            self._fetch_and_store_stock_data(ticker)
            
            # Query again
            prices = self.session.query(StockPrice).filter(
                and_(
                    StockPrice.ticker == ticker,
                    StockPrice.date >= start_date,
                    StockPrice.date <= end_date
                )
            ).order_by(StockPrice.date).all()
        
        return prices
    
    def close(self):
        """Close the database session"""
        self.session.close() 