import React, { useEffect, useRef } from 'react';

interface NewsItem {
  id: number;
  first_name: string;
  second_name: string;
  web_name: string;
  team: string | null;
  team_code: number | null;
  news: string;
  news_added: string | null;
  image_url: string | null;
}

interface NewsTickerProps {
  news: NewsItem[];
}

const NewsTicker: React.FC<NewsTickerProps> = ({ news }) => {
  const tickerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!tickerRef.current) return;

    const ticker = tickerRef.current;
    const tickerContent = ticker.querySelector('.news-ticker-content') as HTMLDivElement;
    
    if (!tickerContent) return;

    // Clone the content for seamless loop
    const clone = tickerContent.cloneNode(true) as HTMLDivElement;
    ticker.appendChild(clone);

    // Calculate animation duration based on content width
    const contentWidth = tickerContent.scrollWidth;
    const duration = contentWidth / 50; // 50px per second

    tickerContent.style.animationDuration = `${duration}s`;
    clone.style.animationDuration = `${duration}s`;

    return () => {
      if (ticker.contains(clone)) {
        ticker.removeChild(clone);
      }
    };
  }, [news]);

  if (!news || news.length === 0) {
    return null;
  }

  const formatTimeAgo = (dateString: string | null): string => {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 60) {
      return `${diffMins}m ago`;
    } else if (diffHours < 24) {
      return `${diffHours}h ago`;
    } else if (diffDays < 7) {
      return `${diffDays}d ago`;
    } else {
      return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
    }
  };

  return (
    <div className="news-ticker-wrapper">
      <div className="news-ticker-label">
        <span className="news-icon">📰</span>
        <span>LATEST NEWS</span>
      </div>
      <div className="news-ticker" ref={tickerRef}>
        <div className="news-ticker-content">
          {news.map((item, index) => (
            <div key={`${item.id}-${index}`} className="news-item">
              <div className="news-player-info">
                {item.team_code && (
                  <img
                    src={`https://resources.premierleague.com/premierleague25/badges-alt/${item.team_code}.svg`}
                    alt={item.team || ''}
                    className="news-team-badge"
                  />
                )}
                <span className="news-player-name">{item.web_name}</span>
                {item.team && (
                  <span className="news-team-name">({item.team})</span>
                )}
              </div>
              <span className="news-separator">•</span>
              <span className="news-text">{item.news}</span>
              {item.news_added && (
                <>
                  <span className="news-separator">•</span>
                  <span className="news-time">{formatTimeAgo(item.news_added)}</span>
                </>
              )}
              <span className="news-divider">|</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default NewsTicker;
