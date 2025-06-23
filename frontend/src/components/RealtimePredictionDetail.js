import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { format, parseISO } from 'date-fns';
import './Day.css';

const RealtimePredictionDetail = () => {
  const { predictionId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all'); // 'all', 'analyzed', 'not-analyzed'

  useEffect(() => {
    loadPredictionDetails();
  }, [predictionId]);

  const loadPredictionDetails = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.get(`/api/realtime/prediction/${predictionId}`);
      setData(response.data);
      console.log('Prediction data:', response.data); // Debug log
    } catch (err) {
      setError(`Error loading prediction details: ${err.response?.data?.error || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const getSentimentClass = (score) => {
    if (score > 0.1) return 'positive';
    if (score < -0.1) return 'negative';
    return 'neutral';
  };

  const getSentimentLabel = (score) => {
    if (score > 0.5) return 'Very Bullish';
    if (score > 0.1) return 'Bullish';
    if (score < -0.5) return 'Very Bearish';
    if (score < -0.1) return 'Bearish';
    return 'Neutral';
  };

  const getFilteredArticles = () => {
    if (!data || !data.news_analysis) return [];
    
    switch (filter) {
      case 'analyzed':
        return data.news_analysis.filter(article => article.has_analysis);
      case 'not-analyzed':
        return data.news_analysis.filter(article => !article.has_analysis);
      default:
        return data.news_analysis;
    }
  };

  const filteredArticles = getFilteredArticles();

  if (loading) {
    return (
      <div>
        <div className="header">
          <h1>Loading Prediction Details...</h1>
        </div>
        <div className="container">
          <div className="loading">Loading prediction analysis...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <div className="header">
          <h1>Error Loading Prediction</h1>
        </div>
        <div className="container">
          <div className="error">{error}</div>
          <button className="btn" onClick={() => navigate('/')}>Back to Dashboard</button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="header">
        <div className="header-content">
          <h1>🔴 Realtime Prediction Analysis</h1>
          <p>Detailed breakdown of news sentiment and trading signals</p>
        </div>
        <button className="btn" onClick={() => navigate('/')}>
          ← Back to Dashboard
        </button>
      </div>
      
      <div className="container">
        {/* Prediction Summary */}
        <div className="trading-section">
          <h2>Prediction Summary</h2>
          <div className="prediction-summary-grid">
            <div className="summary-item">
              <span className="summary-label">Prediction ID:</span>
              <span className="summary-value">#{data.prediction_id}</span>
            </div>
            <div className="summary-item">
              <span className="summary-label">Generated:</span>
              <span className="summary-value">
                {format(parseISO(data.timestamp), 'MMM dd, yyyy h:mm a')}
              </span>
            </div>
            <div className="summary-item">
              <span className="summary-label">News Time Range:</span>
              <span className="summary-value">
                {format(parseISO(data.time_range.start), 'MMM dd h:mm a')} - {format(parseISO(data.time_range.end), 'MMM dd h:mm a')}
              </span>
            </div>
            <div className="summary-item">
              <span className="summary-label">Articles Analyzed:</span>
              <span className="summary-value">{data.articles_analyzed} / {data.total_articles}</span>
            </div>
          </div>

          {/* Market Sentiment */}
          <div className="market-sentiment-section">
            <h3>Market Sentiment</h3>
            <div className={`sentiment-display ${getSentimentClass(data.market_sentiment_score)}`}>
              <span className="sentiment-score">{data.market_sentiment_score.toFixed(3)}</span>
              <span className="sentiment-label">{getSentimentLabel(data.market_sentiment_score)}</span>
            </div>
          </div>

          {/* Trading Signals */}
          <div className="signals-section">
            <div className="signals-grid">
              <div className="signal-column long">
                <h3>🟢 Long Positions</h3>
                {data.long_tickers && data.long_tickers.length > 0 ? (
                  <div className="signal-list">
                    {data.long_tickers.map((ticker, index) => (
                      <div key={index} className="signal-ticker">
                        {ticker}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="no-signals">No long signals</div>
                )}
              </div>
              
              <div className="signal-column short">
                <h3>🔴 Short Positions</h3>
                {data.short_tickers && data.short_tickers.length > 0 ? (
                  <div className="signal-list">
                    {data.short_tickers.map((ticker, index) => (
                      <div key={index} className="signal-ticker">
                        {ticker}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="no-signals">No short signals</div>
                )}
              </div>
            </div>
          </div>

          {/* Ticker Summary */}
          {data.ticker_summary && Object.keys(data.ticker_summary).length > 0 && (
            <div className="ticker-summary-section">
              <h3>Ticker Sentiment Summary (Current Database Analysis)</h3>
              <div className="ticker-summary-grid">
                {Object.entries(data.ticker_summary).map(([ticker, sentiments]) => (
                  <div key={ticker} className="ticker-summary-item">
                    <div className="ticker-name">{ticker}</div>
                    <div className="sentiment-counts">
                      <span className="positive-count">✅ {sentiments.positive}</span>
                      <span className="negative-count">❌ {sentiments.negative}</span>
                      <span className="neutral-count">⚪ {sentiments.neutral}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Original Prediction Data */}
          {data.prediction_data && (
            <div className="original-prediction-section">
              <h3>Original Prediction Signals (At Time of Generation)</h3>
              <div className="original-signals-note">
                <p><strong>Note:</strong> The prediction was generated using fresh API data that may differ from articles currently stored in the database. Below are the exact signals that were generated:</p>
              </div>
              
              <div className="original-signals-grid">
                <div className="original-long-signals">
                  <h4>🟢 Long Signals Generated</h4>
                  {data.prediction_data.long_signals && data.prediction_data.long_signals.length > 0 ? (
                    <div className="original-signal-list">
                      {data.prediction_data.long_signals.map((signal, index) => (
                        <div key={index} className="original-signal-item">
                          <span className="signal-ticker">{signal.ticker}</span>
                          <div className="signal-metrics">
                            <span className="signal-score">Score: {signal.score.toFixed(3)}</span>
                            <span className="signal-articles">{signal.article_count} articles</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="no-original-signals">No long signals</div>
                  )}
                </div>

                <div className="original-short-signals">
                  <h4>🔴 Short Signals Generated</h4>
                  {data.prediction_data.short_signals && data.prediction_data.short_signals.length > 0 ? (
                    <div className="original-signal-list">
                      {data.prediction_data.short_signals.map((signal, index) => (
                        <div key={index} className="original-signal-item">
                          <span className="signal-ticker">{signal.ticker}</span>
                          <div className="signal-metrics">
                            <span className="signal-score">Score: {signal.score.toFixed(3)}</span>
                            <span className="signal-articles">{signal.article_count} articles</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="no-original-signals">No short signals</div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* News Analysis */}
        <div className="news-section">
          <h2>News Analysis ({data.news_analysis.length} articles)</h2>
          
          {/* Filter buttons */}
          <div className="filter-buttons">
            <button 
              className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
              onClick={() => setFilter('all')}
            >
              All Articles ({data.news_analysis.length})
            </button>
            <button 
              className={`filter-btn ${filter === 'analyzed' ? 'active' : ''}`}
              onClick={() => setFilter('analyzed')}
            >
              Analyzed ({data.articles_analyzed})
            </button>
            <button 
              className={`filter-btn ${filter === 'not-analyzed' ? 'active' : ''}`}
              onClick={() => setFilter('not-analyzed')}
            >
              Not Analyzed ({data.total_articles - data.articles_analyzed})
            </button>
          </div>

          <div className="news-list">
            {filteredArticles.length > 0 ? (
              filteredArticles.map(article => (
                <NewsItem key={article.headline_id} item={article} />
              ))
            ) : (
              <div className="no-news">
                No articles found for the selected filter.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const NewsItem = ({ item }) => {
  const [expanded, setExpanded] = useState(false);

  const getSentimentBadgeClass = (sentiment) => {
    if (!sentiment) return 'sentiment-no-analysis';
    switch (sentiment?.toLowerCase()) {
      case 'positive': return 'sentiment-positive';
      case 'negative': return 'sentiment-negative';
      default: return 'sentiment-neutral';
    }
  };

  const getSentimentDisplayText = (sentiment, hasAnalysis) => {
    if (!hasAnalysis) return 'No Analysis';
    return sentiment || 'Neutral';
  };

  return (
    <div className={`news-item ${item.has_analysis ? 'analyzed' : 'not-analyzed'}`}>
      <div className="news-header">
        <div className="news-meta">
          <span className="news-source">{item.source}</span>
          <span className="news-time">
            {format(parseISO(item.time_published), 'h:mm a')}
          </span>
          {!item.has_analysis && (
            <span className="analysis-status">📰 News Only</span>
          )}
          {item.has_analysis && (
            <span className="analysis-status">🔍 Used for Prediction</span>
          )}
        </div>
        <div className="news-sentiment-info">
          <span className={`sentiment-badge ${getSentimentBadgeClass(item.sentiment)}`}>
            {getSentimentDisplayText(item.sentiment, item.has_analysis)}
          </span>
          {item.identified_ticker && (
            <span className="ticker-badge">{item.identified_ticker}</span>
          )}
        </div>
      </div>
      
      <h3 className="news-title">{item.title}</h3>
      
      {item.summary && (
        <div className="news-summary">
          <p>{expanded ? item.summary : `${item.summary.substring(0, 200)}...`}</p>
          {item.summary.length > 200 && (
            <button 
              className="expand-btn"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? 'Show Less' : 'Show More'}
            </button>
          )}
        </div>
      )}
      
      {item.url && (
        <div className="news-actions">
          <a 
            href={item.url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="news-link"
          >
            Read Full Article →
          </a>
        </div>
      )}
    </div>
  );
};

export default RealtimePredictionDetail; 