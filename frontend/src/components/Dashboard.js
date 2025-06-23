import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { format, parseISO } from 'date-fns';
import './Dashboard.css';

const Dashboard = () => {
  const [simulations, setSimulations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.get('/api/simulations');
      setSimulations(response.data);
    } catch (err) {
      setError(`Error loading data: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const deleteSimulation = async (simulationId) => {
    const simulation = simulations.find(s => s.id === simulationId);
    const confirmMessage = `Are you sure you want to delete Simulation ${simulationId}?\n\nThis will permanently delete:\n- The simulation record\n- All daily trading data\n- All news sentiment analysis\n\nThis action cannot be undone.`;
    
    if (!window.confirm(confirmMessage)) {
      return;
    }

    setDeletingId(simulationId);

    try {
      const response = await axios.delete(`/api/simulation/${simulationId}`);
      
      if (response.data.success) {
        // Remove the deleted simulation from state
        setSimulations(prev => prev.filter(sim => sim.id !== simulationId));
        
        // Show success message
        alert(`Simulation ${simulationId} deleted successfully!\n\nDeleted:\n- ${response.data.deleted_records.news_sentiments} news sentiment records\n- ${response.data.deleted_records.daily_recaps} daily recap records\n- ${response.data.deleted_records.simulation} simulation record`);
      }
    } catch (err) {
      setError(`Error deleting simulation: ${err.response?.data?.error || err.message}`);
      alert(`Failed to delete simulation: ${err.response?.data?.error || err.message}`);
    } finally {
      setDeletingId(null);
    }
  };

  if (loading) {
    return (
      <div className="dashboard-content">
        <div className="loading">Loading simulation data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-content">
        <div className="error">{error}</div>
      </div>
    );
  }

  if (simulations.length === 0) {
    return (
      <div className="dashboard-content">
        <div className="no-data">
          <h3>No Simulation Data Found</h3>
          <p>Run some simulations to see performance analysis here.</p>
          <button className="btn" onClick={loadData}>Refresh</button>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-content">
      <div className="simulations-list">
        {simulations.map(simulation => (
          <SimulationRow 
            key={simulation.id} 
            simulation={simulation} 
            onNavigate={() => navigate(`/simulation/${simulation.id}`)}
            onDelete={() => deleteSimulation(simulation.id)}
            isDeleting={deletingId === simulation.id}
          />
        ))}
      </div>
    </div>
  );
};

const SimulationRow = ({ simulation, onNavigate, onDelete, isDeleting }) => {
  const prepareChartData = () => {
    return simulation.dates.map((date, index) => ({
      date,
      cumulativeReturn: simulation.cumulative_returns[index],
      dailyReturn: simulation.daily_returns[index]
    }));
  };

  const formatTooltipValue = (value, name) => {
    if (name === 'cumulativeReturn') {
      return [`${value.toFixed(2)}%`, 'Cumulative Return'];
    }
    if (name === 'dailyReturn') {
      return [`${value.toFixed(2)}%`, 'Daily Return'];
    }
    return [value, name];
  };

  const getReturnClass = (value) => {
    return value > 0 ? 'positive' : value < 0 ? 'negative' : 'neutral';
  };

  const handleDeleteClick = (e) => {
    e.stopPropagation(); // Prevent triggering the row click/navigation
    onDelete();
  };

  const chartData = prepareChartData();
  const returnClass = getReturnClass(simulation.final_return);

  return (
    <div className="simulation-row">
      <div className="simulation-chart" onClick={onNavigate}>
        <div className="simulation-header">
          <div className="simulation-title-section">
            <h3 className="simulation-title">Simulation {simulation.id}</h3>
            <span className="simulation-date">
              {format(parseISO(simulation.executed_at), 'MMM dd, yyyy')}
            </span>
          </div>
          <button 
            className={`delete-btn ${isDeleting ? 'deleting' : ''}`}
            onClick={handleDeleteClick}
            disabled={isDeleting}
            title="Delete this simulation"
          >
            {isDeleting ? '⏳' : '🗑️'}
          </button>
        </div>
        
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis 
              dataKey="date" 
              tickFormatter={(date) => format(parseISO(date), 'MMM dd')}
              stroke="#64748b"
              fontSize={12}
            />
            <YAxis 
              stroke="#64748b"
              tickFormatter={(value) => `${value}%`}
              fontSize={12}
            />
            <Tooltip 
              formatter={formatTooltipValue}
              labelFormatter={(date) => format(parseISO(date), 'MMM dd, yyyy')}
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
              }}
            />
            <Line
              type="monotone"
              dataKey="cumulativeReturn"
              stroke={simulation.final_return >= 0 ? '#059669' : '#dc2626'}
              strokeWidth={2}
              dot={false}
              name="Cumulative Return"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      
      <div className="simulation-data" onClick={onNavigate}>
        <div className="data-grid">
          <div className="data-item">
            <span className="data-label">Total Return</span>
            <span className={`data-value ${returnClass}`}>
              {simulation.final_return > 0 ? '+' : ''}{simulation.final_return.toFixed(2)}%
            </span>
          </div>
          
          <div className="data-item">
            <span className="data-label">Trading Days</span>
            <span className="data-value">
              {simulation.dates.length}
            </span>
          </div>
          
          <div className="data-item">
            <span className="data-label">Total Trades</span>
            <span className="data-value">
              {simulation.total_trades}
            </span>
          </div>
          
          <div className="data-item">
            <span className="data-label">Sharpe Ratio</span>
            <span className="data-value">
              {simulation.sharpe_ratio.toFixed(2)}
            </span>
          </div>
          
          <div className="data-item">
            <span className="data-label">Max Drawdown</span>
            <span className="data-value negative">
              {simulation.max_drawdown.toFixed(2)}%
            </span>
          </div>
          
          <div className="data-item">
            <span className="data-label">Win Rate</span>
            <span className="data-value">
              {simulation.win_rate ? simulation.win_rate.toFixed(1) : '0.0'}%
            </span>
          </div>
        </div>
        
        <div className="click-hint">
          <span>Click to view detailed analysis →</span>
        </div>
      </div>
    </div>
  );
};

export default Dashboard; 