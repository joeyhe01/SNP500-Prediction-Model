import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { format, parseISO } from 'date-fns';
import { parseTimestamp, formatTimestampWithTimezone, formatTimestamp } from '../utils/timeUtils';
import './Day.css';

const Day = () => {
  const { simulationId, date } = useParams();
  const navigate = useNavigate();
  const [dayData, setDayData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // State for similar articles functionality
  const [expandedSimilarArticles, setExpandedSimilarArticles] = useState({});
  const [similarArticlesData, setSimilarArticlesData] = useState({});
  const [loadingSimilarArticles, setLoadingSimilarArticles] = useState({});

  useEffect(() => {
    loadData();
  }, [simulationId, date]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.get(`/api/simulation/${simulationId}/day/${date}`);
      setDayData(response.data);
    } catch (err) {
      setError(`Error loading data: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Function to load similar articles for a sentiment record
  const loadSimilarArticles = async (sentimentId) => {
    setLoadingSimilarArticles(prev => ({ ...prev, [sentimentId]: true }));
    
    try {
      const response = await axios.get(`/api/sentiment/${sentimentId}/similar_articles`);
      setSimilarArticlesData(prev => ({ 
        ...prev, 
        [sentimentId]: response.data.similar_articles 
      }));
    } catch (err) {
      console.error(`Error loading similar articles for sentiment ${sentimentId}:`, err);
      setSimilarArticlesData(prev => ({ 
        ...prev, 
        [sentimentId]: [] 
      }));
    } finally {
      setLoadingSimilarArticles(prev => ({ ...prev, [sentimentId]: false }));
    }
  };

  // Function to toggle similar articles dropdown
  const toggleSimilarArticles = (sentimentId) => {
    const isCurrentlyExpanded = expandedSimilarArticles[sentimentId];
    
    setExpandedSimilarArticles(prev => ({
      ...prev,
      [sentimentId]: !isCurrentlyExpanded
    }));
    
    // Load similar articles if expanding and not already loaded
    if (!isCurrentlyExpanded && !similarArticlesData[sentimentId]) {
      loadSimilarArticles(sentimentId);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const getSentimentBadgeClass = (sentiment) => {
    switch (sentiment?.toLowerCase()) {
      case 'positive': return 'sentiment-positive';
      case 'negative': return 'sentiment-negative';
      default: return 'sentiment-neutral';
    }
  };

  if (loading) {
    return (
      <div>
        <div className="header-nav">
          <div className="header-content">
            <h1>Simulation {simulationId} - {date}</h1>
            <button className="back-btn" onClick={() => navigate(`/simulation/${simulationId}`)}>
              ← Back to Simulation
            </button>
          </div>
        </div>
        <div className="container">
          <div className="loading">Loading day details...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <div className="header-nav">
          <div className="header-content">
            <h1>Simulation {simulationId} - {date}</h1>
            <button className="back-btn" onClick={() => navigate(`/simulation/${simulationId}`)}>
              ← Back to Simulation
            </button>
          </div>
        </div>
        <div className="container">
          <div className="error">{error}</div>
        </div>
      </div>
    );
  }

  if (!dayData) {
    return (
      <div>
        <div className="header-nav">
          <div className="header-content">
            <h1>Simulation {simulationId} - {date}</h1>
            <button className="back-btn" onClick={() => navigate(`/simulation/${simulationId}`)}>
              ← Back to Simulation
            </button>
          </div>
        </div>
        <div className="container">
          <div className="no-data">
            <h3>No Data Found</h3>
            <p>No data available for this day.</p>
          </div>
        </div>
      </div>
    );
  }

  const { daily_summary, news_analysis } = dayData;

  return (
    <div>
      <div className="header-nav">
        <div className="header-content">
          <h1>Simulation {simulationId} - {format(parseISO(date), 'MMM dd, yyyy')}</h1>
          <button className="back-btn" onClick={() => navigate(`/simulation/${simulationId}`)}>
            ← Back to Simulation
          </button>
        </div>
      </div>
      
      <div className="container">
        {daily_summary && (
          <div className="day-summary">
            <h2 className="section-title">Daily Trading Summary</h2>
            <div className="summary-grid">
              <div className="summary-item">
                <span className="summary-label">Starting Portfolio:</span>
                <span className="summary-value">{formatCurrency(daily_summary.starting_money)}</span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Ending Portfolio:</span>
                <span className="summary-value">{formatCurrency(daily_summary.ending_money)}</span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Daily P&L:</span>
                <span className={`summary-value ${daily_summary.daily_pnl >= 0 ? 'positive' : 'negative'}`}>
                  {daily_summary.daily_pnl >= 0 ? '+' : ''}{formatCurrency(daily_summary.daily_pnl)}
                </span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Number of Trades:</span>
                <span className="summary-value">{daily_summary.trades?.length || 0}</span>
              </div>
            </div>
            
            {daily_summary.trades && daily_summary.trades.length > 0 && (
              <div className="trades-section">
                <h3 className="subsection-title">Trades Executed</h3>
                <div className="trades-list">
                  {daily_summary.trades
                    .sort((a, b) => {
                      // Sort by time (market_open first, then market_close)
                      if (a.time === 'market_open' && b.time === 'market_close') return -1;
                      if (a.time === 'market_close' && b.time === 'market_open') return 1;
                      return 0;
                    })
                    .map((trade, index) => (
                    <div key={index} className="trade-item">
                      <div className="trade-main">
                        <span className={`trade-action ${trade.action}`}>
                          {trade.action?.toUpperCase()}
                        </span>
                        <span className="trade-ticker">{trade.ticker}</span>
                        <span className="trade-shares">{trade.shares} shares</span>
                        <span className="trade-price">@ {formatCurrency(trade.price)}</span>
                        <span className={`trade-timing ${trade.time}`}>
                          {trade.time === 'market_open' ? '📈 Open' : '📉 Close'}
                        </span>
                      </div>
                      <div className="trade-details">
                        <span className="trade-total">
                          Total: {formatCurrency(trade.total_value || (trade.shares * trade.price))}
                        </span>
                        {trade.pnl && (
                          <span className={`trade-pnl ${trade.pnl >= 0 ? 'positive' : 'negative'}`}>
                            P&L: {trade.pnl >= 0 ? '+' : ''}{formatCurrency(trade.pnl)}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        
        <div className="news-section">
          <h2 className="section-title">
            News Headlines for {format(parseISO(date), 'MMM dd, yyyy')} 
            ({news_analysis?.length || 0} total, {news_analysis?.filter(item => item.has_analysis).length || 0} analyzed)
          </h2>
          
          {news_analysis && news_analysis.length > 0 ? (
            <div className="news-list">
              {news_analysis
                .sort((a, b) => {
                  // Sort analyzed articles first (has_analysis: true), then non-analyzed
                  if (a.has_analysis && !b.has_analysis) return -1;
                  if (!a.has_analysis && b.has_analysis) return 1;
                  // Within each group, sort by time (most recent first)
                  return parseTimestamp(b.time_published) - parseTimestamp(a.time_published);
                })
                .map((item) => (
                  <NewsItem 
                    key={item.headline_id} 
                    item={item}
                    expandedSimilarArticles={expandedSimilarArticles}
                    toggleSimilarArticles={toggleSimilarArticles}
                    loadingSimilarArticles={loadingSimilarArticles}
                    similarArticlesData={similarArticlesData}
                  />
                ))}
            </div>
          ) : (
            <div className="no-news">
              <p>No news headlines available for this day.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const NewsItem = ({ item, expandedSimilarArticles, toggleSimilarArticles, loadingSimilarArticles, similarArticlesData }) => {
  const [expanded, setExpanded] = useState(false);

  const getSentimentBadgeClass = (sentiment) => {
    if (!sentiment) return 'sentiment-no-analysis';
    switch (sentiment?.toLowerCase()) {
      case 'positive': return 'sentiment-positive';
      case 'negative': return 'sentiment-negative';
      default: return 'sentiment-neutral';
    }
  };

  // Find the first sentiment record that has similar articles data for this article
  const getSimilarArticlesData = () => {
    if (!item.sentiment_data || !Array.isArray(item.sentiment_data)) return null;
    
    for (const sentiment of item.sentiment_data) {
      if (sentiment.id && sentiment.similar_news_faiss_ids && 
          Array.isArray(sentiment.similar_news_faiss_ids) && 
          sentiment.similar_news_faiss_ids.length > 0) {
        return {
          sentimentId: sentiment.id,
          similarIds: sentiment.similar_news_faiss_ids
        };
      }
    }
    return null;
  };



  return (
    <div className={`news-item ${item.has_analysis ? 'analyzed' : 'not-analyzed'}`}>
      <div className="news-header">
        <div className="news-meta">
          <span className="news-source">{item.source}</span>
          <span className="news-time" title={formatTimestampWithTimezone(item.time_published)}>
            {formatTimestamp(item.time_published)}
          </span>
          {!item.has_analysis && (
            <span className="analysis-status">📰 News Only</span>
          )}
          {item.has_analysis && (
            <span className="analysis-status">🔍 Analyzed</span>
          )}
        </div>
        <div className="news-sentiment-info">
          {item.has_analysis && item.sentiment_data && item.sentiment_data.length > 0 ? (
            <div className="sentiment-badges-container">
              {item.sentiment_data.map((sentimentItem, index) => (
                <div key={index} className="ticker-sentiment-container">
                  <div className="ticker-sentiment-pair">
                    <span className="ticker-badge">{sentimentItem.ticker}</span>
                    <span className={`sentiment-badge ${getSentimentBadgeClass(sentimentItem.sentiment)}`}>
                      {sentimentItem.sentiment}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="no-sentiment-analysis">
              <span className="sentiment-badge sentiment-no-analysis">
                No Analysis
              </span>
            </div>
          )}
        </div>
        
        {/* Similar Articles Button - shown once per article */}
        {(() => {
          const similarArticlesInfo = getSimilarArticlesData();
          return similarArticlesInfo && (
            <div className="article-similar-articles-section">
              <button 
                className="similar-articles-toggle"
                onClick={() => toggleSimilarArticles(similarArticlesInfo.sentimentId)}
                title="View similar historical articles used for analysis"
                style={{marginTop: '8px', backgroundColor: '#e3f2fd', border: '1px solid #2196f3', color: '#1976d2'}}
              >
                {expandedSimilarArticles[similarArticlesInfo.sentimentId] ? '▼' : '▶'} Similar Articles ({similarArticlesInfo.similarIds.length})
              </button>
              
              {/* Similar Articles Dropdown */}
              {expandedSimilarArticles[similarArticlesInfo.sentimentId] && (
                <div className="similar-articles-dropdown">
                  {loadingSimilarArticles[similarArticlesInfo.sentimentId] ? (
                    <div className="loading-similar">Loading similar articles...</div>
                  ) : similarArticlesData[similarArticlesInfo.sentimentId] && similarArticlesData[similarArticlesInfo.sentimentId].length > 0 ? (
                    <div className="similar-articles-list">
                      <h4>Historical Context Used for Analysis:</h4>
                      {similarArticlesData[similarArticlesInfo.sentimentId].map((article, articleIndex) => (
                        <div key={articleIndex} className="similar-article-item">
                          <div className="similar-article-header">
                            <span className="similar-article-date">
                              {new Date(article.date_publish).toLocaleDateString()}
                            </span>
                            {article.similarity_score && (
                              <span className="similarity-score">
                                Similarity: {(article.similarity_score * 100).toFixed(1)}%
                              </span>
                            )}
                          </div>
                          <h5 className="similar-article-title">{article.title}</h5>
                          <p className="similar-article-description">
                            {article.description.length > 150 
                              ? `${article.description.substring(0, 150)}...`
                              : article.description
                            }
                          </p>
                          {article.ticker_metadata && Object.keys(article.ticker_metadata).length > 0 && (
                            <div className="historical-price-changes">
                              <strong>Historical Price Impact:</strong>
                              <div className="price-changes">
                                {Object.entries(article.ticker_metadata).map(([ticker, change]) => (
                                  <span key={ticker} className={`price-change ${change > 0 ? 'positive' : change < 0 ? 'negative' : 'neutral'}`}>
                                    {ticker}: {change > 0 ? '+' : ''}{change.toFixed(2)}%
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="no-similar-articles">No similar historical articles found.</div>
                  )}
                </div>
              )}
            </div>
          );
        })()}
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
      
      {item.has_analysis && item.extra_data && Object.keys(item.extra_data).length > 0 && (
        <div className="analysis-details">
          <details>
            <summary>Analysis Details</summary>
            <pre>{JSON.stringify(item.extra_data, null, 2)}</pre>
          </details>
        </div>
      )}
      
      <div className="news-footer">
        {item.url && (
          <a 
            href={item.url} 
            target="_blank" 
            rel="noopener noreferrer" 
            className="news-link"
          >
            Read Full Article →
          </a>
        )}
      </div>
    </div>
  );
};

export default Day; 