import React, { useEffect, useRef } from 'react';
import anime from 'animejs';

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
  const contentRef = useRef<HTMLDivElement>(null);
  const animationRef = useRef<ReturnType<typeof anime> | null>(null);

  useEffect(() => {
    const ticker = tickerRef.current;
    const content = contentRef.current;
    if (!ticker || !content) return;

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

    const startAnimation = () => {
      animationRef.current?.pause();
      anime.remove(content);
      content.style.transform = 'translateX(0)';

      if (reducedMotion.matches) return;

      const start = ticker.clientWidth;
      const distance = start + content.scrollWidth;
      const pixelsPerSecond = 24;
      animationRef.current = anime({
        targets: content,
        translateX: [start, -content.scrollWidth],
        duration: (distance / pixelsPerSecond) * 1000,
        easing: 'linear',
        loop: true,
      });
    };

    const frame = window.requestAnimationFrame(startAnimation);
    const resizeObserver = new ResizeObserver(startAnimation);
    resizeObserver.observe(ticker);
    resizeObserver.observe(content);
    reducedMotion.addEventListener('change', startAnimation);

    return () => {
      window.cancelAnimationFrame(frame);
      resizeObserver.disconnect();
      reducedMotion.removeEventListener('change', startAnimation);
      animationRef.current?.pause();
      anime.remove(content);
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
      <div
        className="news-ticker"
        ref={tickerRef}
        onMouseEnter={() => animationRef.current?.pause()}
        onMouseLeave={() => animationRef.current?.play()}
      >
        <div className="news-ticker-content" ref={contentRef}>
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
