import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { parseTimestamp, formatTimestampWithTimezone, formatTimestamp } from '../utils/timeUtils';
import './Day.css';

const RealtimePredictionDetail = () => {
  const { predictionId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all'); // 'all', 'analyzed', 'not-analyzed'
  const [tickerFilter, setTickerFilter] = useState(''); // Filter by specific ticker
  const [sentimentFilter, setSentimentFilter] = useState(''); // Filter by sentiment
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  
  // New state for efficient ticker sentiment summary
  const [tickerSummary, setTickerSummary] = useState(null);
  const [tickerSummaryLoading, setTickerSummaryLoading] = useState(true);
  const [tickerSummaryError, setTickerSummaryError] = useState(null);
  
  // State for similar articles functionality
  const [expandedSimilarArticles, setExpandedSimilarArticles] = useState({});
  const [similarArticlesData, setSimilarArticlesData] = useState({});
  const [loadingSimilarArticles, setLoadingSimilarArticles] = useState({});

  useEffect(() => {
    loadPredictionDetails();
  }, [predictionId, currentPage, pageSize, filter, tickerFilter, sentimentFilter]); // Add all filter dependencies

  useEffect(() => {
    loadTickerSentimentSummary();
  }, [predictionId]); // Only reload ticker summary when prediction ID changes

  const loadPredictionDetails = async () => {
    console.log('loadPredictionDetails called with:', { 
      predictionId, 
      currentPage, 
      pageSize, 
      filter,
      tickerFilter,
      sentimentFilter
    }); // Debug log
    
    setLoading(true);
    setError(null);
    
    try {
      const params = {
        page: currentPage,
        page_size: pageSize,
        filter: filter
      };
      
      // Only add ticker and sentiment filters if they're not empty
      if (tickerFilter) {
        params.ticker = tickerFilter;
      }
      if (sentimentFilter) {
        params.sentiment = sentimentFilter;
      }
      
      const response = await axios.get(`/api/realtime/prediction/${predictionId}`, {
        params: params
      });
      setData(response.data);
      console.log('Prediction data loaded successfully'); // Debug log
    } catch (err) {
      console.error('Error loading prediction details:', err); // Debug log
      setError(`Error loading prediction details: ${err.response?.data?.error || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadTickerSentimentSummary = async () => {
    setTickerSummaryLoading(true);
    setTickerSummaryError(null);
    
    try {
      const response = await axios.get(`/api/realtime/prediction/${predictionId}/ticker-sentiment-summary`);
      setTickerSummary(response.data);
      console.log('Ticker sentiment summary:', response.data); // Debug log
    } catch (err) {
      setTickerSummaryError(`Error loading ticker sentiment: ${err.response?.data?.error || err.message}`);
    } finally {
      setTickerSummaryLoading(false);
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

  // Articles are now filtered server-side, so we can use them directly
  const filteredArticles = data?.news_analysis || [];

  const handlePageChange = (newPage) => {
    // Save scroll position for page changes too
    savedScrollPositionRef.current = window.scrollY;
    shouldPreserveScrollRef.current = true;
    
    setCurrentPage(newPage);
  };

  const handlePageSizeChange = (newPageSize) => {
    // Save scroll position for page size changes too
    savedScrollPositionRef.current = window.scrollY;
    shouldPreserveScrollRef.current = true;
    
    setPageSize(newPageSize);
    setCurrentPage(1); // Reset to first page when changing page size
  };

  // Track if we should preserve scroll position (for filter changes, not page changes)
  const shouldPreserveScrollRef = useRef(false);
  const savedScrollPositionRef = useRef(0);

  // Effect to restore scroll position after filter changes
  useEffect(() => {
    if (shouldPreserveScrollRef.current) {
      // Restore the saved scroll position
      requestAnimationFrame(() => {
        window.scrollTo(0, savedScrollPositionRef.current);
        shouldPreserveScrollRef.current = false; // Reset the flag
      });
    }
  }, [data]); // Trigger when data changes (after filter is applied)

  // Optimized filter handlers to prevent page refresh and unwanted scrolling
  const handleFilterChange = useCallback((newFilter, event) => {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    
    console.log('Filter changing to:', newFilter); // Debug log
    
    // Batch state updates without scrolling
    if (newFilter !== filter) {
      // Save current scroll position and set flag to preserve it
      savedScrollPositionRef.current = window.scrollY;
      shouldPreserveScrollRef.current = true;
      
      setFilter(newFilter);
      setCurrentPage(1); // Reset to page 1 but preserve scroll position
    }
  }, [filter]);

  const handleFilterAll = useCallback((event) => {
    handleFilterChange('all', event);
  }, [handleFilterChange]);

  const handleFilterAnalyzed = useCallback((event) => {
    handleFilterChange('analyzed', event);
  }, [handleFilterChange]);

  const handleFilterNotAnalyzed = useCallback((event) => {
    handleFilterChange('not-analyzed', event);
  }, [handleFilterChange]);

  // Handlers for ticker and sentiment filters
  const handleTickerFilterChange = useCallback((event) => {
    const newTickerFilter = event.target.value;
    console.log('Ticker filter changing to:', newTickerFilter); // Debug log
    
    // Save current scroll position and set flag to preserve it
    savedScrollPositionRef.current = window.scrollY;
    shouldPreserveScrollRef.current = true;
    
    setTickerFilter(newTickerFilter);
    setCurrentPage(1); // Reset to page 1 but preserve scroll position
  }, []);

  const handleSentimentFilterChange = useCallback((event) => {
    const newSentimentFilter = event.target.value;
    console.log('Sentiment filter changing to:', newSentimentFilter); // Debug log
    
    // Save current scroll position and set flag to preserve it
    savedScrollPositionRef.current = window.scrollY;
    shouldPreserveScrollRef.current = true;
    
    setSentimentFilter(newSentimentFilter);
    setCurrentPage(1); // Reset to page 1 but preserve scroll position
  }, []);

  const clearAllFilters = useCallback(() => {
    console.log('Clearing all filters'); // Debug log
    
    // Save current scroll position and set flag to preserve it
    savedScrollPositionRef.current = window.scrollY;
    shouldPreserveScrollRef.current = true;
    
    setFilter('all');
    setTickerFilter('');
    setSentimentFilter('');
    setCurrentPage(1);
  }, []);

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
          <button type="button" className="btn" onClick={() => navigate('/')}>Back to Dashboard</button>
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
        <button type="button" className="btn" onClick={() => navigate('/')}>
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
                {formatTimestampWithTimezone(data.timestamp)}
              </span>
            </div>
            <div className="summary-item">
              <span className="summary-label">News Time Range:</span>
              <span className="summary-value">
                {formatTimestamp(data.time_range.start)} - {formatTimestamp(data.time_range.end)}
                {data.time_range_info && data.time_range_info.is_custom && (
                  <span className="range-type-indicator"> (Custom Range)</span>
                )}
                {data.time_range_info && !data.time_range_info.is_custom && (
                  <span className="range-type-indicator"> (Default Range)</span>
                )}
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
            <div className={`sentiment-display ${getSentimentClass(data.market_sentiment_score || 0)}`}>
              <span className="sentiment-score">{(data.market_sentiment_score || 0).toFixed(3)}</span>
              <span className="sentiment-label">{getSentimentLabel(data.market_sentiment_score || 0)}</span>
            </div>
          </div>



          {/* Efficient Ticker Sentiment Summary */}
          <div className="ticker-summary-section">
            <h3>Ticker Sentiment Summary (From Stored Prediction Data)</h3>
            
            {tickerSummaryLoading && (
              <div className="ticker-summary-loading">
                <div className="loading">Loading ticker sentiment analysis...</div>
              </div>
            )}
            
            {tickerSummaryError && (
              <div className="ticker-summary-error">
                <div className="error">{tickerSummaryError}</div>
                <button 
                  type="button"
                  className="retry-btn"
                  onClick={loadTickerSentimentSummary}
                >
                  Retry
                </button>
              </div>
            )}
            
            {!tickerSummaryLoading && !tickerSummaryError && tickerSummary && (
              <div>
                {tickerSummary.ticker_sentiment_summary && tickerSummary.ticker_sentiment_summary.length > 0 ? (
                  <div className="ticker-summary-grid">
                    {tickerSummary.ticker_sentiment_summary.map((tickerData) => (
                      <div key={tickerData.ticker} className="ticker-summary-item">
                        <div className="ticker-header">
                          <div className="ticker-name">{tickerData.ticker}</div>
                          <div className={`sentiment-score ${getSentimentClass(tickerData.sentiment_score)}`}>
                            {tickerData.sentiment_score > 0 ? '+' : ''}{tickerData.sentiment_score}
                          </div>
                        </div>
                        <div className="sentiment-counts">
                          <span className="positive-count">✅ {tickerData.positive}</span>
                          <span className="negative-count">❌ {tickerData.negative}</span>
                          <span className="neutral-count">⚪ {tickerData.neutral}</span>
                          <span className="total-count">📊 {tickerData.total}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="no-ticker-data">
                    No ticker sentiment data found for this prediction.
                  </div>
                )}
              </div>
            )}
          </div>

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
                            <span className="signal-score">Net: {signal.net_sentiment > 0 ? '+' : ''}{signal.net_sentiment}</span>
                            <span className="signal-breakdown">({signal.positive_count}+ / {signal.negative_count}-)</span>
                            <span className="signal-articles">{signal.total_articles} articles</span>
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
                            <span className="signal-score">Net: {signal.net_sentiment > 0 ? '+' : ''}{signal.net_sentiment}</span>
                            <span className="signal-breakdown">({signal.positive_count}+ / {signal.negative_count}-)</span>
                            <span className="signal-articles">{signal.total_articles} articles</span>
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
          <h2>News Analysis</h2>
          
          {/* Overall Summary */}
          <div className="news-summary-stats">
            <div className="summary-stat-item">
              <span className="summary-stat-label">Total Articles:</span>
              <span className="summary-stat-value">{data.total_articles}</span>
            </div>
            <div className="summary-stat-item">
              <span className="summary-stat-label">Total Analyzed:</span>
              <span className="summary-stat-value">{data.total_analyzed}</span>
            </div>
            <div className="summary-stat-item">
              <span className="summary-stat-label">Total Not Analyzed:</span>
              <span className="summary-stat-value">{data.total_not_analyzed}</span>
            </div>
            <div className="summary-stat-item">
              <span className="summary-stat-label">Analysis Filter:</span>
              <span className="summary-stat-value">
                {filter === 'all' ? 'All Articles' : 
                 filter === 'analyzed' ? 'Analyzed Only' : 'Not Analyzed Only'}
              </span>
            </div>
            {tickerFilter && (
              <div className="summary-stat-item">
                <span className="summary-stat-label">Ticker Filter:</span>
                <span className="summary-stat-value">{tickerFilter}</span>
              </div>
            )}
            {sentimentFilter && (
              <div className="summary-stat-item">
                <span className="summary-stat-label">Sentiment Filter:</span>
                <span className="summary-stat-value">{sentimentFilter}</span>
              </div>
            )}
            <div className="summary-stat-item">
              <span className="summary-stat-label">Filtered Results:</span>
              <span className="summary-stat-value">{data.filtered_total_count}</span>
            </div>
            <div className="summary-stat-item">
              <span className="summary-stat-label">Current Page:</span>
              <span className="summary-stat-value">{data.pagination?.page} of {data.pagination?.total_pages}</span>
            </div>
          </div>
          
          {/* Pagination and filter controls */}
          <div className="news-controls">
            {/* Analysis Filter buttons */}
            <div className="filter-section">
              <div className="filter-group">
                <label className="filter-label">Analysis Status:</label>
                <div className="filter-buttons">
                  <button 
                    type="button"
                    className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
                    onClick={handleFilterAll}
                  >
                    All Articles ({data.total_articles})
                  </button>
                  <button 
                    type="button"
                    className={`filter-btn ${filter === 'analyzed' ? 'active' : ''}`}
                    onClick={handleFilterAnalyzed}
                  >
                    Analyzed ({data.total_analyzed})
                  </button>
                  <button 
                    type="button"
                    className={`filter-btn ${filter === 'not-analyzed' ? 'active' : ''}`}
                    onClick={handleFilterNotAnalyzed}
                  >
                    Not Analyzed ({data.total_not_analyzed})
                  </button>
                </div>
              </div>

              {/* Ticker and Sentiment Filter dropdowns */}
              <div className="filter-group">
                <label className="filter-label">Content Filters:</label>
                <div className="dropdown-filters">
                  <div className="filter-dropdown">
                    <label htmlFor="tickerFilter">Ticker:</label>
                    <select 
                      id="tickerFilter"
                      value={tickerFilter} 
                      onChange={handleTickerFilterChange}
                    >
                      <option value="">All Tickers</option>
                      {data.available_tickers && data.available_tickers.map(ticker => (
                        <option key={ticker} value={ticker}>{ticker}</option>
                      ))}
                    </select>
                  </div>
                  
                  <div className="filter-dropdown">
                    <label htmlFor="sentimentFilter">Sentiment:</label>
                    <select 
                      id="sentimentFilter"
                      value={sentimentFilter} 
                      onChange={handleSentimentFilterChange}
                    >
                      <option value="">All Sentiments</option>
                      {data.available_sentiments && data.available_sentiments.map(sentiment => (
                        <option key={sentiment} value={sentiment}>
                          {sentiment.charAt(0).toUpperCase() + sentiment.slice(1)}
                        </option>
                      ))}
                    </select>
                  </div>
                  
                  {(tickerFilter || sentimentFilter) && (
                    <button 
                      type="button"
                      className="clear-filters-btn"
                      onClick={clearAllFilters}
                      title="Clear all filters"
                    >
                      Clear Filters
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Pagination info and controls */}
            {data.pagination && (
              <div className="pagination-section">
                <div className="pagination-info">
                  <span className="page-info">
                    Page {data.pagination.page} of {data.pagination.total_pages} 
                    ({data.current_page_articles} of {data.pagination.total_articles} articles)
                  </span>
                  <div className="page-size-selector">
                    <label htmlFor="pageSize">Articles per page:</label>
                    <select 
                      id="pageSize"
                      value={pageSize} 
                      onChange={(e) => handlePageSizeChange(parseInt(e.target.value))}
                    >
                      <option value={25}>25</option>
                      <option value={50}>50</option>
                      <option value={100}>100</option>
                      <option value={200}>200</option>
                    </select>
                  </div>
                </div>
                
                <div className="pagination-controls">
                  <button 
                    type="button"
                    className="pagination-btn"
                    onClick={() => handlePageChange(1)}
                    disabled={!data.pagination.has_prev}
                  >
                    First
                  </button>
                  <button 
                    type="button"
                    className="pagination-btn"
                    onClick={() => handlePageChange(data.pagination.prev_page)}
                    disabled={!data.pagination.has_prev}
                  >
                    Previous
                  </button>
                  
                  {/* Page numbers */}
                  <div className="page-numbers">
                    {Array.from({length: Math.min(5, data.pagination.total_pages)}, (_, i) => {
                      let pageNum;
                      if (data.pagination.total_pages <= 5) {
                        pageNum = i + 1;
                      } else {
                        const current = data.pagination.page;
                        const total = data.pagination.total_pages;
                        if (current <= 3) {
                          pageNum = i + 1;
                        } else if (current >= total - 2) {
                          pageNum = total - 4 + i;
                        } else {
                          pageNum = current - 2 + i;
                        }
                      }
                      
                      return (
                        <button
                          key={pageNum}
                          type="button"
                          className={`page-number ${pageNum === data.pagination.page ? 'active' : ''}`}
                          onClick={() => handlePageChange(pageNum)}
                        >
                          {pageNum}
                        </button>
                      );
                    })}
                  </div>
                  
                  <button 
                    type="button"
                    className="pagination-btn"
                    onClick={() => handlePageChange(data.pagination.next_page)}
                    disabled={!data.pagination.has_next}
                  >
                    Next
                  </button>
                  <button 
                    type="button"
                    className="pagination-btn"
                    onClick={() => handlePageChange(data.pagination.total_pages)}
                    disabled={!data.pagination.has_next}
                  >
                    Last
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="news-list">
            {filteredArticles.length > 0 ? (
              filteredArticles.map(article => (
                <NewsItem 
                  key={article.headline_id} 
                  item={article}
                  expandedSimilarArticles={expandedSimilarArticles}
                  toggleSimilarArticles={toggleSimilarArticles}
                  loadingSimilarArticles={loadingSimilarArticles}
                  similarArticlesData={similarArticlesData}
                />
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

  const getSentimentDisplayText = (sentiment, hasAnalysis) => {
    if (!hasAnalysis) return 'No Analysis';
    return sentiment || 'Neutral';
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

  const similarArticlesInfo = getSimilarArticlesData();

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
            <span className="analysis-status">🔍 Used for Prediction</span>
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
        {similarArticlesInfo && (
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
        )}
      </div>
      
      <h3 className="news-title">{item.title}</h3>
      
      {item.summary && (
        <div className="news-summary">
          <p>{expanded ? item.summary : `${item.summary.substring(0, 200)}...`}</p>
          {item.summary.length > 200 && (
            <button 
              type="button"
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