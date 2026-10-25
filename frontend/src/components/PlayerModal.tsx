import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

// Players open on their own page now (/players/:id), the same wherever they
// are clicked. This keeps the old modal call sites working: it hands over to
// the page instead of drawing a modal.
export function PlayerModal({ playerId, onClose }: { playerId: number; onClose: () => void }) {
  const navigate = useNavigate();
  useEffect(() => {
    navigate(`/players/${playerId}`);
    onClose();
  }, [playerId]); // eslint-disable-line react-hooks/exhaustive-deps
  return null;
}
