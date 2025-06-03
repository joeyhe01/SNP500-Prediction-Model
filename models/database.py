from sqlalchemy import create_engine, Column, String, Float, Date, UniqueConstraint, Integer, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
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


# Database setup
def get_db_session():
    """Create and return a database session"""
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Create SQLite database
    engine = create_engine('sqlite:///data/stock_prices.db')
    Base.metadata.create_all(engine)
    
    # Create session
    Session = sessionmaker(bind=engine)
    return Session()


def init_database():
    """Initialize the database"""
    session = get_db_session()
    session.close()
    print("Database initialized successfully") 