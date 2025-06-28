import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { format } from 'date-fns';
import { useNavigate } from 'react-router-dom';
import { parseTimestamp, formatTimestampWithTimezone, getTimezoneInfo, debugTimestamp } from '../utils/timeUtils';
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
  const [useCustomRange, setUseCustomRange] = useState(false);
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    loadLatestPrediction();
    loadStatus();
    loadDataStatus();
    loadRecentPredictions();
    setDefaultTimeRange();
  }, []);

  const setDefaultTimeRange = () => {
    try {
      const now = new Date();
      const currentTime = now.getHours();
      
      let endTime, startTime;
      
      // If it's before 9 AM today, get from yesterday 5PM to now
      if (currentTime < 9) {
        endTime = now;
        startTime = new Date(now);
        startTime.setDate(startTime.getDate() - 1);
        startTime.setHours(17, 0, 0, 0);
      } else {
        // If it's after 9 AM, get from yesterday 5PM to current time
        startTime = new Date(now);
        startTime.setDate(startTime.getDate() - 1);
        startTime.setHours(17, 0, 0, 0);
        endTime = now;
      }
      
      // Skip weekends for start_time
      while (startTime.getDay() === 0 || startTime.getDay() === 6) {
        startTime.setDate(startTime.getDate() - 1);
      }
      
      // Validate dates before formatting
      if (isNaN(startTime.getTime()) || isNaN(endTime.getTime())) {
        console.error('Invalid dates in setDefaultTimeRange');
        return;
      }
      
      // Format for datetime-local input
      setStartTime(startTime.toISOString().slice(0, 16));
      setEndTime(endTime.toISOString().slice(0, 16));
    } catch (error) {
      console.error('Error in setDefaultTimeRange:', error);
    }
  };

  const setPresetRange = (hours) => {
    try {
      const now = new Date();
      const start = new Date(now.getTime() - (hours * 60 * 60 * 1000));
      
      // Validate dates
      if (isNaN(start.getTime()) || isNaN(now.getTime())) {
        console.error('Invalid dates in setPresetRange');
        return;
      }
      
      setStartTime(start.toISOString().slice(0, 16));
      setEndTime(now.toISOString().slice(0, 16));
    } catch (error) {
      console.error('Error in setPresetRange:', error);
    }
  };

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

    // Validate custom time range if enabled
    if (useCustomRange && (!startTime || !endTime)) {
      setError('Please provide both start and end times for custom range');
      setFetchingData(false);
      return;
    }

    if (useCustomRange && new Date(startTime) >= new Date(endTime)) {
      setError('Start time must be before end time');
      setFetchingData(false);
      return;
    }

    try {
      const requestData = useCustomRange ? {
        start_time: new Date(startTime).toISOString(),
        end_time: new Date(endTime).toISOString()
      } : {};

      const response = await axios.post('/api/realtime/fetch-data', requestData);
      
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

    // Validate custom time range if enabled
    if (useCustomRange && (!startTime || !endTime)) {
      setError('Please provide both start and end times for custom range');
      setLoading(false);
      return;
    }

    if (useCustomRange && new Date(startTime) >= new Date(endTime)) {
      setError('Start time must be before end time');
      setLoading(false);
      return;
    }

    try {
      const requestData = useCustomRange ? {
        start_time: new Date(startTime).toISOString(),
        end_time: new Date(endTime).toISOString()
      } : {};

      const response = await axios.post('/api/realtime/generate-prediction', requestData);
      
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
      // Debug logging to identify problem timestamps
      if (timestamp && (typeof timestamp !== 'string' || !timestamp.match(/^\d{4}-\d{2}-\d{2}T/))) {
        debugTimestamp(timestamp, 'formatTime');
      }
      
      const formatted = formatTimestampWithTimezone(timestamp);
      // If our formatting function returns 'Invalid date', fall back to original timestamp
      if (formatted === 'Invalid date') {
        console.warn('formatTime received invalid timestamp:', timestamp);
        return timestamp || 'No date';
      }
      return formatted;
    } catch (error) {
      console.error('formatTime error:', error, 'timestamp:', timestamp);
      return timestamp || 'No date';
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

      {/* Time Range Configuration */}
      <div className="time-range-panel">
        <div className="time-range-header">
          <h3>📅 News Time Range Configuration</h3>
          <label className="custom-range-toggle">
            <input
              type="checkbox"
              checked={useCustomRange}
              onChange={(e) => setUseCustomRange(e.target.checked)}
            />
            Use Custom Time Range
          </label>
        </div>

        {useCustomRange && (
          <div className="time-range-controls">
            <div className="preset-buttons">
              <span className="preset-label">Quick Presets:</span>
              <button 
                className="preset-btn" 
                onClick={() => setPresetRange(24)}
                type="button"
              >
                Last 24h
              </button>
              <button 
                className="preset-btn" 
                onClick={() => setPresetRange(12)}
                type="button"
              >
                Last 12h
              </button>
              <button 
                className="preset-btn" 
                onClick={() => setPresetRange(6)}
                type="button"
              >
                Last 6h
              </button>
              <button 
                className="preset-btn" 
                onClick={() => setDefaultTimeRange}
                type="button"
              >
                Default Range
              </button>
            </div>
            
            <div className="datetime-inputs">
              <div className="datetime-group">
                <label htmlFor="startTime">Start Time:</label>
                <input
                  id="startTime"
                  type="datetime-local"
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                  className="datetime-input"
                />
              </div>
              
              <div className="datetime-group">
                <label htmlFor="endTime">End Time:</label>
                <input
                  id="endTime"
                  type="datetime-local"
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                  className="datetime-input"
                />
              </div>
            </div>

            <div className="time-range-info">
              <span className="info-text">
                {startTime && endTime && (
                  <div className="time-info-details">
                    <div className="local-time">
                      <strong>Local Time:</strong> {startTime && endTime ? `${formatTimestampWithTimezone(startTime)} - ${formatTimestampWithTimezone(endTime)}` : 'Please select valid times'}
                    </div>
                    <div className="utc-time">
                      <strong>UTC Time:</strong> {startTime && endTime ? `${new Date(startTime).toISOString().replace('T', ' ').slice(0, 16)} - ${new Date(endTime).toISOString().replace('T', ' ').slice(0, 16)}` : 'Please select valid times'}
                    </div>
                    <div className="duration">
                      <strong>Duration:</strong> {startTime && endTime ? `${Math.round((new Date(endTime) - new Date(startTime)) / (1000 * 60 * 60))} hours` : 'N/A'}
                    </div>
                    <div className="timezone-info">
                      <strong>Your Timezone:</strong> {getTimezoneInfo().display}
                    </div>
                  </div>
                )}
              </span>
            </div>
          </div>
        )}

        {!useCustomRange && (
          <div className="default-range-info">
            <span className="info-text">
              Using default range: Previous trading day 5PM to current time (or 9AM if after market open)
            </span>
          </div>
        )}

        <div className="timezone-notice">
          <span className="notice-text">
            ℹ️ <strong>Timezone Note:</strong> You enter times in your local timezone, but the system processes them in UTC. 
            The backend logs will show UTC times, which may differ from your input.
          </span>
        </div>
      </div>

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
              <span className="status-value" title={dataStatus.latest_news_time ? `Full timestamp: ${formatTimestampWithTimezone(dataStatus.latest_news_time)}` : 'No data available'}>
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
              <span className="prediction-time" title={`Full timestamp: ${formatTimestampWithTimezone(prediction.timestamp)}`}>
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
                  <span className="summary-time" title={`Full timestamp: ${formatTimestampWithTimezone(pred.timestamp)}`}>{formatTime(pred.timestamp)}</span>
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