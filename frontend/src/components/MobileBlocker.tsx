import { useEffect, useState } from "react";

export function MobileBlocker({ children }: { children: React.ReactNode }) {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkDevice = () => {
      // Check screen width (anything under 1024px is considered mobile/tablet)
      const isMobileWidth = window.innerWidth < 1024;
      
      // Check user agent for mobile devices
      const isMobileDevice = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
        navigator.userAgent
      );
      
      setIsMobile(isMobileWidth || isMobileDevice);
    };

    // Check on mount
    checkDevice();

    // Check on resize
    window.addEventListener("resize", checkDevice);
    
    return () => {
      window.removeEventListener("resize", checkDevice);
    };
  }, []);

  if (isMobile) {
    return (
      <div className="mobile-blocker">
        <div className="mobile-blocker-content">
          <div className="mobile-blocker-icon">🖥️</div>
          <h1>Thank You for Your Interest!</h1>
          <p className="blocker-description">
            We're excited to have you explore AeroFPL
          </p>
          <div className="mobile-blocker-message">
            <p>
              To provide you with the best experience and full functionality,
              we recommend accessing this platform on a desktop or laptop computer.
            </p>
            <p>
              Our interface is optimized for larger screens, ensuring you can
              take full advantage of all the analytics, visualizations, and
              interactive features.
            </p>
          </div>
          <div className="mobile-blocker-footer">
            <p>✨ See you on desktop! ✨</p>
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
