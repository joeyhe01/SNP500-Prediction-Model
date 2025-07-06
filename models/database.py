from sqlalchemy import create_engine, Column, String, Float, Date, UniqueConstraint, Integer, DateTime, Index, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pgvector.sqlalchemy import Vector
import os
from datetime import datetime

Base = declarative_base()

class StockPrice(Base):
    __tablename__ = 'stock_prices'
    
    ticker = Column(String, primary_key=True)
    date = Column(Date, primary_key=True)
    open_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    high_price = Column(Float)
    low_price = Column(Float)
    volume = Column(Float)
    
    __table_args__ = (
        UniqueConstraint('ticker', 'date', name='_ticker_date_uc'),
    )
    
    def __repr__(self):
        return f"<StockPrice(ticker='{self.ticker}', date='{self.date}', open={self.open_price}, close={self.close_price})>"


class News(Base):
    __tablename__ = 'news'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    summary = Column(String)
    source = Column(String)
    url = Column(String, unique=True, nullable=False)
    time_published = Column(DateTime, nullable=False, index=True)
    
    __table_args__ = (
        Index('idx_time_published', 'time_published'),
    )
    
    def __repr__(self):
        return f"<News(id={self.id}, title='{self.title[:50]}...', time_published='{self.time_published}')>"


class Simulation(Base):
    __tablename__ = 'simulation'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    executed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    extra_data = Column(JSON)  # For storing simulation results and metadata
    
    def __repr__(self):
        return f"<Simulation(id={self.id}, executed_at='{self.executed_at}')>"


class NewsSentiment(Base):
    __tablename__ = 'news_sentiment'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    simulation_id = Column(Integer, nullable=False, index=True)  # References simulation.id
    date = Column(Date, nullable=False, index=True)
    headline_id = Column(Integer, nullable=False)  # References news.id
    sentiment = Column(String, nullable=False)  # 'positive', 'negative', 'neutral'
    ticker = Column(String)  # Extracted ticker from headline
    extra_data = Column(JSON)  # For future vector db use
    
    __table_args__ = (
        Index('idx_news_sentiment_simulation', 'simulation_id'),
        Index('idx_news_sentiment_date', 'date'),
        Index('idx_news_sentiment_ticker', 'ticker'),
    )
    
    def __repr__(self):
        return f"<NewsSentiment(id={self.id}, simulation_id={self.simulation_id}, date='{self.date}', headline_id={self.headline_id}, sentiment='{self.sentiment}', ticker='{self.ticker}')>"


class DailyRecap(Base):
    __tablename__ = 'daily_recap'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    simulation_id = Column(Integer, nullable=False, index=True)  # References simulation.id
    date = Column(Date, nullable=False, index=True)
    starting_money = Column(Float, nullable=False)
    ending_money = Column(Float, nullable=False)
    extra_data = Column(JSON)  # Contains shorts, longs, and returns for each action
    
    __table_args__ = (
        Index('idx_daily_recap_simulation', 'simulation_id'),
        Index('idx_daily_recap_date', 'date'),
    )
    
    def __repr__(self):
        return f"<DailyRecap(id={self.id}, simulation_id={self.simulation_id}, date='{self.date}', starting_money={self.starting_money}, ending_money={self.ending_money})>"


class RealtimePrediction(Base):
    __tablename__ = 'realtime_predictions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    prediction_data = Column(JSON, nullable=False)  # Full prediction data
    long_tickers = Column(JSON)  # List of tickers for long positions
    short_tickers = Column(JSON)  # List of tickers for short positions
    market_sentiment_score = Column(Float)  # Overall market sentiment
    
    __table_args__ = (
        Index('idx_realtime_predictions_timestamp', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<RealtimePrediction(id={self.id}, timestamp='{self.timestamp}', market_sentiment={self.market_sentiment_score})>"

class SECFilings(Base):
    __tablename__ = 'sec_filings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    accession_number = Column(String, nullable=False, index=True)  
    chunk_id = Column(Integer, nullable=False)                     
    text = Column(Text, nullable=False)                            
    company_name = Column(String)
    filing_date = Column(String, index=True)                        
    form_type = Column(String)
    cik = Column(String)
    source_file = Column(String)
    metadata_json = Column(JSON)
    embedding = Column(Vector(384))                                    

    __table_args__ = (
        # Prevent duplicates if multiple ingestions run
        UniqueConstraint('accession_number', 'chunk_id', name='uix_accession_chunk'),
    )

    def __repr__(self):
        return f"<SECFilings(accession={self.accession_number}, chunk_id={self.chunk_id})>"


_engine = None
_Session = None
_db_initialized = False

def get_engine():
    db_user = os.getenv('POSTGRES_USER', 'postgres')
    db_password = os.getenv('POSTGRES_PASSWORD', 'postgres')
    db_host = os.getenv('POSTGRES_HOST', 'localhost')
    db_port = os.getenv('POSTGRES_PORT', '5432')
    db_name = os.getenv('POSTGRES_DB', 'trading_data')
    db_url = f'postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
    return create_engine(db_url)

def init_database():
    """Initialize the database (create tables, keys, and indices if they do not exist)"""
    global _db_initialized, _engine
    if not _db_initialized:
        if _engine is None:
            _engine = get_engine()
        Base.metadata.create_all(_engine)  # Idempotent
        _db_initialized = True
        print("Database initialized successfully")

def get_db_session():
    """Create and return a database session. Initializes DB schema only once per process."""
    global _engine, _Session
    if _engine is None:
        _engine = get_engine()
    if _Session is None:
        _Session = sessionmaker(bind=_engine)
    # Ensure DB is initialized only once
    init_database()
    return _Session()