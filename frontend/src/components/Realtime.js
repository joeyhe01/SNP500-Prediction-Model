import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { format, parseISO } from 'date-fns';
import { useNavigate } from 'react-router-dom';
import './Realtime.css';

const Realtime = () => {
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fetchingData, setFetchingData] = useState(false);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState(null);
  const [dataStatus, setDataStatus] = useState(null);
  const [recentPredictions, setRecentPredictions] = useState([]);
  const [fetchMessage, setFetchMessage] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadLatestPrediction();
    loadStatus();
    loadDataStatus();
    loadRecentPredictions();
  }, []);

  const loadLatestPrediction = async () => {
    try {
      const response = await axios.get('/api/realtime/latest-prediction');
      if (response.data.success && response.data.prediction) {
        setPrediction(response.data.prediction);
      }
    } catch (err) {
      console.error('Error loading latest prediction:', err);
    }
  };

  const loadStatus = async () => {
    try {
      const response = await axios.get('/api/realtime/prediction-status');
      if (response.data.success) {
        setStatus(response.data.status);
      }
    } catch (err) {
      console.error('Error loading status:', err);
    }
  };

  const loadDataStatus = async () => {
    try {
      const response = await axios.get('/api/realtime/data-status');
      if (response.data.success) {
        setDataStatus(response.data.data_status);
      }
    } catch (err) {
      console.error('Error loading data status:', err);
    }
  };

  const loadRecentPredictions = async () => {
    try {
      const response = await axios.get('/api/realtime/predictions');
      if (response.data.success) {
        setRecentPredictions(response.data.predictions);
      }
    } catch (err) {
      console.error('Error loading recent predictions:', err);
    }
  };

  const fetchFreshData = async () => {
    setFetchingData(true);
    setError(null);
    setFetchMessage(null);

    try {
      const response = await axios.post('/api/realtime/fetch-data');
      
      if (response.data.success) {
        setFetchMessage(response.data.message);
        // Refresh data status after fetching
        loadDataStatus();
        // Auto-clear the message after 5 seconds
        setTimeout(() => setFetchMessage(null), 5000);
      } else {
        setError(response.data.message || 'Failed to fetch data');
      }
    } catch (err) {
      setError(`Error fetching data: ${err.response?.data?.error || err.message}`);
    } finally {
      setFetchingData(false);
    }
  };

  const generateNewPrediction = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await axios.post('/api/realtime/generate-prediction');
      
      if (response.data.success) {
        setPrediction({
          id: response.data.prediction_id,
          timestamp: response.data.timestamp,
          prediction_data: response.data.signals,
          long_tickers: response.data.signals.long_signals.map(s => s.ticker),
          short_tickers: response.data.signals.short_signals.map(s => s.ticker),
          market_sentiment_score: response.data.signals.market_sentiment
        });
        
        // Refresh other data
        loadStatus();
        loadRecentPredictions();
      } else {
        setError(response.data.message || 'Failed to generate prediction');
      }
    } catch (err) {
      setError(`Error generating prediction: ${err.response?.data?.error || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (timestamp) => {
    try {
      return format(parseISO(timestamp), 'MMM dd, yyyy h:mm a');
    } catch {
      return timestamp;
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

  const navigateToPredictionDetail = (predictionId) => {
    navigate(`/realtime/prediction/${predictionId}`);
  };

  return (
    <div className="realtime-container">
      <div className="realtime-header">
        <div className="header-content">
          <h2>🔴 Realtime Trading Predictions</h2>
          <p>Step 1: Fetch fresh news data → Step 2: Generate AI predictions</p>
        </div>
        <div className="action-buttons">
          <button 
            className={`fetch-btn ${fetchingData ? 'loading' : ''}`}
            onClick={fetchFreshData}
            disabled={fetchingData || loading}
            title="Fetch latest news articles from multiple APIs and store in database"
          >
            {fetchingData ? '⏳ Fetching Data...' : '📥 Fetch Fresh Data'}
          </button>
          <button 
            className={`generate-btn ${loading ? 'loading' : ''}`}
            onClick={generateNewPrediction}
            disabled={loading || fetchingData}
            title="Analyze stored news articles and generate trading predictions"
          >
            {loading ? '⏳ Generating...' : '🚀 Generate Prediction'}
          </button>
        </div>
      </div>

      {error && (
        <div className="error-message">
          <span>❌ {error}</span>
        </div>
      )}

      {fetchMessage && (
        <div className="success-message">
          <span>✅ {fetchMessage}</span>
        </div>
      )}

      {status && (
        <div className="status-panel">
          <div className="status-item">
            <span className="status-label">Last Prediction:</span>
            <span className="status-value">
              {status.latest_prediction_time 
                ? formatTime(status.latest_prediction_time)
                : 'None'
              }
            </span>
          </div>
          <div className="status-item">
            <span className="status-label">Predictions Today:</span>
            <span className="status-value">{status.predictions_today}</span>
          </div>
          <div className="status-item">
            <span className="status-label">Total Predictions:</span>
            <span className="status-value">{status.total_predictions}</span>
          </div>
        </div>
      )}

      {dataStatus && (
        <div className="data-status-panel">
          <h3>📊 News Data Status</h3>
          <div className="data-status-grid">
            <div className="status-item">
              <span className="status-label">Latest News:</span>
              <span className="status-value">
                {dataStatus.latest_news_time 
                  ? formatTime(dataStatus.latest_news_time)
                  : 'No data'
                }
              </span>
            </div>
            <div className="status-item">
              <span className="status-label">Articles Today:</span>
              <span className="status-value">{dataStatus.news_today}</span>
            </div>
            <div className="status-item">
              <span className="status-label">Total Articles:</span>
              <span className="status-value">{dataStatus.total_news.toLocaleString()}</span>
            </div>
            <div className="status-item">
              <span className="status-label">Available for Prediction:</span>
              <span className="status-value">
                {dataStatus.articles_in_prediction_range} articles
              </span>
            </div>
          </div>
          <div className="prediction-range-info">
            <span className="range-label">Prediction Time Range:</span>
            <span className="range-value">
              {formatTime(dataStatus.prediction_time_range.start)} - {formatTime(dataStatus.prediction_time_range.end)}
            </span>
          </div>
        </div>
      )}

      {prediction ? (
        <div className="prediction-panel">
          <div className="prediction-header">
            <h3>Latest Prediction</h3>
            <div className="prediction-actions">
              <span className="prediction-time">
                {formatTime(prediction.timestamp)}
              </span>
              <button 
                className="detail-btn"
                onClick={() => navigateToPredictionDetail(prediction.id)}
                title="View detailed analysis"
              >
                📊 View Details
              </button>
            </div>
          </div>

          <div className="market-sentiment">
            <h4>Market Sentiment</h4>
            <div className={`sentiment-score ${getSentimentClass(prediction.market_sentiment_score)}`}>
              <span className="sentiment-value">
                {prediction.market_sentiment_score?.toFixed(3) || '0.000'}
              </span>
              <span className="sentiment-label">
                {getSentimentLabel(prediction.market_sentiment_score || 0)}
              </span>
            </div>
          </div>

          <div className="trading-signals">
            <div className="signals-grid">
              <div className="signal-section long">
                <h4>🟢 Long Positions</h4>
                {prediction.prediction_data?.long_signals?.length > 0 ? (
                  <div className="signal-list">
                    {prediction.prediction_data.long_signals.map((signal, index) => (
                      <div key={index} className="signal-item">
                        <span className="ticker">{signal.ticker}</span>
                        <div className="signal-details">
                          <span className="score">Net: {signal.net_sentiment > 0 ? '+' : ''}{signal.net_sentiment}</span>
                          <span className="sentiment-breakdown">
                            ({signal.positive_count}+ / {signal.negative_count}-)
                          </span>
                          <span className="articles">{signal.total_articles} articles</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="no-signals">No long signals found</div>
                )}
              </div>

              <div className="signal-section short">
                <h4>🔴 Short Positions</h4>
                {prediction.prediction_data?.short_signals?.length > 0 ? (
                  <div className="signal-list">
                    {prediction.prediction_data.short_signals.map((signal, index) => (
                      <div key={index} className="signal-item">
                        <span className="ticker">{signal.ticker}</span>
                        <div className="signal-details">
                          <span className="score">Net: {signal.net_sentiment > 0 ? '+' : ''}{signal.net_sentiment}</span>
                          <span className="sentiment-breakdown">
                            ({signal.positive_count}+ / {signal.negative_count}-)
                          </span>
                          <span className="articles">{signal.total_articles} articles</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="no-signals">No short signals found</div>
                )}
              </div>
            </div>
          </div>

          {prediction.prediction_data && (
            <div className="prediction-stats">
              <div className="stat-item">
                <span className="stat-label">Articles Analyzed:</span>
                <span className="stat-value">{prediction.prediction_data.total_articles_analyzed}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Unique Tickers:</span>
                <span className="stat-value">{prediction.prediction_data.unique_tickers}</span>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="no-prediction">
          <h3>No Recent Predictions</h3>
          <p>Click "Generate New Prediction" to analyze the latest market news and get trading signals.</p>
        </div>
      )}

      {recentPredictions.length > 0 && (
        <div className="recent-predictions">
          <h3>Recent Predictions</h3>
          <div className="predictions-list">
            {recentPredictions.slice(0, 5).map((pred) => (
              <div 
                key={pred.id} 
                className="prediction-summary clickable"
                onClick={() => navigateToPredictionDetail(pred.id)}
                title="Click to view detailed analysis"
              >
                <div className="summary-header">
                  <span className="summary-time">{formatTime(pred.timestamp)}</span>
                  <span className={`summary-sentiment ${getSentimentClass(pred.market_sentiment_score)}`}>
                    {getSentimentLabel(pred.market_sentiment_score || 0)}
                  </span>
                </div>
                <div className="summary-signals">
                  <span className="summary-longs">
                    Long: {pred.long_tickers?.join(', ') || 'None'}
                  </span>
                  <span className="summary-shorts">
                    Short: {pred.short_tickers?.join(', ') || 'None'}
                  </span>
                </div>
                <div className="click-hint">
                  <span>Click to view detailed analysis →</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Realtime; 