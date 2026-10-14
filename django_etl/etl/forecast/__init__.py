"""Next-gameweek points forecast, trained on every season we hold.

* ``data``: loads the season-keyed history tables into pandas.
* ``features``: deadline-safe features (only weeks before the target week).
* ``model``: the gradient-boosted points model.
* ``selection``: captain and starting-XI choices, with FPL's autosub rules.
* ``backtest``: walk-forward evaluation against fixed baselines, and the gate
  that decides whether picks may be shown.
"""

VERSION = "v2.0"
