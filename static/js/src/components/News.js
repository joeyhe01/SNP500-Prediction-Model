import React, { useState, useEffect } from 'react';

function News() {
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Fetch news when component mounts
    const fetchNews = async () => {
      try {
        setLoading(true);
        const response = await fetch('/api/news');
        
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.status === 'ok') {
          setNews(data.articles);
        } else {
          throw new Error(data.message || 'Failed to fetch news');
        }
      } catch (err) {
        setError(err.message);
        console.error('Error fetching news:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchNews();
  }, []);

  if (loading) {
    return <div className="news-loading">Loading news...</div>;
  }

  if (error) {
    return <div className="news-error">Error: {error}</div>;
  }

  return (
    <div className="news-container">
      <h1>Top Headlines</h1>
      {news.length === 0 ? (
        <p>No news articles available at this time.</p>
      ) : (
        <ul className="news-list">
          {news.map((article, index) => (
            <li key={index} className="news-item">
              {article.urlToImage && (
                <img 
                  src={article.urlToImage} 
                  alt={article.title} 
                  className="news-image"
                />
              )}
              <div className="news-content">
                <h2 className="news-title">
                  <a href={article.url} target="_blank" rel="noopener noreferrer">
                    {article.title}
                  </a>
                </h2>
                <p className="news-source">{article.source.name}</p>
                <p className="news-description">{article.description}</p>
                <p className="news-date">
                  {new Date(article.publishedAt).toLocaleDateString()}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default News; 