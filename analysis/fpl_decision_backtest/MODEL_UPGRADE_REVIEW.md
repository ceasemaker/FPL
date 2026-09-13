# Model review and first upgrade — 6 September 2026

## Scope and baseline

Worktree: `/Users/nyashamutseta/Desktop/personal/FPL-model-upgrade`  
Branch: `codex/model-upgrade-20260906`  
Base commit: `4f6fe51`, plus a copy of the original checkout's tracked working changes and non-ignored untracked files. The original checkout was not edited. No commit, push or deployment was performed.

Reviewed the previous audit, stacked backtest and acceptance gates, structural scoring, live player service, input builder, dashboard integration, and the separate Django ML feature path. This is a targeted mathematical/implementation review, not a complete production audit.

The stacked model's reported mean-accuracy improvement does not validate the live workbench: the latter calculates its own points directly from snapshot inputs and positional priors. Likewise, existing historical backtest scores do not measure this new workbench version. The current optimizer and transfer-horizon acceptance flags remain unchanged.

## Implemented: workbench-v2-state-scoring

In `django_etl/etl/services/player_analysis.py`:

- Saves now earn the expectation of completed groups of three, replacing the doubled linear rate.
- Goalkeepers and defenders receive expected goals-conceded deductions, one per completed group of two.
- Goalkeeper goals score ten points rather than six.
- Defensive contributions award two points times the probability of reaching 10 (DEF) or 12 (MID/FWD), replacing proportional partial credit.
- Nonlinear count scores are evaluated separately for start/substitute minute states and then weighted by their probabilities.
- Return and multiple-return probabilities use those same playing states, including zero returns when absent. They cannot exceed appearance probability.
- Explicit blank gameweeks earn zero points and minutes.
- Start rates are clamped before calculating substitute probabilities, preventing negative substitute probability from inconsistent match counts.
- API metadata identifies the model version; report formulas and limitations describe the new implementation. Historical workbook/report artifacts are not rewritten.

Scoring reference checked on 6 September 2026: [Premier League scoring rules](https://www.premierleague.com/en/news/2174909).

Poisson event counts and the start/substitute minute estimates remain modeling assumptions. Correctly applying a scoring rule does not establish calibration or better out-of-sample selection.

## Validation and impact

Command: `cd django_etl && python manage.py test etl.tests.test_player_analysis etl.tests.test_decision_dashboard` — **19 tests pass**. New cases independently enumerate discrete save/conceded/DC scores and test absence, partial availability, blank gameweeks and inconsistent start counts.

All 1,956 rows from the 4 September snapshot were checked for coherent probability bounds and component totals. Full recalculation took approximately 0.26 seconds locally. The before/after results are in `output/workbench_v2_comparison.json`.

| Player, GW3 | Previous xP | Revised xP |
|---|---:|---:|
| Haaland | 5.9179 | 5.3525 |
| B. Fernandes | 5.1616 | 4.2598 |

These are changes to a saved forecast, not realized performance or a fresh transfer recommendation. The existing team forecast artifact uses a separate path and was not regenerated.

## Prioritized next upgrades

1. **Fixture-level inputs and aggregation.** `build_workbench_inputs.py` assigns one fixture per `(team, gameweek)` and silently overwrites earlier fixtures in a double gameweek. `calculate_snapshot` also allocates goal shares by team/gameweek. Move to fixture IDs throughout, score each fixture, then aggregate gameweeks. Count actual completed team fixtures instead of `start_gameweek - 1`.
2. **Calibrate playing time and event distributions.** The fixed 95% probability of reaching 60 minutes conditional on starting is not learned from player history. Minutes per start include substitute minutes; full-match clean-sheet probability ignores substitution timing. Fit and validate minute states, DC tails and save distributions with historical pre-deadline features. Penalty/set-piece orders are present in inputs but unused in allocation.
3. **Unify forecast provenance before promotion.** The research stack, snapshot workbench, saved live-team output and Django random forest are distinct paths. Record model/version/input cutoff on each forecast and replay the exact serving calculation before claiming the historical improvement applies to it.
4. **Fix the separate Django ML training path before trusting its validation.** `etl/ml/features.py` computes season points per game over all athlete rows without a pre-gameweek cutoff; current ownership, transfer totals and availability are reused for historical examples. It also turns a legitimate zero availability into 100 via `or 100`. Historical training needs season-aware, as-of features and archived mutable inputs. This path was reviewed but not changed in this first workbench upgrade.
5. **Freeze decision validation.** Use a predeclared rolling-origin protocol, an untouched future acceptance period, ranking/captain/transfer utility, and paired hold comparisons. Preserve the previous audit's rejection of optimizer/horizon promotion. Do not retune repeatedly on 2025/26 and call it untouched.

The first upgrade is ready for review in the new worktree. The recommended next implementation is fixture-level support, followed by calibrated minutes and a serving-equivalent rolling backtest.

## Follow-up delivered: fixture support

The next implementation above is now complete as `workbench-v3-fixture-scoring`.
The input builder retains fixture IDs, multiple matches and unknown kickoff times,
and counts finished earlier-gameweek fixtures. Scoring allocates within each match,
then aggregates weekly points, minutes, components and return probabilities. The
API retains one weekly summary with nested `matches`; the UI and both reports show
individual fixtures. Duplicate fixture rows are rejected. Captain and horizon
values use weekly totals, including blanks. Cross-match probability independence
is explicitly disclosed.

23 focused tests pass, including a cached builder-to-service test covering a double,
a postponed match, unknown kickoff and a blank between scoring weeks. The frontend
build passes and browser checks confirm values and horizon selection. Rebuilding
the saved schema leaves all 1,956 existing single-match xP estimates unchanged.
The next substantive model work is minutes calibration and serving-equivalent
validation; this upgrade does not establish improved predictive accuracy.
