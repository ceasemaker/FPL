# Premier League Data API (pulselive)

Research notes on the stats backend behind premierleague.com, verified by direct
requests on 14 October 2026. Nothing here is wired into AeroFPL yet.

> **Terms.** Neither API is public or documented. Both serve premierleague.com,
> whose terms reserve intellectual-property rights in its data. Treat them as
> research sources until we decide whether AeroFPL's use is acceptable
> (personal/study vs commercial). Keep request volume low, cache everything, and
> make anything built on them fail gracefully: they can change without notice.

## How to call them

Every call is an unauthenticated `GET` with one header:

```
Origin: https://www.premierleague.com
```

No package is needed; `requests`/`urllib` is enough. A research sweep of 1,040
sequential requests with a 0.4 s pause hit no rate limit or error.

There are two hosts. The site migrated to the second in its 2025 relaunch, but
the first still answers and holds data the second does not.

| | Classic API | SDP API (current site) |
|---|---|---|
| Base URL | `https://footballapi.pulselive.com/football/` | `https://sdp-prem-prod.premier-league-prod.pulselive.com/api/` |
| Competition | `comps=1` | `competitions/8` |
| Season | internal id: 2026/27 = `841`, 2025/26 = `777` | year the season starts: 2026/27 = `2026` |
| Player id | pulselive id (Haaland `65970`) | Opta id (Haaland `223094`) |
| Match id | pulselive id (`128980`) | Opta id (`2645252`) |
| Stat names | snake_case (`total_scoring_att`) | camelCase (`totalShots`) |

The classic API returns the Opta ids too (`altIds.opta`, e.g. `p223094`,
`g2645252`), so records can be joined across both. FPL's xG/xA match these feeds
exactly (Haaland 2026/27 xG: 4.82 in both), so FPL's numbers come from the same
Opta source.

## What each API provides

### Classic API

| Endpoint | What you get |
|---|---|
| `competitions/1/compseasons` | All 35 seasons, 1992/93 to 2026/27, with ids |
| `compseasons/{season}/teams` | The 20 clubs and their ids |
| `players?compSeasons={season}&pageSize=100&page=N` | Every registered player (1,018 in 2025/26) |
| `stats/player/{id}?comps=1&compSeasons={season}` | A player's full season stat sheet (catalogue below) |
| `stats/player/{id}?fixtures={matchId}` | **The same sheet for a single match** (Cherki v Liverpool: 97 stats) |
| `stats/team/{id}?comps=1&compSeasons={season}` | A club's full season stat sheet |
| `stats/ranked/players/{stat}?compSeasons={season}` | League leaderboard for any one stat |
| `stats/ranked/teams/{stat}?compSeasons={season}` | Club leaderboard for any one stat |
| `compseasons/{season}/standings` | League table |
| `fixtures?comps=1&compSeasons={season}&statuses=C` | Results (use `statuses=U` for upcoming) |
| `fixtures/{matchId}` | Match detail: lineups and bench, officials, venue, attendance, half-time score, key-event timeline |
| `stats/match/{matchId}` | ~153 team stats per side for one match, plus formation |
| `fixtures/{matchId}/textstream/EN?pageSize=200` | Full text commentary (129 entries for one match) |

**History depth.** Seasons go back to 1992/93, but detail varies. Arsenal's
1992/93 sheet has 15 basic stats; 2013/14 has the full 229. The exact season the
detailed stats start was not pinned down.

**Stat sheets only list non-zero values**, so a player with no penalties has no
`att_pen_goal` key. Treat a missing stat as 0, not unknown.

### SDP API (current site)

| Endpoint | What you get |
|---|---|
| `v2/competitions/8/seasons/{year}/players/{optaId}/stats` | Player season stats, 128 curated keys **including `expectedGoals`, `expectedAssists`, `expectedGoalsOnTarget`** |
| `v1/competitions/8/players/{optaId}/stats` | Player career stats |
| `v1/players/{optaId}` · `v1/players/{optaId}/basic` · `v2/players-by-id?id=a,b,c` | Player bios, bulk lookup |
| `v1/competitions/8/seasons/{year}/teams` | Clubs |
| `v2/matches?competition=8&season={year}&matchweek={n}` | Fixtures and results by gameweek |
| `v2/matches/{optaId}` | Match summary |
| `v3/matches/{optaId}/stats` | 194 team stats per match, **with xG, xA, xGOT, free-kick xG** |
| `v3/matches/{optaId}/lineups` | Lineups with positions and captains |
| `v1/matches/{optaId}/events` | Goals, cards and subs per team |
| `v1/matches/{optaId}/timeline` | Every key event with clock and timestamps (lineup confirmed, period start/end, goals, cards, subs) |
| `v1/matches/{optaId}/momentum` | Raw Opta feed: minute-by-minute momentum (home/away/combined), goals, cards **with reasons** (e.g. dissent), subs, formation and each player's formation slot |
| `v2/matches/{optaId}/commentary?_limit=100&lang=en` | Commentary, paginated with `_next` |
| `v1/matches/{optaId}/officials` | Referee and officials |
| `v2/matches/{optaId}/preview` | Previous meetings (head to head) |

## Coordinates and timelines

**No x/y coordinates are available.** Every endpoint the match centre and player
pages call was checked, plus the classic API. None carries pitch coordinates for
shots, passes, touches or any other event. The underlying Opta feed has full
coverage (`coverageLevel: 13`), but it is not served. The closest substitutes:

- **Shot placement and location stats** (`att_goal_low_left`, `att_sv_high_right`,
  `att_ibox_*` / `att_obox_*`, `att_bx_centre`, …): counts by goal-mouth zone and
  by inside/outside the box, not points on a pitch.
- **Commentary text**, which describes each shot in words that can be parsed
  ("right footed shot from outside the box misses to the right. Assisted by
  Rayan Cherki following a corner") and lists the shooter and assister ids.
- **Formation slots** (`formationPlace`, `positionSide`) for tactical position, not
  location.

**Timelines are available.** There are three levels of detail:
1. `v1/matches/{id}/timeline` (SDP) or `fixtures/{id}` events (classic): key
   events (goals, cards, subs, period start and end) with match clock and real time.
2. `v1/matches/{id}/momentum`: a per-minute momentum series for the whole match.
3. Text commentary: every shot, corner, free kick, offside and card, in order,
   with player ids.

**Goals in order (stored).** `sync_match_goals` stores every Premier League match
(`v2/matches?competition=8&season={year}&_limit=100`, cursor-paged with `_next`) and,
for finished ones, its goals from `v1/matches/{id}/events` into `PlMatch`/`MatchGoal`
(2021/22 onwards; the daily pipeline adds new matches). Things to know about that payload:
- `goalType` is `Goal`, `Penalty` or `Own`. Own goals are listed under the team that
  benefited, so each side's goals add up to its score (the sync checks this and retries a
  match that doesn't).
- `time` is the match minute. First-half stoppage can read past 45 (e.g. `54` with
  `period: FirstHalf`), so the period decides which half a goal belongs to; `timestamp`
  gives the exact order.
- Python `requests` can't reach pulselive from the local sandbox (curl can); run the sync on
  Render.

Chart Lab's clutch goals (`etl/services/clutch.py`) values each goal by the league points
it added, using win probabilities estimated from these matches.

## Other competitions

The SDP API lists 62 competitions and the classic API 115 (cups, women's, youth,
friendlies, Scottish and Belgian leagues, and more). Being listed doesn't mean
having data. Coverage of the ones that matter for transfers and promoted clubs,
tested for 2025/26 on 14 October 2026:

| Competition | SDP API | Classic API |
|---|---|---|
| Premier League | Full, **with xG/xA/xGOT** | Full (293 stats) |
| Championship (promoted clubs) | Fixtures and results only; stat sheets empty | **Full player sheets** (e.g. 189 stats for 2025/26's top scorer); seasons through 2026/27 |
| Champions League | Match and player stats, **no xG** | Full player sheets (169 stats, 2025/26) |
| Europa League / Conference League | Match stats (175 / 164 keys), no xG | Listed; not tested |
| La Liga | No 2025/26 matches | Full sheets (167 stats) **up to 2024/25 only** |
| Serie A, Bundesliga, Ligue 1 | Not listed; no matches under their Opta ids (21, 22, 24) | Not listed |
| Spanish Segunda División | — | Stops at 2017/18 |
| Scottish Premiership | No 2025/26 matches | Basic stats only (7), up to 2024/25 |
| Belgian Pro League | Fixtures, no stats | Listed; not tested |

So for incoming players and promoted clubs, the **Championship** (classic API)
and **Champions League** (both) are usable. Serie A, the Bundesliga and Ligue 1
are not covered, and La Liga only up to 2024/25. Only the Premier League has xG.

## Loaded into AeroFPL

`python manage.py sync_season_stats` loads season stat sheets into the
`player_season_stats` table (`PlayerSeasonStat`). Rows are keyed by source,
competition (Opta id: 8 PL, 10 Championship, 5 UCL), season (start year) and
Opta player id, and linked to `Athlete` via `Athlete.code` (FPL's `code` is the
Opta id). Re-running upserts.

| Load | Command |
|---|---|
| Premier League, SDP (xG, xGOT; ~130 stats) | `sync_season_stats --season 2026` |
| Premier League, classic (~260 stats) | `sync_season_stats --season 2026 --source classic` |
| Champions League, classic | `sync_season_stats --season 2026 --source classic --competition champions-league` |
| Championship, classic | `sync_season_stats --season 2026 --source classic --competition championship` |

- **SDP** lists players through the paginated leaderboard
  (`v2/competitions/{id}/seasons/{year}/players/stats/leaderboard`, cursor
  `_next`), then fetches each full sheet; the leaderboard alone has only 64 keys
  and no xG. Its paging can repeat a player, which the upsert absorbs.
- **Classic** looks up the season id from its label, lists players through the
  minutes leaderboard (`stats/ranked/players/mins_played`, so only players with
  minutes), then fetches each sheet. `source_player_id` keeps the pulselive id
  for the per-match endpoint.
- **Championship 2026/27 has no stats yet** (checked 14 October 2026): 115
  matches played, but the leaderboards, match stats and player sheets are all
  empty. 2025/26 is fully populated, so the data may arrive later in the season.
- **Championship 2024/25 has no stats at all** (checked 14 October 2026): the
  season (id 723) lists 1,381 squad players, but the leaderboards and every
  player sheet sampled are empty. Championship coverage starts with 2025/26.
- **Season clubs.** Player sheets carry only the club a player is at *today*.
  `sync_season_teams --season S [--competition C]` reads each club's squad for
  that season (SDP `v2/competitions/{c}/seasons/{s}/teams/{team}/squad`; classic
  `teams/{team}/compseasons/{cs}/staff`, matched on the squad entry's `id`, not
  `playerId`) and fills `season_team_id`/`season_team_name`. Usage rates need it.
- **Speed and rate limits.** `sync_season_stats --workers 3` fetches sheets in
  parallel (about 2–3 minutes a season). Six workers triggered HTTP 429; the
  client now backs off on 429 (Retry-After, else 15 s × attempt).
- **Loaded so far:** Premier League 2024/25 (SDP 725 players, classic 562),
  2025/26 (SDP 790, classic 537) and 2026/27; Champions League 2024/25 (879),
  2025/26 (871) and 2026/27 (623); Championship 2025/26 (503); club sheets for
  all three PL seasons.

## What this adds over FPL

FPL already gives xG, xA, xGC, ICT, bonus and the basics per gameweek. These APIs
add the event-level detail FPL lacks: shots and shot quality (on target, big
chances, inside/outside box), xG on target, key passes and chances created,
touches in the box, duels, dribbles, tackles, recoveries, crosses and goalkeeper
actions. They also offer **per-match player sheets** (classic
`stats/player/{id}?fixtures={matchId}`), the gameweek-level detail Chart Lab
trends and the prediction model would need.

## Full stat catalogue: classic API

The full catalogue comes from every 2025/26 player sheet (1,018 players, 513
with an appearance) and all 20 club sheets: **293 distinct stats, 264 at player
level and 261 at club level.** "Players with it" counts how many players
recorded a non-zero value, which shows how rare a stat is.

### Appearances & results (11)

| Stat | Player | Club | Players with it in 2025/26 |
|---|:-:|:-:|--:|
| `appearances` | ✓ |  | 513 |
| `game_started` | ✓ |  | 452 |
| `mins_played` | ✓ |  | 513 |
| `total_sub_on` | ✓ |  | 434 |
| `total_sub_off` | ✓ |  | 398 |
| `wins` | ✓ | ✓ | 458 |
| `draws` | ✓ | ✓ | 462 |
| `losses` | ✓ | ✓ | 487 |
| `subs_made` |  | ✓ | — |
| `pts_dropped_winning_pos` |  | ✓ | — |
| `pts_gained_losing_pos` |  | ✓ | — |

### Goals (26)

| Stat | Player | Club | Players with it in 2025/26 |
|---|:-:|:-:|--:|
| `goals` | ✓ | ✓ | 272 |
| `goals_openplay` | ✓ | ✓ | 208 |
| `goal_fastbreak` | ✓ | ✓ | 61 |
| `att_pen_goal` | ✓ | ✓ | 32 |
| `att_freekick_goal` | ✓ | ✓ | 13 |
| `att_hd_goal` | ✓ | ✓ | 114 |
| `att_ibox_goal` | ✓ | ✓ | 257 |
| `att_obox_goal` | ✓ | ✓ | 91 |
| `att_lf_goal` | ✓ | ✓ | 138 |
| `att_rf_goal` | ✓ | ✓ | 187 |
| `att_obp_goal` | ✓ | ✓ | 8 |
| `goals_ibox` |  | ✓ | — |
| `goals_obox` |  | ✓ | — |
| `first_half_goals` |  | ✓ | — |
| `defender_goals` |  | ✓ | — |
| `midfielder_goals` |  | ✓ | — |
| `forward_goals` |  | ✓ | — |
| `subs_goals` |  | ✓ | — |
| `direct_corner_goals` |  | ✓ | — |
| `direct_setpiece_goals` | ✓ | ✓ | 3 |
| `winning_goal` | ✓ |  | 513 |
| `big_chance_scored` | ✓ | ✓ | 219 |
| `own_goals` | ✓ | ✓ | 35 |
| `own_goal_accrued` |  | ✓ | — |
| `att_ibox_own_goal` |  | ✓ | — |
| `att_obox_own_goal` |  | ✓ | — |

### Shots (40)

| Stat | Player | Club | Players with it in 2025/26 |
|---|:-:|:-:|--:|
| `total_scoring_att` | ✓ | ✓ | 422 |
| `ontarget_scoring_att` | ✓ | ✓ | 369 |
| `shot_off_target` | ✓ | ✓ | 401 |
| `blocked_scoring_att` | ✓ | ✓ | 376 |
| `post_scoring_att` | ✓ | ✓ | 150 |
| `hit_woodwork` | ✓ | ✓ | 183 |
| `big_chance_missed` | ✓ | ✓ | 296 |
| `att_one_on_one` | ✓ | ✓ | 99 |
| `att_fastbreak` | ✓ | ✓ | 206 |
| `shot_fastbreak` | ✓ | ✓ | 206 |
| `total_fastbreak` | ✓ | ✓ | 228 |
| `att_openplay` | ✓ | ✓ | 397 |
| `att_setpiece` | ✓ | ✓ | 249 |
| `att_corner` | ✓ | ✓ | 344 |
| `attempts_ibox` | ✓ | ✓ | 407 |
| `attempts_obox` | ✓ | ✓ | 348 |
| `att_ibox_target` | ✓ | ✓ | 328 |
| `att_ibox_miss` | ✓ | ✓ | 372 |
| `att_ibox_blocked` | ✓ | ✓ | 348 |
| `att_ibox_post` | ✓ | ✓ | 118 |
| `att_obox_target` | ✓ | ✓ | 229 |
| `att_obox_miss` | ✓ | ✓ | 300 |
| `att_obox_blocked` | ✓ | ✓ | 283 |
| `att_obox_post` | ✓ | ✓ | 50 |
| `att_hd_total` | ✓ | ✓ | 309 |
| `att_hd_target` | ✓ | ✓ | 174 |
| `att_hd_miss` | ✓ | ✓ | 264 |
| `att_hd_post` | ✓ | ✓ | 55 |
| `att_lf_total` | ✓ | ✓ | 352 |
| `att_lf_target` | ✓ | ✓ | 220 |
| `att_rf_total` | ✓ | ✓ | 376 |
| `att_rf_target` | ✓ | ✓ | 280 |
| `att_freekick_total` | ✓ | ✓ | 83 |
| `att_freekick_target` | ✓ | ✓ | 46 |
| `att_freekick_miss` | ✓ | ✓ | 47 |
| `att_freekick_post` | ✓ | ✓ | 11 |
| `att_pen_target` | ✓ | ✓ | 11 |
| `att_pen_miss` | ✓ | ✓ | 2 |
| `att_pen_post` | ✓ | ✓ | 2 |
| `penalty_won` | ✓ | ✓ | 62 |

### Shot placement (36)

| Stat | Player | Club | Players with it in 2025/26 |
|---|:-:|:-:|--:|
| `att_goal_low_left` | ✓ | ✓ | 152 |
| `att_goal_low_centre` | ✓ | ✓ | 130 |
| `att_goal_low_right` | ✓ | ✓ | 140 |
| `att_goal_high_left` | ✓ | ✓ | 79 |
| `att_goal_high_centre` | ✓ | ✓ | 70 |
| `att_goal_high_right` | ✓ | ✓ | 74 |
| `att_sv_low_left` | ✓ | ✓ | 221 |
| `att_sv_low_centre` | ✓ | ✓ | 288 |
| `att_sv_low_right` | ✓ | ✓ | 219 |
| `att_sv_high_left` | ✓ | ✓ | 117 |
| `att_sv_high_centre` | ✓ | ✓ | 193 |
| `att_sv_high_right` | ✓ | ✓ | 103 |
| `att_miss_left` | ✓ | ✓ | 313 |
| `att_miss_right` | ✓ | ✓ | 311 |
| `att_miss_high` | ✓ | ✓ | 306 |
| `att_miss_high_left` | ✓ | ✓ | 200 |
| `att_miss_high_right` | ✓ | ✓ | 212 |
| `att_cmiss_left` | ✓ | ✓ | 188 |
| `att_cmiss_right` | ✓ | ✓ | 206 |
| `att_cmiss_high` | ✓ | ✓ | 148 |
| `att_cmiss_high_left` | ✓ | ✓ | 45 |
| `att_cmiss_high_right` | ✓ | ✓ | 56 |
| `att_post_left` | ✓ | ✓ | 57 |
| `att_post_right` | ✓ | ✓ | 56 |
| `att_post_high` | ✓ | ✓ | 69 |
| `att_bx_left` | ✓ | ✓ | 241 |
| `att_bx_centre` | ✓ | ✓ | 383 |
| `att_bx_right` | ✓ | ✓ | 238 |
| `att_obx_left` | ✓ | ✓ | 11 |
| `att_obx_centre` | ✓ | ✓ | 346 |
| `att_obx_right` | ✓ | ✓ | 12 |
| `att_obxd_left` | ✓ | ✓ | 20 |
| `att_obxd_right` | ✓ | ✓ | 14 |
| `att_lg_left` | ✓ | ✓ | 4 |
| `att_lg_centre` | ✓ | ✓ | 46 |
| `att_lg_right` | ✓ | ✓ | 8 |

### Chance creation & assists (21)

| Stat | Player | Club | Players with it in 2025/26 |
|---|:-:|:-:|--:|
| `goal_assist` | ✓ | ✓ | 272 |
| `goal_assist_openplay` | ✓ | ✓ | 249 |
| `goal_assist_setplay` | ✓ | ✓ | 105 |
| `goal_assist_deadball` | ✓ | ✓ | 43 |
| `goal_assist_intentional` | ✓ | ✓ | 238 |
| `second_goal_assist` | ✓ |  | 57 |
| `total_att_assist` | ✓ | ✓ | 427 |
| `att_assist_openplay` | ✓ | ✓ | 419 |
| `att_assist_setplay` | ✓ | ✓ | 147 |
| `ontarget_att_assist` | ✓ | ✓ | 408 |
| `offtarget_att_assist` | ✓ | ✓ | 380 |
| `big_chance_created` | ✓ | ✓ | 322 |
| `shot_created` | ✓ | ✓ | 336 |
| `assist_blocked_shot` | ✓ |  | 25 |
| `assist_attempt_saved` | ✓ |  | 28 |
| `assist_post` | ✓ |  | 8 |
| `assist_own_goal` | ✓ |  | 36 |
| `assist_penalty_won` | ✓ |  | 41 |
| `assist_free_kick_won` | ✓ |  | 13 |
| `assist_handball_won` | ✓ |  | 16 |
| `assist_pass_lost` | ✓ |  | 70 |

### Passing (35)

| Stat | Player | Club | Players with it in 2025/26 |
|---|:-:|:-:|--:|
| `total_pass` | ✓ | ✓ | 507 |
| `accurate_pass` | ✓ | ✓ | 505 |
| `open_play_pass` | ✓ | ✓ | 507 |
| `successful_open_play_pass` | ✓ | ✓ | 505 |
| `fwd_pass` | ✓ | ✓ | 499 |
| `backward_pass` | ✓ | ✓ | 470 |
| `leftside_pass` | ✓ | ✓ | 496 |
| `rightside_pass` | ✓ | ✓ | 490 |
| `passes_left` | ✓ | ✓ | 485 |
| `passes_right` | ✓ | ✓ | 489 |
| `total_fwd_zone_pass` | ✓ | ✓ | 507 |
| `accurate_fwd_zone_pass` | ✓ | ✓ | 503 |
| `total_back_zone_pass` | ✓ | ✓ | 500 |
| `accurate_back_zone_pass` | ✓ | ✓ | 498 |
| `total_long_balls` | ✓ | ✓ | 479 |
| `accurate_long_balls` | ✓ | ✓ | 459 |
| `total_launches` | ✓ | ✓ | 432 |
| `accurate_launches` | ✓ | ✓ | 350 |
| `total_chipped_pass` | ✓ | ✓ | 473 |
| `accurate_chipped_pass` | ✓ | ✓ | 447 |
| `total_through_ball` | ✓ | ✓ | 297 |
| `accurate_through_ball` | ✓ | ✓ | 200 |
| `total_layoffs` | ✓ | ✓ | 373 |
| `accurate_layoffs` | ✓ | ✓ | 366 |
| `total_flick_on` | ✓ | ✓ | 373 |
| `accurate_flick_on` | ✓ | ✓ | 286 |
| `head_pass` | ✓ |  | 457 |
| `long_pass_own_to_opp` | ✓ | ✓ | 486 |
| `long_pass_own_to_opp_success` | ✓ | ✓ | 473 |
| `total_final_third_passes` | ✓ | ✓ | 503 |
| `successful_final_third_passes` | ✓ | ✓ | 498 |
| `put_through` | ✓ | ✓ | 452 |
| `successful_put_through` | ✓ | ✓ | 430 |
| `blocked_pass` | ✓ | ✓ | 430 |
| `opposition_passes` |  | ✓ | — |

### Crossing & set pieces (18)

| Stat | Player | Club | Players with it in 2025/26 |
|---|:-:|:-:|--:|
| `total_cross` | ✓ | ✓ | 414 |
| `accurate_cross` | ✓ | ✓ | 321 |
| `total_cross_nocorner` | ✓ | ✓ | 411 |
| `accurate_cross_nocorner` | ✓ | ✓ | 316 |
| `crosses_18yard` | ✓ | ✓ | 371 |
| `crosses_18yardplus` | ✓ | ✓ | 358 |
| `blocked_cross` | ✓ | ✓ | 294 |
| `effective_blocked_cross` | ✓ | ✓ | 294 |
| `freekick_cross` | ✓ | ✓ | 126 |
| `accurate_freekick_cross` | ✓ | ✓ | 81 |
| `total_pull_back` | ✓ | ✓ | 215 |
| `accurate_pull_back` | ✓ | ✓ | 133 |
| `corner_taken` | ✓ | ✓ | 191 |
| `total_corners_intobox` | ✓ | ✓ | 161 |
| `accurate_corners_intobox` | ✓ | ✓ | 132 |
| `won_corners` | ✓ | ✓ | 405 |
| `lost_corners` | ✓ | ✓ | 407 |
| `foul_throw_in` | ✓ | ✓ | 32 |

### Territory & ball progression (16)

| Stat | Player | Club | Players with it in 2025/26 |
|---|:-:|:-:|--:|
| `touches` | ✓ | ✓ | 510 |
| `touches_in_final_third` | ✓ | ✓ | 483 |
| `touches_in_opp_box` | ✓ | ✓ | 448 |
| `final_third_entries` | ✓ | ✓ | 491 |
| `successful_final_third_entries` | ✓ | ✓ | 394 |
| `final_third_entries_open_play` | ✓ | ✓ | 403 |
| `successful_final_third_entries_open_play` | ✓ | ✓ | 387 |
| `pen_area_entries` | ✓ | ✓ | 469 |
| `successful_pen_area_entries` | ✓ | ✓ | 319 |
| `pen_area_entries_open_play` | ✓ | ✓ | 354 |
| `successful_pen_area_entries_open_play` | ✓ | ✓ | 294 |
| `carries` | ✓ | ✓ | 498 |
| `progressive_carries` | ✓ | ✓ | 487 |
| `overrun` | ✓ | ✓ | 264 |
| `shield_ball_oop` | ✓ | ✓ | 241 |
| `unsuccessful_touch` | ✓ | ✓ | 458 |

### Duels & possession (16)

| Stat | Player | Club | Players with it in 2025/26 |
|---|:-:|:-:|--:|
| `duel_won` | ✓ | ✓ | 490 |
| `duel_lost` | ✓ | ✓ | 492 |
| `aerial_won` | ✓ | ✓ | 454 |
| `aerial_lost` | ✓ | ✓ | 463 |
| `total_contest` | ✓ | ✓ | 446 |
| `won_contest` | ✓ | ✓ | 412 |
| `dispossessed` | ✓ | ✓ | 425 |
| `times_tackled` | ✓ |  | 513 |
| `turnover` | ✓ |  | 458 |
| `poss_lost_all` | ✓ | ✓ | 506 |
| `poss_lost_ctrl` | ✓ | ✓ | 506 |
| `poss_won_att_3rd` | ✓ | ✓ | 373 |
| `poss_won_mid_3rd` | ✓ | ✓ | 456 |
| `poss_won_def_3rd` | ✓ | ✓ | 469 |
| `ball_recovery` | ✓ | ✓ | 493 |
| `possession_percentage` |  | ✓ | — |

### Defending (16)

| Stat | Player | Club | Players with it in 2025/26 |
|---|:-:|:-:|--:|
| `total_tackle` | ✓ | ✓ | 457 |
| `won_tackle` | ✓ | ✓ | 434 |
| `last_man_tackle` | ✓ | ✓ | 103 |
| `challenge_lost` | ✓ | ✓ | 434 |
| `interception` | ✓ | ✓ | 413 |
| `interception_won` | ✓ | ✓ | 413 |
| `interceptions_in_box` | ✓ | ✓ | 256 |
| `total_clearance` | ✓ | ✓ | 465 |
| `effective_clearance` | ✓ | ✓ | 465 |
| `head_clearance` | ✓ | ✓ | 423 |
| `effective_head_clearance` | ✓ | ✓ | 423 |
| `clearance_off_line` | ✓ | ✓ | 77 |
| `outfielder_block` | ✓ | ✓ | 366 |
| `six_yard_block` | ✓ | ✓ | 211 |
| `defensive_actions` |  | ✓ | — |
| `ppda` |  | ✓ | — |

### Goalkeeping (25)

| Stat | Player | Club | Players with it in 2025/26 |
|---|:-:|:-:|--:|
| `saves` | ✓ | ✓ | 38 |
| `saved_ibox` | ✓ | ✓ | 38 |
| `saved_obox` | ✓ | ✓ | 34 |
| `diving_save` | ✓ | ✓ | 37 |
| `dive_save` | ✓ |  | 34 |
| `dive_catch` | ✓ |  | 12 |
| `stand_save` | ✓ |  | 33 |
| `stand_catch` | ✓ |  | 16 |
| `big_chance_saves` | ✓ | ✓ | 109 |
| `penalty_save` | ✓ | ✓ | 8 |
| `penalty_faced` | ✓ | ✓ | 30 |
| `punches` | ✓ | ✓ | 39 |
| `total_high_claim` | ✓ | ✓ | 36 |
| `good_high_claim` | ✓ | ✓ | 36 |
| `cross_not_claimed` | ✓ |  | 10 |
| `keeper_pick_up` | ✓ |  | 40 |
| `gk_smother` | ✓ |  | 27 |
| `total_keeper_sweeper` | ✓ | ✓ | 35 |
| `accurate_keeper_sweeper` | ✓ | ✓ | 35 |
| `keeper_throws` | ✓ | ✓ | 38 |
| `accurate_keeper_throws` | ✓ | ✓ | 38 |
| `total_throws` | ✓ | ✓ | 366 |
| `accurate_throws` | ✓ | ✓ | 359 |
| `goal_kicks` | ✓ | ✓ | 139 |
| `accurate_goal_kicks` | ✓ | ✓ | 138 |

### Conceding (8)

| Stat | Player | Club | Players with it in 2025/26 |
|---|:-:|:-:|--:|
| `clean_sheet` | ✓ | ✓ | 307 |
| `goals_conceded` | ✓ | ✓ | 480 |
| `goals_conceded_ibox` | ✓ | ✓ | 476 |
| `goals_conceded_obox` | ✓ | ✓ | 408 |
| `pen_goals_conceded` | ✓ | ✓ | 325 |
| `own_goals_conceded` | ✓ |  | 262 |
| `attempts_conceded_ibox` | ✓ | ✓ | 505 |
| `attempts_conceded_obox` | ✓ | ✓ | 493 |

### Discipline & errors (20)

| Stat | Player | Club | Players with it in 2025/26 |
|---|:-:|:-:|--:|
| `fouls` | ✓ |  | 439 |
| `was_fouled` | ✓ |  | 449 |
| `fouled_final_third` | ✓ | ✓ | 303 |
| `attempted_tackle_foul` | ✓ | ✓ | 424 |
| `fk_foul_won` |  | ✓ | — |
| `fk_foul_lost` |  | ✓ | — |
| `hand_ball` | ✓ | ✓ | 169 |
| `dangerous_play` | ✓ |  | 14 |
| `penalty_conceded` | ✓ | ✓ | 89 |
| `yellow_card` | ✓ |  | 363 |
| `red_card` | ✓ |  | 39 |
| `total_yel_card` |  | ✓ | — |
| `second_yellow` | ✓ | ✓ | 13 |
| `total_red_card` |  | ✓ | — |
| `staff_yellow` |  | ✓ | — |
| `total_offside` | ✓ | ✓ | 286 |
| `offside_provoked` | ✓ |  | 265 |
| `error_lead_to_shot` | ✓ | ✓ | 253 |
| `error_lead_to_goal` | ✓ | ✓ | 122 |
| `contentious_decision` |  | ✓ | — |

### Attendance (5)

| Stat | Player | Club | Players with it in 2025/26 |
|---|:-:|:-:|--:|
| `attendance_average` |  | ✓ | — |
| `attendance_count` |  | ✓ | — |
| `attendance_highest` |  | ✓ | — |
| `attendance_lowest` |  | ✓ | — |
| `attendance_total` |  | ✓ | — |

## Full stat catalogue: SDP API

The SDP API names stats differently and curates them. Its player and club lists are separate.

### Player season stats (128)

Collected from 20 players (the five most-used at each position, 2025/26):

`aerialDuels`, `aerialDuelsLost`, `aerialDuelsWon`, `appearances`, `attemptsFromSetPieces`, `awayGoals`, `backwardPasses`, `blockedShots`, `blocks`, `catches`, `cleanSheets`, `clearancesOffTheLine`, `cornersTakenInclShortCorners`, `cornersWon`, `crossesNotClaimed`, `drops`, `duels`, `duelsLost`, `duelsWon`, `expectedAssists`, `expectedGoals`, `expectedGoalsFreekick`, `expectedGoalsOnTarget`, `expectedGoalsOnTargetConceded`, `forwardPasses`, `foulAttemptedTackle`, `foulWonPenalty`, `freekickTotal`, `gamesPlayed`, `gkSuccessfulDistribution`, `gkUnsuccessfulDistribution`, `goalAssists`, `goalKicks`, `goalkeeperSmother`, `goals`, `goalsConceded`, `goalsConcededInsideBox`, `goalsConcededOutsideBox`, `groundDuels`, `groundDuelsLost`, `groundDuelsWon`, `handballsConceded`, `headedGoals`, `hitWoodwork`, `homeGoals`, `iboxBlocked`, `iboxTarget`, `interceptions`, `keyPassesAttemptAssists`, `lastPlayerTackle`, `leftFootGoals`, `leftsidePasses`, `oboxBlocked`, `oboxTarget`, `offsides`, `openPlayPasses`, `otherGoals`, `overruns`, `ownGoalScored`, `penaltiesConceded`, `penaltiesFaced`, `penaltiesSaved`, `penaltiesTaken`, `penaltyGoals`, `penaltyGoalsConceded`, `punches`, `putthroughBlockedDistribution`, `putthroughBlockedDistributionWon`, `recoveries`, `rightFootGoals`, `rightsidePasses`, `savesFromPenalty`, `savesMade`, `savesMadeCaught`, `savesMadeFromInsideBox`, `savesMadeFromOutsideBox`, `savesMadeParried`, `secondGoalAssists`, `setPiecesGoals`, `shotsBlockedInBox`, `shotsBlockedOutsideBox`, `shotsOffTargetIncWoodwork`, `shotsOnTargetInBox`, `shotsOnTargetIncGoals`, `shotsOnTargetOutsideBox`, `starts`, `straightRedCards`, `substituteOff`, `substituteOn`, `successfulCornersIntoBox`, `successfulCrossesAndCorners`, `successfulCrossesOpenPlay`, `successfulDribbles`, `successfulLaunches`, `successfulLayoffs`, `successfulLongPasses`, `successfulPassesOppositionHalf`, `successfulPassesOwnHalf`, `successfulShortPasses`, `tacklesLost`, `tacklesWon`, `throughBalls`, `throwInsToOppositionPlayer`, `throwInsToOwnPlayer`, `timePlayed`, `timesTackled`, `totalClearances`, `totalFoulsConceded`, `totalFoulsWon`, `totalLossesOfPossession`, `totalPasses`, `totalRedCards`, `totalShots`, `totalTackles`, `totalTouchesInOppositionBox`, `totalUnsuccessfulPassesExclCrossesAndCorners`, `touches`, `unsuccessfulCornersIntoBox`, `unsuccessfulCrossesAndCorners`, `unsuccessfulCrossesOpenPlay`, `unsuccessfulDribbles`, `unsuccessfulLaunches`, `unsuccessfulLayoffs`, `unsuccessfulLongPasses`, `unsuccessfulPassesOwnHalf`, `unsuccessfulShortPasses`, `winningGoal`, `yellowCards`

### Team match stats (194)

From `v3/matches/{id}/stats` (Liverpool v Man City, 11 October 2026, both sides):

`accurateBackZonePass`, `accurateChippedPass`, `accurateCornersIntobox`, `accurateCross`, `accurateCrossNocorner`, `accurateFlickOn`, `accurateFreekickCross`, `accurateFwdZonePass`, `accurateGoalKicks`, `accurateKeeperThrows`, `accurateLaunches`, `accurateLayoffs`, `accurateLongBalls`, `accuratePass`, `accuratePullBack`, `accurateThroughBall`, `accurateThrows`, `aerialLost`, `aerialWon`, `attAssistOpenplay`, `attAssistSetplay`, `attBxCentre`, `attBxLeft`, `attBxRight`, `attCmissLeft`, `attCmissRight`, `attCorner`, `attFastbreak`, `attFreekickGoal`, `attFreekickTarget`, `attFreekickTotal`, `attGoalHighCentre`, `attGoalHighLeft`, `attGoalHighRight`, `attGoalLowCentre`, `attGoalLowLeft`, `attGoalLowRight`, `attHdGoal`, `attHdTotal`, `attIboxBlocked`, `attIboxGoal`, `attIboxMiss`, `attIboxTarget`, `attLfGoal`, `attLfTarget`, `attLfTotal`, `attMissHigh`, `attMissHighRight`, `attMissLeft`, `attMissRight`, `attOboxBlocked`, `attOboxGoal`, `attOboxMiss`, `attOboxTarget`, `attObpGoal`, `attObxCentre`, `attOneOnOne`, `attOpenplay`, `attPenGoal`, `attRfGoal`, `attRfTarget`, `attRfTotal`, `attSetpiece`, `attSvHighLeft`, `attSvLowCentre`, `attSvLowLeft`, `attSvLowRight`, `attemptedTackleFoul`, `attemptsConcededIbox`, `attemptsConcededObox`, `attemptsIbox`, `attemptsObox`, `backwardPass`, `ballRecovery`, `bigChanceCreated`, `bigChanceMissed`, `bigChanceScored`, `blockedCross`, `blockedPass`, `blockedScoringAtt`, `challengeLost`, `cleanSheet`, `cornerTaken`, `crosses18yard`, `crosses18yardplus`, `defenderGoals`, `dispossessed`, `divingSave`, `duelLost`, `duelWon`, `effectiveBlockedCross`, `effectiveClearance`, `effectiveHeadClearance`, `errorLeadToShot`, `expectedAssists`, `expectedGoals`, `expectedGoalsFreekick`, `expectedGoalsOnTarget`, `expectedGoalsOnTargetConceded`, `fastestPlayer`, `finalThirdEntries`, `fkFoulLost`, `fkFoulWon`, `forwardGoals`, `fouledFinalThird`, `freekickCross`, `freekickTotal`, `fwdPass`, `goalAssist`, `goalAssistIntentional`, `goalAssistOpenplay`, `goalKicks`, `goals`, `goalsConceded`, `goalsConcededIbox`, `goalsConcededObox`, `goalsOpenplay`, `goodHighClaim`, `handBall`, `headClearance`, `interception`, `interceptionWon`, `interceptionsInBox`, `keeperGoals`, `keeperThrows`, `leftsidePass`, `longPassOwnToOpp`, `longPassOwnToOppSuccess`, `lostCorners`, `midfielderGoals`, `offtargetAttAssist`, `ontargetAttAssist`, `ontargetScoringAtt`, `openPlayPass`, `outfielderBlock`, `overrun`, `ownGoals`, `passesLeft`, `passesRight`, `penAreaEntries`, `possLostAll`, `possLostCtrl`, `possWonAtt3rd`, `possWonDef3rd`, `possWonMid3rd`, `possessionPercentage`, `putThrough`, `redCard`, `rightsidePass`, `savedIbox`, `savedObox`, `saves`, `secondYellow`, `shieldBallOop`, `shotFastbreak`, `shotOffTarget`, `subsGoals`, `subsMade`, `successfulFinalThirdPasses`, `successfulOpenPlayPass`, `successfulPutThrough`, `totalAttAssist`, `totalBackZonePass`, `totalChippedPass`, `totalClearance`, `totalContest`, `totalCornersIntobox`, `totalCross`, `totalCrossNocorner`, `totalFastbreak`, `totalFinalThirdPasses`, `totalFlickOn`, `totalFwdZonePass`, `totalHighClaim`, `totalLaunches`, `totalLayoffs`, `totalLongBalls`, `totalOffside`, `totalPass`, `totalPullBack`, `totalRedCard`, `totalScoringAtt`, `totalTackle`, `totalThroughBall`, `totalThrows`, `totalYelCard`, `touches`, `touchesInOppBox`, `unsuccessfulTouch`, `winningGoal`, `wonContest`, `wonCorners`, `wonTackle`, `yellowCard`
