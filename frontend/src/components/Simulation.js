import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { format, parseISO } from 'date-fns';
import './Simulation.css';

const Simulation = () => {
  const { simulationId } = useParams();
  const navigate = useNavigate();
  const [simulation, setSimulation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadData();
  }, [simulationId]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.get(`/api/simulation/${simulationId}`);
      setSimulation(response.data);
    } catch (err) {
      setError(`Error loading data: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const prepareChartData = () => {
    if (!simulation?.daily_data) return [];
    
    return simulation.daily_data.map(day => ({
      date: day.date,
      portfolioValue: day.ending_money,
      dailyPnL: day.daily_pnl,
      dailyReturn: day.daily_return
    }));
  };

  const handleChartClick = (data) => {
    if (data && data.activeLabel) {
      navigate(`/simulation/${simulationId}/day/${data.activeLabel}`);
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

  const formatTooltip = (value, name) => {
    if (name === 'portfolioValue') {
      return [formatCurrency(value), 'Portfolio Value'];
    }
    if (name === 'dailyPnL') {
      return [formatCurrency(value), 'Daily P&L'];
    }
    return [value, name];
  };

  if (loading) {
    return (
      <div>
        <div className="header-nav">
          <div className="header-content">
            <h1>Simulation {simulationId}</h1>
            <button className="back-btn" onClick={() => navigate('/')}>
              ← Back to Dashboard
            </button>
          </div>
        </div>
        <div className="container">
          <div className="loading">Loading simulation details...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <div className="header-nav">
          <div className="header-content">
            <h1>Simulation {simulationId}</h1>
            <button className="back-btn" onClick={() => navigate('/')}>
              ← Back to Dashboard
            </button>
          </div>
        </div>
        <div className="container">
          <div className="error">{error}</div>
        </div>
      </div>
    );
  }

  if (!simulation?.daily_data || simulation.daily_data.length === 0) {
    return (
      <div>
        <div className="header-nav">
          <div className="header-content">
            <h1>Simulation {simulationId}</h1>
            <button className="back-btn" onClick={() => navigate('/')}>
              ← Back to Dashboard
            </button>
          </div>
        </div>
        <div className="container">
          <div className="no-data">
            <h3>No Data Found</h3>
            <p>No daily trading data available for this simulation.</p>
          </div>
        </div>
      </div>
    );
  }

  const chartData = prepareChartData();
  const { daily_data, simulation: simInfo } = simulation;
  const firstDay = daily_data[0];
  const lastDay = daily_data[daily_data.length - 1];
  const totalReturn = ((lastDay.ending_money - firstDay.starting_money) / firstDay.starting_money * 100);
  const totalTrades = daily_data.reduce((sum, day) => sum + day.total_trades, 0);
  const extraData = simInfo.extra_data || {};

  return (
    <div>
      <div className="header-nav">
        <div className="header-content">
          <h1>Simulation {simulationId}</h1>
          <button className="back-btn" onClick={() => navigate('/')}>
            ← Back to Dashboard
          </button>
        </div>
      </div>
      
      <div className="container">
        <div className="summary-cards">
          <SummaryCard 
            label="Total Return" 
            value={`${totalReturn > 0 ? '+' : ''}${totalReturn.toFixed(2)}%`}
            className={totalReturn > 0 ? 'positive' : totalReturn < 0 ? 'negative' : 'neutral'}
          />
          <SummaryCard 
            label="Final Portfolio" 
            value={formatCurrency(lastDay.ending_money)}
            className="neutral"
          />
          <SummaryCard 
            label="Total Trades" 
            value={totalTrades.toString()}
            className="neutral"
          />
          <SummaryCard 
            label="Trading Days" 
            value={daily_data.length.toString()}
            className="neutral"
          />
          <SummaryCard 
            label="Sharpe Ratio" 
            value={(extraData.sharpe_ratio || 0).toFixed(2)}
            className="neutral"
          />
          <SummaryCard 
            label="Max Drawdown" 
            value={`${(extraData.max_drawdown_pct || 0).toFixed(2)}%`}
            className="negative"
          />
          <SummaryCard 
            label="Win Rate" 
            value={`${(extraData.win_rate_pct || 0).toFixed(2)}%`}
            className={(extraData.win_rate_pct || 0) > 50 ? 'positive' : (extraData.win_rate_pct || 0) < 50 ? 'negative' : 'neutral'}
          />
        </div>
        
        <div className="chart-container">
          <h2 className="chart-title">Daily P&L and Portfolio Value</h2>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={chartData} onClick={handleChartClick}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis 
                dataKey="date" 
                tickFormatter={(date) => format(parseISO(date), 'MMM dd')}
                stroke="#64748b"
              />
              <YAxis 
                yAxisId="portfolio"
                orientation="left"
                stroke="#667eea"
                tickFormatter={formatCurrency}
              />
              <YAxis 
                yAxisId="pnl"
                orientation="right"
                stroke="#22c55e"
                tickFormatter={formatCurrency}
              />
              <Tooltip 
                formatter={formatTooltip}
                labelFormatter={(date) => format(parseISO(date), 'MMM dd, yyyy')}
                contentStyle={{
                  backgroundColor: 'white',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
                }}
              />
              <Legend />
              <Line
                yAxisId="portfolio"
                type="monotone"
                dataKey="portfolioValue"
                stroke="#667eea"
                strokeWidth={2}
                dot={false}
                name="Portfolio Value"
              />
              <Line
                yAxisId="pnl"
                type="monotone"
                dataKey="dailyPnL"
                stroke="#22c55e"
                strokeWidth={2}
                dot={false}
                name="Daily P&L"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        
        <div className="daily-data">
          <div className="daily-data-header">
            <h2 className="daily-data-title">Daily Trading Details</h2>
          </div>
          
          <div className="day-row day-header">
            <div>Date</div>
            <div>Starting $</div>
            <div>Ending $</div>
            <div>Daily P&L</div>
            <div>Return %</div>
            <div>Trades</div>
            <div>Positions</div>
          </div>
          
          <div className="daily-data-list">
            {daily_data.map(day => (
              <DayRow 
                key={day.date} 
                day={day} 
                onClick={() => navigate(`/simulation/${simulationId}/day/${day.date}`)}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

const SummaryCard = ({ label, value, className }) => (
  <div className="summary-card">
    <div className="summary-label">{label}</div>
    <div className={`summary-value ${className}`}>{value}</div>
  </div>
);

const DayRow = ({ day, onClick }) => {
  const returnClass = day.daily_return > 0 ? 'positive' : 
                     day.daily_return < 0 ? 'negative' : 'neutral';

  const positionsSummary = [];
  if (day.num_long_positions > 0) positionsSummary.push(`${day.num_long_positions} Long`);
  if (day.num_short_positions > 0) positionsSummary.push(`${day.num_short_positions} Short`);

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  return (
    <div className="day-row" onClick={onClick}>
      <div className="day-date">{format(parseISO(day.date), 'MMM dd, yyyy')}</div>
      <div className="day-value">{formatCurrency(day.starting_money)}</div>
      <div className="day-value">{formatCurrency(day.ending_money)}</div>
      <div className={`day-value ${returnClass}`}>
        {day.daily_pnl > 0 ? '+' : ''}{formatCurrency(day.daily_pnl)}
      </div>
      <div className={`day-value ${returnClass}`}>
        {day.daily_return > 0 ? '+' : ''}{day.daily_return}%
      </div>
      <div className="day-value">{day.total_trades}</div>
      <div className="positions-summary">{positionsSummary.join(', ') || 'None'}</div>
    </div>
  );
};

export default Simulation; 