import React, { useState } from 'react';
import News from './components/News';

function App() {
  const [page, setPage] = useState('news');

  const navigateTo = (pageName) => {
    setPage(pageName);
  };

  return (
    <div className="app">
      <nav>
        <a href="#" onClick={(e) => { e.preventDefault(); navigateTo('news'); }}>News</a>
      </nav>
      
      {page === 'news' && <News />}
    </div>
  );
}

export default App; 