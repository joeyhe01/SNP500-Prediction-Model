import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import Simulation from './components/Simulation';
import Day from './components/Day';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/simulation/:simulationId" element={<Simulation />} />
          <Route path="/simulation/:simulationId/day/:date" element={<Day />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App; 