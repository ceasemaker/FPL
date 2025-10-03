import { useEffect, useRef } from "react";
import anime from "animejs";
import type { PlayerMover } from "../types";

interface TransfersTickerProps {
  transfersIn: PlayerMover[] | undefined;
  transfersOut: PlayerMover[] | undefined;
  loading: boolean;
}

export function TransfersTicker({
  transfersIn,
  transfersOut,
  loading,
}: TransfersTickerProps) {
  const inStripRef = useRef<HTMLDivElement>(null);
  const outStripRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (loading || !transfersIn?.length) return;
    const inStrip = inStripRef.current;
    if (!inStrip) return;

    anime({
      targets: inStrip,
      translateX: [0, -inStrip.scrollWidth / 2],
      duration: 31250,
      easing: "linear",
      loop: true,
    });
  }, [transfersIn, loading]);

  useEffect(() => {
    if (loading || !transfersOut?.length) return;
    const outStrip = outStripRef.current;
    if (!outStrip) return;

    anime({
      targets: outStrip,
      translateX: [0, -outStrip.scrollWidth / 2],
      duration: 31250,
      easing: "linear",
      loop: true,
    });
  }, [transfersOut, loading]);

  if (loading) {
    return (
      <section className="ticker">
        <h3 className="section-subtitle">Loading transfers...</h3>
      </section>
    );
  }

  const allTransfersIn = transfersIn ? [...transfersIn, ...transfersIn] : [];
  const allTransfersOut = transfersOut ? [...transfersOut, ...transfersOut] : [];

  return (
    <section className="transfers-section">
      <div className="transfers-row">
        <h3 className="section-subtitle">Most Transferred In</h3>
        <div className="ticker-viewport">
          <div className="ticker-strip" ref={inStripRef}>
            {allTransfersIn.map((player, idx) => {
              const initials =
                player.first_name && player.second_name
                  ? `${player.first_name[0]}${player.second_name[0]}`
                  : "??";
              return (
                <div key={`in-${player.id}-${idx}`} className="ticker-card in">
                  <div className="ticker-avatar">
                    {player.image_url ? (
                      <img src={player.image_url} alt={player.second_name} />
                    ) : (
                      initials
                    )}
                  </div>
                  <div className="ticker-body">
                    <div className="ticker-name">
                      {player.first_name} {player.second_name}
                    </div>
                    <div className="ticker-meta">
                      <span>{player.team || "FA"}</span>
                      <span>•</span>
                      <span>£{((player.now_cost ?? 0) / 10).toFixed(1)}m</span>
                    </div>
                  </div>
                  <div className="ticker-badge">
                    +{player.value.toLocaleString()}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="transfers-row">
        <h3 className="section-subtitle">Most Transferred Out</h3>
        <div className="ticker-viewport">
          <div className="ticker-strip" ref={outStripRef}>
            {allTransfersOut.map((player, idx) => {
              const initials =
                player.first_name && player.second_name
                  ? `${player.first_name[0]}${player.second_name[0]}`
                  : "??";
              return (
                <div key={`out-${player.id}-${idx}`} className="ticker-card out">
                  <div className="ticker-avatar">
                    {player.image_url ? (
                      <img src={player.image_url} alt={player.second_name} />
                    ) : (
                      initials
                    )}
                  </div>
                  <div className="ticker-body">
                    <div className="ticker-name">
                      {player.first_name} {player.second_name}
                    </div>
                    <div className="ticker-meta">
                      <span>{player.team || "FA"}</span>
                      <span>•</span>
                      <span>£{((player.now_cost ?? 0) / 10).toFixed(1)}m</span>
                    </div>
                  </div>
                  <div className="ticker-badge">
                    -{player.value.toLocaleString()}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
