CREATE TABLE teams (
    id INT PRIMARY KEY,
    code INT,
    name VARCHAR(255) NOT NULL,
    short_name VARCHAR(10),
    strength INT,
    played INT DEFAULT 0,
    win INT DEFAULT 0,
    draw INT DEFAULT 0,
    loss INT DEFAULT 0,
    points INT DEFAULT 0,
    position INT,
    form VARCHAR(50), -- Assuming form might be a string like 'WWLDW'
    unavailable BOOLEAN DEFAULT FALSE,
    strength_overall_home INT,
    strength_overall_away INT,
    strength_attack_home INT,
    strength_attack_away INT,
    strength_defence_home INT,
    strength_defence_away INT,
    team_division INT, -- Can be NULL if a team is not in a division
    pulse_id INT
);
ALTER TABLE teams
ADD CONSTRAINT teams_code_unique UNIQUE (code);

-- Optional: Add comments to columns for better understanding
COMMENT ON COLUMN teams.id IS 'Primary Key: Unique identifier for the team';
COMMENT ON COLUMN teams.code IS 'A numerical code for the team';
COMMENT ON COLUMN teams.name IS 'Full name of the team (e.g., Arsenal)';
COMMENT ON COLUMN teams.short_name IS 'Short name or abbreviation for the team (e.g., ARS)';
COMMENT ON COLUMN teams.strength IS 'Overall strength rating of the team';
COMMENT ON COLUMN teams.played IS 'Number of games played';
COMMENT ON COLUMN teams.win IS 'Number of games won';
COMMENT ON COLUMN teams.draw IS 'Number of games drawn';
COMMENT ON COLUMN teams.loss IS 'Number of games lost';
COMMENT ON COLUMN teams.points IS 'Total points accumulated in the league';
COMMENT ON COLUMN teams.position IS 'Current league position of the team';
COMMENT ON COLUMN teams.form IS 'Recent match form (e.g., W, D, L sequence)';
COMMENT ON COLUMN teams.unavailable IS 'Flag indicating if the team is currently unavailable for selection/matches';
COMMENT ON COLUMN teams.strength_overall_home IS 'Overall strength when playing at home';
COMMENT ON COLUMN teams.strength_overall_away IS 'Overall strength when playing away';
COMMENT ON COLUMN teams.strength_attack_home IS 'Attacking strength when playing at home';
COMMENT ON COLUMN teams.strength_attack_away IS 'Attacking strength when playing away';
COMMENT ON COLUMN teams.strength_defence_home IS 'Defensive strength when playing at home';
COMMENT ON COLUMN teams.strength_defence_away IS 'Defensive strength when playing away';
COMMENT ON COLUMN teams.team_division IS 'Identifier for the division the team belongs to, can be NULL';
COMMENT ON COLUMN teams.pulse_id IS 'An external identifier, possibly from another system (e.g., Opta Pulse ID)';

-- Example of how to insert data (using the provided JSON as a basis):


CREATE TABLE athletes (
    id INT PRIMARY KEY,
    can_transact BOOLEAN,
    can_select BOOLEAN,
    chance_of_playing_next_round INT, -- Assuming percentage 0-100
    chance_of_playing_this_round INT, -- Assuming percentage 0-100
    code INT UNIQUE, -- Athlete's own unique code
    cost_change_event INT,
    cost_change_event_fall INT,
    cost_change_start INT,
    cost_change_start_fall INT,
    dreamteam_count INT,
    element_type INT, -- Potentially a FK to an element_types table
    ep_next NUMERIC(5, 2), -- Expected points next round
    ep_this NUMERIC(5, 2), -- Expected points this round
    event_points INT,
    first_name VARCHAR(255),
    form NUMERIC(5, 2),
    in_dreamteam BOOLEAN,
    news TEXT,
    news_added TIMESTAMP WITH TIME ZONE,
    now_cost INT,
    photo VARCHAR(255), -- File name or path
    points_per_game NUMERIC(5, 2),
    removed BOOLEAN DEFAULT FALSE,
    second_name VARCHAR(255),
    selected_by_percent NUMERIC(5, 2), -- Percentage
    special BOOLEAN,
    squad_number INT, -- Can be NULL
    status VARCHAR(10), -- e.g., 'a' (available), 'i' (injured), 's' (suspended)
    team INT, -- Corresponds to teams.id (the primary key of the teams table)
    team_code INT, -- Corresponds to teams.code
    total_points INT,
    transfers_in INT,
    transfers_in_event INT,
    transfers_out INT,
    transfers_out_event INT,
    value_form NUMERIC(5, 2),
    value_season NUMERIC(5, 2),
    web_name VARCHAR(255),
    region INT,
    team_join_date DATE,
    birth_date DATE,
    has_temporary_code BOOLEAN,
    opta_code VARCHAR(50),
    minutes INT,
    goals_scored INT,
    assists INT,
    clean_sheets INT,
    goals_conceded INT,
    own_goals INT,
    penalties_saved INT,
    penalties_missed INT,
    yellow_cards INT,
    red_cards INT,
    saves INT,
    bonus INT,
    bps INT, -- Bonus Points System
    influence NUMERIC(10, 2),
    creativity NUMERIC(10, 2),
    threat NUMERIC(10, 2),
    ict_index NUMERIC(10, 2),
    starts INT,
    expected_goals NUMERIC(10, 3),
    expected_assists NUMERIC(10, 3),
    expected_goal_involvements NUMERIC(10, 3),
    expected_goals_conceded NUMERIC(10, 3),
    mng_win INT,
    mng_draw INT,
    mng_loss INT,
    mng_underdog_win INT,
    mng_underdog_draw INT,
    mng_clean_sheets INT,
    mng_goals_scored INT,
    influence_rank INT,
    influence_rank_type INT,
    creativity_rank INT,
    creativity_rank_type INT,
    threat_rank INT,
    threat_rank_type INT,
    ict_index_rank INT,
    ict_index_rank_type INT,
    corners_and_indirect_freekicks_order INT, -- Can be NULL
    corners_and_indirect_freekicks_text TEXT,
    direct_freekicks_order INT, -- Can be NULL
    direct_freekicks_text TEXT,
    penalties_order INT, -- Can be NULL
    penalties_text TEXT,
    expected_goals_per_90 NUMERIC(10, 3),
    saves_per_90 NUMERIC(10, 3),
    expected_assists_per_90 NUMERIC(10, 3),
    expected_goal_involvements_per_90 NUMERIC(10, 3),
    expected_goals_conceded_per_90 NUMERIC(10, 3),
    goals_conceded_per_90 NUMERIC(10, 3),
    now_cost_rank INT,
    now_cost_rank_type INT,
    form_rank INT,
    form_rank_type INT,
    points_per_game_rank INT,
    points_per_game_rank_type INT,
    selected_rank INT,
    selected_rank_type INT,
    starts_per_90 NUMERIC(10, 3),
    clean_sheets_per_90 NUMERIC(10, 3),

    -- Foreign Key constraint
    -- Note: For this FK to be most effective in a one-to-many relationship,
    -- the 'code' column in the 'teams' table should have a UNIQUE constraint.
    CONSTRAINT fk_team_code
        FOREIGN KEY(team_code)
        REFERENCES teams(code)
        ON DELETE SET NULL -- Or ON DELETE RESTRICT, ON DELETE CASCADE, depending on desired behavior
        ON UPDATE CASCADE
);

-- Optional: Add comments to columns for better understanding (selected examples)
COMMENT ON COLUMN athletes.id IS 'Primary Key: Unique identifier for the athlete';
COMMENT ON COLUMN athletes.code IS 'Athlete specific code, should be unique for each athlete';
COMMENT ON COLUMN athletes.first_name IS 'Athlete''s first name';
COMMENT ON COLUMN athletes.second_name IS 'Athlete''s second name or surname';
COMMENT ON COLUMN athletes.web_name IS 'Display name for web (e.g., G.Jesus)';
COMMENT ON COLUMN athletes.team IS 'FK candidate: Identifier for the team the athlete belongs to (references teams.id)';
COMMENT ON COLUMN athletes.team_code IS 'FK: Identifier for the team code (references teams.code)';
COMMENT ON COLUMN athletes.news_added IS 'Timestamp when news about the athlete was added';
COMMENT ON COLUMN athletes.status IS 'Player status (e.g., available, injured, suspended)';
COMMENT ON COLUMN athletes.ict_index IS 'Influence, Creativity, Threat index score';


CREATE TABLE athlete_stats (
    id INT,                            -- Foreign key referencing athletes.id
    game_week INT,
    minutes INT DEFAULT 0,
    goals_scored INT DEFAULT 0,
    assists INT DEFAULT 0,
    clean_sheets INT DEFAULT 0,
    goals_conceded INT DEFAULT 0,
    own_goals INT DEFAULT 0,
    penalties_saved INT DEFAULT 0,
    penalties_missed INT DEFAULT 0,
    yellow_cards INT DEFAULT 0,
    red_cards INT DEFAULT 0,
    saves INT DEFAULT 0,
    bonus INT DEFAULT 0,
    bps INT DEFAULT 0,                 -- Bonus Points System
    influence NUMERIC(10, 2) DEFAULT 0.0,
    creativity NUMERIC(10, 2) DEFAULT 0.0,
    threat NUMERIC(10, 2) DEFAULT 0.0,
    ict_index NUMERIC(10, 2) DEFAULT 0.0, -- Influence, Creativity, Threat index
    starts INT DEFAULT 0,
    expected_goals NUMERIC(10, 3) DEFAULT 0.00,
    expected_assists NUMERIC(10, 3) DEFAULT 0.00,
    expected_goal_involvements NUMERIC(10, 3) DEFAULT 0.00,
    expected_goals_conceded NUMERIC(10, 3) DEFAULT 0.00,
    mng_win INT DEFAULT 0,             -- Manager win
    mng_draw INT DEFAULT 0,            -- Manager draw
    mng_loss INT DEFAULT 0,            -- Manager loss
    mng_underdog_win INT DEFAULT 0,
    mng_underdog_draw INT DEFAULT 0,
    mng_clean_sheets INT DEFAULT 0,
    mng_goals_scored INT DEFAULT 0,
    total_points INT DEFAULT 0,
    in_dreamteam BOOLEAN DEFAULT FALSE,

    -- Composite Primary Key
    PRIMARY KEY (id, game_week),

    -- Foreign Key constraint to ensure the athlete exists in the athletes table
    CONSTRAINT fk_athlete
        FOREIGN KEY(id)
        REFERENCES athletes(id)
        ON DELETE CASCADE -- If an athlete is deleted, their stats are also deleted
        ON UPDATE CASCADE -- If an athlete's id changes, update it here as well
);

-- Optional: Add comments to columns for better understanding
COMMENT ON COLUMN athlete_stats.id IS 'Foreign Key: References the id of the athlete in the athletes table.';
COMMENT ON COLUMN athlete_stats.game_week IS 'The specific game week for which these stats apply.';
COMMENT ON COLUMN athlete_stats.minutes IS 'Minutes played by the athlete in this game week.';
COMMENT ON COLUMN athlete_stats.ict_index IS 'Combined score for Influence, Creativity, and Threat for the game week.';
COMMENT ON COLUMN athlete_stats.bps IS 'Bonus Points System score for the game week.';
COMMENT ON COLUMN athlete_stats.total_points IS 'Total fantasy points scored by the athlete in this game week.';
COMMENT ON COLUMN athlete_stats.in_dreamteam IS 'Indicates if the athlete was part of the dream team for this game week.';
