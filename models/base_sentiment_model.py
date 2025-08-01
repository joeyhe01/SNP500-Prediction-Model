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
        self.debug = debug
        self.session = get_db_session()
        
        try:
            # Force CPU usage to avoid meta tensor issues with GPU
            print("Initializing sentiment analyzer on CPU...")
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis", 
                model="ProsusAI/finbert",
                device=-1,  # Force CPU
                return_all_scores=False,
                top_k=1
            )
            print("Model loaded successfully on CPU")
        except Exception as e:
            print(f"Error loading FinBERT model: {e}")
            print("Falling back to default sentiment model...")
            try:
                # Fallback to a more reliable model
                self.sentiment_analyzer = pipeline(
                    "sentiment-analysis",
                    model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                    device=-1,  # Force CPU
                    return_all_scores=False,
                    top_k=1
                )
                print("Fallback model loaded successfully")
            except Exception as e2:
                print(f"Error loading fallback model: {e2}")
                print("Using basic sentiment analyzer...")
                # Last resort: use a very simple model
                self.sentiment_analyzer = pipeline(
                    "sentiment-analysis",
                    device=-1,  # Force CPU
                    return_all_scores=False,
                    top_k=1
                )
                print("Basic model loaded successfully")
        
     
        
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
            # Input validation
            if not headline or not isinstance(headline, str):
                if self.debug:
                    print(f"Invalid headline input: {headline}")
                return 'neutral'
            
            # Clean and truncate the headline
            clean_headline = headline.strip()
            if len(clean_headline) == 0:
                return 'neutral'
            
            # Truncate to avoid model limits
            clean_headline = clean_headline[:512]
            
            # Use the pipeline for sentiment analysis with error handling
            try:
                result = self.sentiment_analyzer(clean_headline)
                
                # Debug: log the raw result format
                if self.debug:
                    print(f"Raw sentiment result type: {type(result)}, value: {result}")
                
                # Handle different result formats more robustly
                if isinstance(result, list):
                    if len(result) == 0:
                        if self.debug:
                            print("Empty result list from sentiment analyzer")
                        return 'neutral'
                    
                    # Take the first result and validate it
                    result = result[0]
                    
                    # Check if the first result is still a list (nested lists)
                    if isinstance(result, list):
                        if len(result) > 0:
                            result = result[0]
                        else:
                            if self.debug:
                                print("Nested empty list in sentiment result")
                            return 'neutral'
                
                # Ensure we have a dictionary at this point
                if not isinstance(result, dict):
                    if self.debug:
                        print(f"Unexpected result format after processing: {type(result)}, value: {result}")
                    return 'neutral'
                
                # Extract label safely
                label = result.get('label', '').lower()
                
                # Map different label formats to standard ones
                if label in ['positive', 'pos', 'label_2']:
                    return 'positive'
                elif label in ['negative', 'neg', 'label_0']:
                    return 'negative'
                elif label in ['neutral', 'neu', 'label_1']:
                    return 'neutral'
                else:
                    # For unknown labels, try to parse from score
                    score = result.get('score', 0)
                    if isinstance(score, (int, float)):
                        if score > 0.6:
                            return 'positive' if 'positive' in label or 'pos' in label else 'negative'
                        elif score < 0.4:
                            return 'neutral'
                        else:
                            return 'neutral'
                    else:
                        if self.debug:
                            print(f"Unknown label format: {label}, defaulting to neutral")
                        return 'neutral'
                        
            except RuntimeError as e:
                if "meta tensor" in str(e).lower():
                    print(f"Meta tensor error in sentiment analysis: {e}")
                    print("This suggests a model loading issue. Returning neutral.")
                    return 'neutral'
                else:
                    raise e
                    
        except Exception as e:
            if self.debug:
                print(f"Error analyzing sentiment for '{headline[:50]}...': {e}")
            else:
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
        ticker_sentiment_counts = defaultdict(lambda: {'positive': 0, 'negative': 0, 'neutral': 0})
        
        # Progress tracking variables
        processed_articles = 0
        sentiment_pairs_created = 0
        total_articles = len(relevant_news)
        
        if self.debug:
            ticker_extraction_stats = defaultdict(int)
            no_ticker_count = 0
            print(f"Starting sentiment analysis for {total_articles} articles...")
        
        for i, news_item in enumerate(relevant_news, 1):
            # Extract ticker from headline
            ticker = self.extract_ticker_from_headline(news_item.title)
            
            if ticker:
                # Analyze sentiment
                sentiment = self.analyze_headline_sentiment(news_item.title, ticker)
                
                # Store in database with simulation_id
                self.store_sentiment_analysis(simulation_id, date, news_item, sentiment, ticker)
                
                # Count sentiments by type
                ticker_sentiment_counts[ticker][sentiment] += 1
                
                processed_articles += 1
                sentiment_pairs_created += 1
                
                if self.debug:
                    ticker_extraction_stats[ticker] += 1
                    print(f"  {news_item.title[:80]}... -> {ticker} ({sentiment})")
            else:
                processed_articles += 1
                if self.debug:
                    no_ticker_count += 1
            
            # Progress logging every 10 articles
            if i % 10 == 0 or i == total_articles:
                progress_pct = (i / total_articles) * 100
                print(f"Progress: {i}/{total_articles} articles analyzed ({progress_pct:.1f}%), {sentiment_pairs_created} sentiment pairs created")
        
        print(f"\nCompleted sentiment analysis:")
        print(f"  Processed: {processed_articles} articles")
        print(f"  Created: {sentiment_pairs_created} ticker-sentiment pairs")
        print(f"  Unique tickers found: {len(ticker_sentiment_counts)}")
        
        if self.debug:
            print(f"\nTicker extraction stats:")
            for ticker, count in sorted(ticker_extraction_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {ticker}: {count} headlines")
            print(f"  No ticker found: {no_ticker_count} headlines")
        
        # Calculate net sentiment (positive - negative) for each ticker
        ticker_net_sentiment = {}
        for ticker, counts in ticker_sentiment_counts.items():
            net_sentiment = counts['positive'] - counts['negative']
            ticker_net_sentiment[ticker] = net_sentiment
        
        if self.debug:
            print(f"\nTicker net sentiment (positive - negative):")
            for ticker, net_sentiment in sorted(ticker_net_sentiment.items(), key=lambda x: x[1], reverse=True)[:10]:
                counts = ticker_sentiment_counts[ticker]
                total_articles = counts['positive'] + counts['negative'] + counts['neutral']
                print(f"  {ticker}: {net_sentiment:+d} (pos:{counts['positive']}, neg:{counts['negative']}, neu:{counts['neutral']}, total:{total_articles})")
        
        # Sort tickers by net sentiment (positive - negative)
        sorted_tickers = sorted(ticker_net_sentiment.items(), key=lambda x: x[1], reverse=True)
        
        # Get top 5 for long (highest positive-negative) and bottom 5 for short (lowest positive-negative)
        long_tickers = []
        short_tickers = []
        
        # Get tickers with highest net positive sentiment for long positions
        for ticker, net_sentiment in sorted_tickers:
            if net_sentiment > 0 and len(long_tickers) < 5:
                long_tickers.append(ticker)
        
        # Get tickers with lowest net sentiment (most negative) for short positions
        for ticker, net_sentiment in reversed(sorted_tickers):
            if net_sentiment < 0 and len(short_tickers) < 5:
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