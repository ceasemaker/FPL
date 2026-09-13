"""Guards for the MILP squad optimiser.

The solver defines its squad composition on the labels ``GK/DEF/MID/FWD`` while
callers (including this project's own API views and the FPL API itself) use
``GKP`` for goalkeepers. When that mismatch went unnoticed the goalkeeper
constraint matched no players and every solve came back infeasible, so these
tests pin the normalisation and an end-to-end feasible solve.
"""

from __future__ import annotations

import unittest

import pandas as pd
from django.test import SimpleTestCase

try:
    from ..fpl_solver.solver import FPLSolver, normalize_position
except ImportError:  # pragma: no cover - optional optimizer dependency
    FPLSolver = None
    normalize_position = None


@unittest.skipIf(FPLSolver is None, "pulp is not installed")
class PositionNormalizationTests(SimpleTestCase):
    def test_goalkeeper_aliases_map_to_the_composition_key(self) -> None:
        for alias in ("GKP", "gkp", " Goalkeeper ", "G"):
            self.assertEqual(normalize_position(alias), "GK")

    def test_outfield_aliases(self) -> None:
        self.assertEqual(normalize_position("Defender"), "DEF")
        self.assertEqual(normalize_position("MID"), "MID")
        self.assertEqual(normalize_position("forward"), "FWD")

    def test_unknown_and_non_string_values_pass_through(self) -> None:
        self.assertEqual(normalize_position("MNG"), "MNG")
        self.assertIsNone(normalize_position(None))


def _squad_pool() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """A pool large enough to build a legal squad, labelled the FPL way."""
    rows = []
    element = 1
    # Four clubs keeps the three-per-club limit satisfiable.
    for position, count, price in (("GKP", 6, 45), ("DEF", 12, 45), ("MID", 12, 50), ("FWD", 8, 55)):
        for index in range(count):
            rows.append(
                {
                    "element": element,
                    "event": 3,
                    "position": position,
                    "value": price,
                    "name": f"{position}{index}",
                    "team": index % 6,
                }
            )
            element += 1

    gw_data = pd.DataFrame(
        [{k: row[k] for k in ("element", "event", "position", "value", "name")} for row in rows]
    )
    normalized = pd.DataFrame(
        [{"element": row["element"], "event": 3, "player_team_id": row["team"]} for row in rows]
    )
    predictions = pd.DataFrame(
        [
            {
                "element": row["element"],
                "event": 4,
                "predicted_points": 3.0 + (row["element"] % 5),
                "name": row["name"],
                "position": row["position"],
                "predicted_variance": 4.0,
                "effective_ownership": 0.05,
            }
            for row in rows
        ]
    )
    return predictions, gw_data, normalized


@unittest.skipIf(FPLSolver is None, "pulp is not installed")
class SolverFeasibilityTests(SimpleTestCase):
    def test_open_pool_solve_returns_a_legal_squad(self) -> None:
        predictions, gw_data, normalized = _squad_pool()
        solver = FPLSolver(planning_horizon=1, budget=1000, start_gw=4)
        solver.load_predictions(predictions)
        solver.load_player_data(gw_data, normalized)
        solver.build_model()

        self.assertTrue(solver.solve(time_limit=30), "solver should find a feasible squad")

        solution = solver.extract_solution()
        # Solution dicts are keyed by the solver's internal 1..T index, not by
        # the real gameweek number.
        squad = solution["squads"][1]
        lineup = solution["lineups"][1]
        self.assertEqual(len(squad), 15)
        self.assertEqual(len(lineup["starters"]), 11)
        self.assertEqual(len(lineup["bench"]), 4)

        positions = solver.players.set_index("element")["position"]
        counts = positions.loc[squad].value_counts().to_dict()
        self.assertEqual(counts.get("GK"), 2)
        self.assertEqual(counts.get("DEF"), 5)
        self.assertEqual(counts.get("MID"), 5)
        self.assertEqual(counts.get("FWD"), 3)

        prices = solver.players.set_index("element")["value"]
        self.assertLessEqual(prices.loc[squad].sum(), 1000)
