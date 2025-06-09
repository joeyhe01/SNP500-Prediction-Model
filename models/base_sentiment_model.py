from transformers import pipeline
import torch
from datetime import datetime, timedelta
import json
import os
from collections import defaultdict
from models.database import get_db_session, News, NewsSentiment
from sqlalchemy import and_, or_

class BaseSentimentModel:
    def __init__(self, debug=False):
        print("Loading sentiment analysis model...")
        # Use a simpler sentiment analysis pipeline that doesn't require sentencepiece
        self.sentiment_analyzer = pipeline(
            "sentiment-analysis", 
            model="ProsusAI/finbert",
            device=0 if torch.cuda.is_available() else -1
        )
        print(f"Model loaded successfully")
        self.session = get_db_session()
        self.debug = debug
        
    def analyze_headline_sentiment(self, headline, ticker=None):
        """
        Analyze the sentiment of a headline for a specific ticker
        
        Args:
            headline: News headline text
            ticker: Stock ticker (optional, for context)
            
        Returns:
            sentiment: 'positive', 'negative', or 'neutral'
        """
        try:
            # Use the pipeline for sentiment analysis
            result = self.sentiment_analyzer(headline[:512])[0]  # Truncate to 512 chars
            
            # FinBERT returns labels like 'positive', 'negative', 'neutral'
            label = result['label'].lower()
            
            # Ensure we return a valid sentiment
            if label not in ['positive', 'negative', 'neutral']:
                return 'neutral'
                
            return label
        except Exception as e:
            print(f"Error analyzing sentiment: {e}")
            return 'neutral'
    
    def extract_ticker_from_headline(self, headline):
        """
        Extract ticker symbols from news headlines using keyword matching
        
        Args:
            headline: News headline text
            
        Returns:
            ticker: Stock ticker symbol or None if not found
        """
        import re
        
        headline_lower = headline.lower()
        
        # Common stock tickers and their associated keywords
        common_tickers = {
            'AAPL': ['Apple', 'iPhone', 'iPad', 'Mac', 'iOS', 'MacBook'],
            'MSFT': ['Microsoft', 'Windows', 'Azure', 'Office', 'Xbox', 'Surface'],
            'GOOGL': ['Google', 'Alphabet', 'YouTube', 'Android', 'Chrome', 'Gmail'],
            'AMZN': ['Amazon', 'AWS', 'Prime', 'Alexa', 'Whole Foods'],
            'META': ['Meta', 'Facebook', 'Instagram', 'WhatsApp', 'Oculus', 'Reality Labs'],
            'TSLA': ['Tesla', 'Elon Musk', 'Model 3', 'Model Y', 'Model S'],
            'NVDA': ['Nvidia', 'GeForce', 'RTX', 'CUDA', 'Jensen Huang'],
            'JPM': ['JP Morgan', 'JPMorgan', 'Chase', 'Jamie Dimon'],
            'JNJ': ['Johnson & Johnson', 'J&J'],
            'V': ['Visa'],
            'PG': ['Procter & Gamble', 'P&G', 'Tide', 'Gillette', 'Pampers'],
            'UNH': ['UnitedHealth', 'United Health', 'Optum'],
            'HD': ['Home Depot'],
            'MA': ['Mastercard', 'MasterCard'],
            'DIS': ['Disney', 'Walt Disney', 'Marvel', 'Pixar', 'ESPN'],
            'BAC': ['Bank of America', 'BofA', 'Merrill Lynch'],
            'NFLX': ['Netflix'],
            'ADBE': ['Adobe', 'Photoshop', 'Creative Cloud'],
            'CRM': ['Salesforce', 'Slack'],
            'PFE': ['Pfizer', 'BioNTech'],
            'CSCO': ['Cisco'],
            'INTC': ['Intel'],
            'WMT': ['Walmart', 'Wal-Mart', 'Sam\'s Club'],
            'IBM': ['IBM', 'Red Hat', 'Watson'],
            'BA': ['Boeing', '737', '787', 'Dreamliner'],
            'GS': ['Goldman Sachs', 'Goldman'],
            'MS': ['Morgan Stanley'],
            'CVX': ['Chevron'],
            'XOM': ['Exxon', 'ExxonMobil', 'Mobil'],
            'VZ': ['Verizon'],
            'T': ['AT&T', 'Warner'],
            'KO': ['Coca-Cola', 'Coca Cola', 'Coke'],
            'PEP': ['Pepsi', 'PepsiCo', 'Frito-Lay', 'Gatorade'],
            'NKE': ['Nike', 'Jordan'],
            'MRK': ['Merck'],
            'ABBV': ['AbbVie'],
            'TMO': ['Thermo Fisher'],
            'COST': ['Costco'],
            'AVGO': ['Broadcom'],
            'ORCL': ['Oracle'],
            'ACN': ['Accenture'],
            'LLY': ['Eli Lilly', 'Lilly'],
            'TXN': ['Texas Instruments'],
            'MCD': ['McDonald\'s', 'McDonalds'],
            'QCOM': ['Qualcomm', 'Snapdragon'],
            'DHR': ['Danaher'],
            'NEE': ['NextEra Energy', 'NextEra'],
            'BMY': ['Bristol Myers', 'Bristol-Myers'],
            'UPS': ['UPS', 'United Parcel'],
            'RTX': ['Raytheon'],
            'LOW': ['Lowe\'s', 'Lowes'],
            'SPGI': ['S&P Global', 'Standard & Poor'],
            'INTU': ['Intuit', 'TurboTax', 'QuickBooks'],
            'AMD': ['AMD', 'Advanced Micro Devices', 'Ryzen', 'Radeon'],
            'CAT': ['Caterpillar'],
            'MDLZ': ['Mondelez'],
            'GE': ['General Electric', 'GE'],
            'MMM': ['3M'],
            'CVS': ['CVS', 'Aetna'],
            'AMT': ['American Tower'],
            'AXP': ['American Express', 'Amex'],
            'DE': ['John Deere', 'Deere'],
            'BKNG': ['Booking', 'Priceline'],
            'AMAT': ['Applied Materials'],
            'TJX': ['TJX', 'TJ Maxx', 'Marshalls'],
            'ISRG': ['Intuitive Surgical', 'da Vinci'],
            'ADP': ['ADP', 'Automatic Data'],
            'GILD': ['Gilead'],
            'CME': ['CME Group', 'Chicago Mercantile'],
            'TMUS': ['T-Mobile', 'TMobile'],
            'REGN': ['Regeneron'],
            'C': ['Citigroup', 'Citi', 'Citibank'],
            'VRTX': ['Vertex'],
            'BLK': ['BlackRock'],
            'ZTS': ['Zoetis'],
            'NOW': ['ServiceNow'],
            'PANW': ['Palo Alto Networks', 'Palo Alto'],
            'SYK': ['Stryker'],
            'BSX': ['Boston Scientific'],
            'SNOW': ['Snowflake'],
            'UBER': ['Uber'],
            'SBUX': ['Starbucks'],
            'SPOT': ['Spotify'],
            'ABNB': ['Airbnb'],
            'PYPL': ['PayPal', 'Venmo'],
            'SQ': ['Square', 'Block'],
            'COIN': ['Coinbase'],
            'ROKU': ['Roku'],
            'ZM': ['Zoom'],
            'DOCU': ['DocuSign'],
            'ETSY': ['Etsy'],
            'SHOP': ['Shopify'],
            'TWLO': ['Twilio'],
            'SNAP': ['Snap', 'Snapchat'],
            'PINS': ['Pinterest'],
            'LYFT': ['Lyft'],
            'DBX': ['Dropbox'],
            'W': ['Wayfair'],
            'PTON': ['Peloton'],
            'HOOD': ['Robinhood'],
            'F': ['Ford', 'F-150'],
            'GM': ['General Motors', 'GM', 'Chevrolet', 'Chevy'],
            'RIVN': ['Rivian'],
            'LCID': ['Lucid'],
            'NIO': ['NIO'],
            'LI': ['Li Auto'],
            'XPEV': ['XPeng'],
            'PLTR': ['Palantir'],
            'NET': ['Cloudflare'],
            'DDOG': ['Datadog'],
            'CRWD': ['CrowdStrike'],
            'OKTA': ['Okta'],
            'MDB': ['MongoDB'],
            'TEAM': ['Atlassian'],
            'FTNT': ['Fortinet'],
            'WDAY': ['Workday'],
            'ADSK': ['Autodesk'],
            'EA': ['Electronic Arts', 'EA Sports'],
            'TTWO': ['Take-Two', 'Grand Theft Auto', 'GTA'],
            'ATVI': ['Activision', 'Call of Duty'],
            'RBLX': ['Roblox'],
            'U': ['Unity'],
            'MSCI': ['MSCI'],
            'SPGI': ['S&P Global'],
            'MCO': ['Moody\'s'],
            'ICE': ['Intercontinental Exchange'],
            'CME': ['CME Group'],
            'NDAQ': ['Nasdaq'],
            'CBOE': ['Cboe'],
            'WFC': ['Wells Fargo'],
            'USB': ['U.S. Bank', 'US Bank'],
            'PNC': ['PNC Bank', 'PNC'],
            'TFC': ['Truist'],
            'SCHW': ['Charles Schwab', 'Schwab'],
            'COF': ['Capital One'],
            'AIG': ['AIG', 'American International Group'],
            'MET': ['MetLife'],
            'PRU': ['Prudential'],
            'TRV': ['Travelers'],
            'AFL': ['Aflac'],
            'ALL': ['Allstate'],
            'PGR': ['Progressive'],
            'CB': ['Chubb'],
            'HIG': ['Hartford'],
            'WBA': ['Walgreens'],
            'CI': ['Cigna'],
            'HUM': ['Humana'],
            'CNC': ['Centene'],
            'ELV': ['Elevance', 'Anthem']
        }
        
        headline_lower = headline.lower()
        
        # First check for ticker symbols in parentheses or after common patterns
        import re
        
        # Pattern 1: Ticker in parentheses (e.g., "Apple (AAPL)")
        ticker_pattern = r'\(([A-Z]{1,5})\)'
        matches = re.findall(ticker_pattern, headline)
        if matches:
            # Verify it's a known ticker
            for match in matches:
                if match in common_tickers:
                    return match
        
        # Pattern 2: Ticker after "NYSE:" or "NASDAQ:" etc.
        exchange_pattern = r'(?:NYSE|NASDAQ|NYSE:|NASDAQ:|NASD:)\s*([A-Z]{1,5})'
        matches = re.findall(exchange_pattern, headline, re.IGNORECASE)
        if matches:
            for match in matches:
                if match.upper() in common_tickers:
                    return match.upper()
        
        # Pattern 3: Standalone ticker preceded by $ (e.g., "$AAPL")
        dollar_pattern = r'\$([A-Z]{1,5})\b'
        matches = re.findall(dollar_pattern, headline)
        if matches:
            for match in matches:
                if match in common_tickers:
                    return match
        
        # Check for company names/keywords
        for ticker, keywords in common_tickers.items():
            for keyword in keywords:
                # Use word boundaries for more accurate matching
                if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', headline_lower):
                    return ticker
        
        return None
    
    def store_sentiment_analysis(self, simulation_id, date, news_item, sentiment, ticker):
        """
        Store sentiment analysis result in the database
        
        Args:
            simulation_id: ID of the current simulation run
            date: Trading date
            news_item: News item from database
            sentiment: Sentiment analysis result
            ticker: Extracted ticker symbol
        """
        try:
            # Check if we already have this sentiment analysis for this simulation
            existing = self.session.query(NewsSentiment).filter(
                and_(
                    NewsSentiment.simulation_id == simulation_id,
                    NewsSentiment.date == date,
                    NewsSentiment.headline_id == news_item.id
                )
            ).first()
            
            if not existing:
                news_sentiment = NewsSentiment(
                    simulation_id=simulation_id,
                    date=date,
                    headline_id=news_item.id,
                    sentiment=sentiment,
                    ticker=ticker,
                    extra_data={}  # Will be populated later for vector db
                )
                self.session.add(news_sentiment)
                self.session.commit()
        except Exception as e:
            print(f"Error storing sentiment analysis: {e}")
            self.session.rollback()
    
    def get_trading_signals(self, date, simulation_id):
        """
        Get trading signals for a specific date based on news sentiment
        
        Args:
            date: datetime.date object
            simulation_id: ID of the current simulation run
            
        Returns:
            dict with 'long' and 'short' lists of tickers
        """
        # Calculate previous trading day
        prev_date = date - timedelta(days=1)
        
        # Skip weekends
        while prev_date.weekday() > 4:  # 5 = Saturday, 6 = Sunday
            prev_date = prev_date - timedelta(days=1)
        
        # Query news from database for the relevant time range
        # From previous day 4PM to current day 9:30AM (market open)
        start_time = datetime.combine(prev_date, datetime.min.time()).replace(hour=16, minute=0)
        end_time = datetime.combine(date, datetime.min.time()).replace(hour=9, minute=30)
        
        # Query news from database
        relevant_news = self.session.query(News).filter(
            and_(
                News.time_published >= start_time,
                News.time_published <= end_time
            )
        ).order_by(News.time_published).all()
        
        print(f"Found {len(relevant_news)} news articles for {date} from database")
        
        # Analyze sentiment for each article and store in database
        ticker_sentiments = defaultdict(list)
        
        if self.debug:
            ticker_extraction_stats = defaultdict(int)
            no_ticker_count = 0
        
        for news_item in relevant_news:
            # Extract ticker from headline
            ticker = self.extract_ticker_from_headline(news_item.title)
            
            if ticker:
                # Analyze sentiment
                sentiment = self.analyze_headline_sentiment(news_item.title, ticker)
                
                # Store in database with simulation_id
                self.store_sentiment_analysis(simulation_id, date, news_item, sentiment, ticker)
                
                # Convert sentiment to score for aggregation
                if sentiment == 'positive':
                    score = 1
                elif sentiment == 'negative':
                    score = -1  
                else:
                    score = 0
                
                ticker_sentiments[ticker].append(score)
                
                if self.debug:
                    ticker_extraction_stats[ticker] += 1
                    print(f"  {news_item.title[:80]}... -> {ticker} ({sentiment})")
            else:
                if self.debug:
                    no_ticker_count += 1
        
        if self.debug:
            print(f"\nTicker extraction stats:")
            for ticker, count in sorted(ticker_extraction_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {ticker}: {count} headlines")
            print(f"  No ticker found: {no_ticker_count} headlines")
        
        # Calculate average sentiment scores by ticker
        ticker_scores = {}
        for ticker, sentiments in ticker_sentiments.items():
            ticker_scores[ticker] = sum(sentiments) / len(sentiments)
        
        if self.debug:
            print(f"\nTicker sentiment scores:")
            for ticker, score in sorted(ticker_scores.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {ticker}: {score:.2f} (from {len(ticker_sentiments[ticker])} articles)")
        
        # Sort tickers by sentiment score
        sorted_tickers = sorted(ticker_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Get top 5 for long and bottom 5 for short
        long_tickers = []
        short_tickers = []
        
        # Get positive sentiment stocks for long
        for ticker, score in sorted_tickers:
            if score > 0 and len(long_tickers) < 5:
                long_tickers.append(ticker)
        
        # Get negative sentiment stocks for short
        for ticker, score in reversed(sorted_tickers):
            if score < 0 and len(short_tickers) < 5:
                short_tickers.append(ticker)
        
        # Ensure equal number of long and short positions
        min_positions = min(len(long_tickers), len(short_tickers))
        long_tickers = long_tickers[:min_positions]
        short_tickers = short_tickers[:min_positions]
        
        print(f"Trading signals for {date}:")
        print(f"  Long: {long_tickers}")
        print(f"  Short: {short_tickers}")
        
        return {
            'long': long_tickers,
            'short': short_tickers
        }
    
    def close(self):
        """Close the database session"""
        self.session.close() 