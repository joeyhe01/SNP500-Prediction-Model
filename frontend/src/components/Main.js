import React, { useState } from 'react';
import Dashboard from './Dashboard';
import Realtime from './Realtime';
import './Main.css';

const Main = () => {
  const [activeTab, setActiveTab] = useState('simulation');

  return (
    <div>
      <div className="header">
        <h1>S&P 500 Trading Platform</h1>
        <p>Advanced sentiment-driven algorithmic trading analysis</p>
      </div>
      
      <div className="container">
        <div className="tab-container">
          <div className="tabs">
            <button 
              className={`tab ${activeTab === 'simulation' ? 'active' : ''}`}
              onClick={() => setActiveTab('simulation')}
            >
              📊 Historical Simulations
            </button>
            <button 
              className={`tab ${activeTab === 'realtime' ? 'active' : ''}`}
              onClick={() => setActiveTab('realtime')}
            >
              🔴 Realtime Trading
            </button>
          </div>
          
          <div className="tab-content">
            {activeTab === 'simulation' && <Dashboard />}
            {activeTab === 'realtime' && <Realtime />}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Main; 