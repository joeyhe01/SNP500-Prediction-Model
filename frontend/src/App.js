import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Main from './components/Main';
import Simulation from './components/Simulation';
import Day from './components/Day';
import RealtimePredictionDetail from './components/RealtimePredictionDetail';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<Main />} />
          <Route path="/simulation/:simulationId" element={<Simulation />} />
          <Route path="/simulation/:simulationId/day/:date" element={<Day />} />
          <Route path="/realtime/prediction/:predictionId" element={<RealtimePredictionDetail />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App; 