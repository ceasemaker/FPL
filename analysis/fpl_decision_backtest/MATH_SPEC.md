# FPL Decision System: Current Mathematics

This document describes the mathematics currently implemented. It deliberately
separates estimated quantities from hand-set decision rules.

## 1. One-gameweek player forecast

For player `p` before gameweek `g`, the feature vector contains only information
available through `g-1`:

\[
x_{p,g}=\bigl[g,\ price,\ history,\ P_{g-1},\ M_{g-1},\
\bar P_3,\bar P_6,s_{P,6},\bar M_3,\bar M_6,
appearance_6,start_6,xGI90_6,xGC90_6,ICT90_6,BPS90_6,position\bigr].
\]

Each numeric feature is median-imputed and standardized:

\[
z_j=\frac{x_j-\bar x_j}{s_j}.
\]

The target is the player's realized FPL points, clipped to `[-5,25]`. A ridge
regression with penalty `alpha=25` estimates:

\[
\hat\beta=(Z^\top Z+\alpha P)^{-1}Z^\top y,
\]

where the intercept is not penalized. The base expected-points estimate is:

\[
\hat\mu^{base}_{p,g}=clip(\hat\beta_0+z_{p,g}^\top\hat\beta,0,18).
\]

Models are walk-forward by season. For example, the 2025/26 model is trained
only on 2022/23 through 2024/25.

### Bookmaker calibration

For decimal odds `o_i`, the overround-free implied probability is:

\[
q_i=\frac{1/o_i}{\sum_j 1/o_j}.
\]

The ridge model is refit with five additional team-gameweek features: win,
draw, loss, over-2.5 probabilities and home status. Its output is the immediate
gameweek forecast used by the historical replay:

\[
\hat\mu_{p,g}=clip(\hat\beta^{odds}_0+z_{p,g}^\top\hat\beta^{odds},0,18).
\]

This reduced player-week MAE from `2.3608` to `2.3423` in 2025/26, a `0.79%`
improvement. It is useful but small.

## 2. Forecast uncertainty

Training residuals are:

\[
e_{p,g}=y_{p,g}-\hat\mu_{p,g}.
\]

Within each position, empirical residual quantiles `q_0.10` and `q_0.90` are
added to the mean:

\[
P10=clip(\hat\mu+q_{0.10},-3,18),\qquad
P90=clip(\hat\mu+q_{0.90},0,25).
\]

An approximate standard deviation is recovered with the width of a Normal 80%
interval:

\[
\hat\sigma=\frac{P90-P10}{\Phi^{-1}(0.9)-\Phi^{-1}(0.1)}
=\frac{P90-P10}{2.563}.
\]

This is an empirical uncertainty summary, not a player-specific probability
distribution.

## 3. Three-gameweek forecast used for transfers

At the deadline for gameweek `g`, player form is frozen. Later realized player
outcomes are never used to form the projections for `g+1` or `g+2`.

The archived fixture factor for a team is:

\[
F_{t,g}=f(difficulty_{t,g})h_{t,g},
\]

with:

\[
f(1,2,3,4,5)=(1.22,1.10,1.00,0.89,0.78)
\]

and `h=1.04` at home or `0.96` away. Factors are added for doubles and are zero
for blanks.

The frozen future projection is:

\[
\hat\mu_{p,g+k\mid g}=\hat\mu_{p,g}\times
clip\left(\frac{F_{team(p),g+k}}{F_{team(p),g}},0.55,1.65\right),
\qquad k\in\{1,2\}.
\]

If `g+k` is a blank, the projection is zero. The squad horizon value is:

\[
V_g(S)=\sum_{k=0}^{2}0.9^k L(S,\hat\mu_{g+k\mid g}),
\]

where `L` is the maximum legal XI score for that week:

\[
L(S,\mu)=\max_{XI,C}\left(\sum_{p\in XI}\mu_p+\mu_C\right).
\]

`XI` must contain 11 players in a legal FPL formation and `C` must be in the
XI. The captain receives one extra copy of expected points, for two copies in
total.

## 4. Transfer decision

For `n` transfers with `FT` banked free transfers, the action utility is:

\[
U(S')=V_g(S')-1.5n-4\max(0,n-FT).
\]

Holding has utility:

\[
U(S)=V_g(S).
\]

The policy selects the legal action with the largest utility among hold, one
transfer and two transfers. The `1.5` is an explicit option-cost heuristic for
spending a transfer; it is not estimated from data. Free transfers evolve as:

\[
FT_{g+1}=\min\{5,\max(0,FT_g-n)+1\}.
\]

Squad constraints are exactly 2 goalkeepers, 5 defenders, 5 midfielders and 3
forwards; no more than three players per club; and same-position replacements.
Historical affordability currently uses reconstructed opening prices, not exact
deadline sale prices.

## 5. Realized base-points comparison

After normal FPL autosubs, the realized score is:

\[
P_g=\sum_{p\in XI^{final}_g}P_{p,g}+P_{C,g}
-4\max(0,n-FT).
\]

If the captain plays zero minutes, the vice-captain receives the extra copy if
they enter the final XI. Bench Boost and Triple Captain multipliers are never
used. Thus every week is an ordinary XI plus one normal captain.

## 6. Ownership and rank exposure

Let player points be random variable `X` with mean `mu` and variance `v`. Let
`m` be our multiplier (`0` unowned, `1` owned, `2` captained) and `e` the
comparison cohort's effective ownership. Relative points are:

\[
R=(m-e)X.
\]

Therefore:

\[
E[R]=(m-e)\mu,\qquad Var(R)=(m-e)^2v.
\]

The change in relative variance from unowned to owned is:

\[
[(1-e)^2-e^2]v=(1-2e)v.
\]

The additional change from owned to captained is:

\[
[(2-e)^2-(1-e)^2]v=(3-2e)v.
\]

These identities are mathematically correct. Ownership changes rank exposure,
not the player's raw expected points. The balanced replay therefore maximizes
raw expected points and does not force ownership shields.

The live Protect/Chase view currently adds a scaled variance change to expected
points:

\[
utility=\mu+\lambda\Delta Var,
\]

where `lambda=-0.04` for Protect, `0` for Balanced and `0.025` for Chase. This
is a heuristic mean-variance utility and is not used by the historical team
replay.

## 7. Player value

Within each position and gameweek, a cross-sectional price curve is fitted:

\[
\widehat{xP}=a+b\,price,\qquad b\in[0,2].
\]

Then:

\[
valuation\ edge=\hat\mu-(a+b\,price).
\]

The replacement baseline is the 25th percentile of expected points among
players projected for at least 45 minutes. Value above replacement per extra
million is:

\[
VORP/£m=\frac{\hat\mu-\mu_{replacement}}
{\max(0.5,price-price_{min}+0.5)}.
\]

These are relative screening measures, not estimates of a player's market price.

## 8. Mathematical audit

### Defensible

- Walk-forward feature timing and season separation.
- Ridge estimator and no-vig probability normalization.
- Legal lineup/captain expected-points sum.
- Ownership relative-point expectation and variance identities.
- Explicit accounting for hit points and normal captain scoring.

### Heuristic but transparent

- The `0.90` horizon discount, `1.5` transfer option cost, FDR multipliers,
  home/away multipliers and projection-ratio caps.
- Position-wide residual intervals and Normal conversion to standard deviation.
- The 25th-percentile replacement level and linear price curve.
- Mean-variance Protect/Chase coefficients.

### Rejected from the original blueprint

The adapted Black-Scholes equation is not used. FPL expected points are not a
tradable underlying asset; no replicating portfolio or no-arbitrage argument
exists; `xP`, price, hit cost and appearance points have incompatible roles and
units in that mapping; player downside is not fixed at two; and volatility does
not mechanically create value. Volatility can help a rank-chasing utility or
captaincy decision, but only after expected points and the manager's objective
are specified.

Likewise, `xP(m-EO)` is valid as expected relative rank points, not as a revised
intrinsic player value. A 70% ownership threshold is a strategy preference, not
a mathematical law. A regression gap must compare commensurate quantities;
raw `xGI - actual FPL returns` does not.

## 9. What the failed replay tells us

The optimizer equations are coherent enough to test, but they optimize weak
inputs. The 2025/26 decision-player correlation is only `0.168` before the odds
layer and `0.223` with it. The three-gameweek replay's 0/100 result therefore
does not identify an algebra error by itself; it says the present expected-point
ranking and/or hand-set fixture/transfer rules are not decision-grade.

## 10. Structural Poisson forecast

The structural backtest replaces the direct points regression with an event
model. Opening bookmaker odds are first normalized to remove the overround. If
`p_over` is the no-vig over-2.5 probability, the total match intensity solves:

\[
p_{over}=1-e^{-\lambda_T}\left(1+\lambda_T+\frac{\lambda_T^2}{2}\right).
\]

Holding `lambda_T` fixed, a bounded numerical fit chooses the home share so an
independent Poisson score model best matches the no-vig home/draw/away
probabilities. This gives `lambda_home` and `lambda_away`.

For player `i`, six-match xG and xA rates are shifted by one gameweek and
shrunk toward position rates calculated from earlier seasons only:

\[
xG90_i=90\frac{xG_{i,6}+450\,xG90_{pos}/90}{mins_{i,6}+450}.
\]

Expected minutes use the same lag rule and three prior games of positional
shrinkage. Raw player event intensities are allocated proportionally and then
scaled so their team sum equals the market-implied team intensity:

\[
\lambda_{goal,i}=\lambda_{team}
\frac{xG90_i\,E[mins_i]/90}{\sum_j xG90_j\,E[mins_j]/90}.
\]

Assists use the equivalent xA share and an empirically conservative assumption
that 75% of team goals are assisted. Clean-sheet probability for a single
fixture is `exp(-lambda_opponent)`. Appearance, goals, assists, clean sheets,
goals-conceded deductions, saves, cards, own goals, penalties, bonus and the
2025/26 defensive-contribution rule are then converted with ordinary FPL point
values. Chips are not part of the forecast.

This model passes the general-error test but not yet the selection test. On the
untouched 2025/26 season its MAE is `2.217` versus `2.342` for ridge and its
correlation is `0.226` versus `0.223`. However, its weekly top-five selections
average `4.941` realized points versus `5.178` for ridge. It therefore remains
a structural/risk layer and is not yet the optimizer's sole ranking authority.
