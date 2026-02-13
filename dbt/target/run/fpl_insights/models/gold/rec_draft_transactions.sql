
  
    

  create  table "fpl_elo"."public_gold"."rec_draft_transactions__dbt_tmp"
  
  
    as
  
  (
    WITH current_gw AS (
    SELECT MAX(gameweek_id) as last_gw
    FROM "fpl_elo"."public_silver"."stg_fpl__fixtures"
    WHERE finished = true
),

upcoming_fixtures AS (
    SELECT 
        fixture_id,
        gameweek_id,
        home_team_id as team_id,
        away_team_id as opponent_id,
        true as is_home
    FROM "fpl_elo"."public_silver"."stg_fpl__fixtures"
    WHERE gameweek_id > (SELECT last_gw FROM current_gw)
    AND gameweek_id <= (SELECT last_gw + 3 FROM current_gw)
    
    UNION ALL
    
    SELECT 
        fixture_id,
        gameweek_id,
        away_team_id as team_id,
        home_team_id as opponent_id,
        false as is_home
    FROM "fpl_elo"."public_silver"."stg_fpl__fixtures"
    WHERE gameweek_id > (SELECT last_gw FROM current_gw)
    AND gameweek_id <= (SELECT last_gw + 3 FROM current_gw)
),

market_odds AS (
    SELECT 
        h.home_team,
        h.away_team,
        h.home_win_prob,
        h.away_win_prob,
        t_home.team_id as home_team_id,
        t_away.team_id as away_team_id
    FROM "fpl_elo"."public_silver"."stg_odds__h2h" h
    JOIN "fpl_elo"."public_silver"."dim_teams" t_home ON h.home_team = t_home.team_name
    JOIN "fpl_elo"."public_silver"."dim_teams" t_away ON h.away_team = t_away.team_name
),

fixture_intelligence AS (
    SELECT 
        u.team_id,
        AVG(t.elo) as avg_opponent_elo,
        -- Venue Bias: Ratio of home games in next 3
        SUM(CASE WHEN is_home THEN 1 ELSE 0 END) / 3.0 as home_ratio,
        -- Market Factor: Avg win probability from betting odds for upcoming games
        AVG(CASE 
            WHEN u.is_home THEN mo.home_win_prob 
            ELSE mo.away_win_prob 
        END) as avg_market_win_prob
    FROM upcoming_fixtures u
    JOIN "fpl_elo"."public_silver"."dim_teams" t ON u.opponent_id = t.team_id
    LEFT JOIN market_odds mo ON (u.team_id = mo.home_team_id AND u.opponent_id = mo.away_team_id)
                             OR (u.team_id = mo.away_team_id AND u.opponent_id = mo.home_team_id)
    GROUP BY 1
),

draft_players AS (
    SELECT * FROM "fpl_elo"."public_silver"."dim_draft_players"
),

set_piece_lookup AS (
    SELECT 
        player_code,
        penalties_order,
        corners_and_indirect_freekicks_order as corner_order,
        direct_freekicks_order as fk_order
    FROM "fpl_elo"."public_silver"."stg_fpl__players"
),

teams AS (
    SELECT * FROM "fpl_elo"."public_silver"."dim_teams"
),

ml_preds AS (
    SELECT * FROM "fpl_elo"."public_silver"."stg_ml__projections"
),

player_combined AS (
    SELECT 
        d.player_id,
        d.web_name,
        d.availability_status,
        d.owner_name,
        d.position_id,
        d.form,
        d.ep_next,
        COALESCE(mlp.ml_xp, d.ep_next, 0) as ml_xp, -- Fallback to FPL EP if ML missing
        d.expected_goal_involvements,
        d.minutes,
        d.starts,
        d.total_points,
        d.clean_sheets,
        -- Injury & Availability
        d.player_status,
        COALESCE(d.chance_of_playing_next_round, 
            CASE 
                WHEN d.player_status IN ('i', 'u', 's') THEN 0
                WHEN d.player_status = 'd' THEN 50
                ELSE 100 
            END
        ) as availability_chance,
        d.draft_rank,
        d.defensive_contribution,
        -- Set piece bonuses from FPL Standard API (numeric, reliable)
        CASE WHEN sp.penalties_order IS NOT NULL AND sp.penalties_order <= 2 
             THEN 1 ELSE 0 END as is_penalty_taker,
        CASE WHEN sp.corner_order IS NOT NULL AND sp.corner_order <= 2 
             THEN 1 ELSE 0 END as is_corner_taker,
        CASE WHEN sp.fk_order IS NOT NULL AND sp.fk_order <= 2 
             THEN 1 ELSE 0 END as is_fk_taker,
        t.team_name,
        t.elo as team_elo,
        COALESCE(fi.avg_opponent_elo, 1200) as avg_opponent_elo,
        COALESCE(fi.home_ratio, 0.5) as home_ratio,
        COALESCE(fi.avg_market_win_prob, 0.33) as market_factor,
        (SELECT last_gw FROM current_gw) as last_gw
    FROM draft_players d
    JOIN teams t ON d.team_id = t.team_id
    LEFT JOIN fixture_intelligence fi ON d.team_id = fi.team_id
    LEFT JOIN set_piece_lookup sp ON d.player_code = sp.player_code
    LEFT JOIN ml_preds mlp ON d.player_id = mlp.player_id AND mlp.gameweek = (SELECT last_gw + 1 FROM current_gw)
),

scoring AS (
    SELECT 
        *,
        -- Normalized Fixture Delta
        0.5 + ((team_elo - avg_opponent_elo) / 1000.0) as fixture_factor,
        
        -- Momentum: Form relative to season ppg
        CASE 
            WHEN last_gw > 5 AND (total_points / last_gw) > 0.5 
            THEN LEAST(form / (total_points / last_gw), 2.0) / 2.0
            ELSE 0.5 
        END as momentum_factor,

        -- Minutes Risk
        CASE WHEN last_gw > 0 
             THEN LEAST(minutes / (last_gw * 90.0), 1.0) 
             ELSE 1.0 
        END as minutes_reliability,

        -- Set-Piece Composite Bonus (0-1 range)
        (is_penalty_taker * 0.6 + is_corner_taker * 0.25 + is_fk_taker * 0.15) as set_piece_bonus,

        -- Availability Multiplier (0-1)
        availability_chance / 100.0 as availability_multiplier
    FROM player_combined
),

final_recommendations AS (
    SELECT 
        *,
        (CASE 
            WHEN position_id IN (1, 2) -- GKP, DEF: prioritize clean sheet probability and ML predictions
            THEN (ml_xp * 0.40) + (form * 0.15) + (minutes_reliability * 0.10) + (market_factor * 0.15) + (fixture_factor * 0.10) + (momentum_factor * 0.10)
            ELSE -- MID, FWD: prioritize ML predictions and goal involvement
            (ml_xp * 0.40) + (form * 0.15) + (expected_goal_involvements * 0.20) + (market_factor * 0.10) + (fixture_factor * 0.10) + (momentum_factor * 0.05)
        END 
            * (1.0 + (home_ratio * 0.1))           -- Venue boost: up to +10%
            * availability_multiplier                -- Injury/loan zero-out
            * (CASE WHEN minutes_reliability < 0.6 THEN 0.8 ELSE 1.0 END)  -- Bench risk penalty
        ) as recommendation_score
    FROM scoring
),

-- Position scarcity: avg score of available free agents per position
position_replacement AS (
    SELECT 
        position_id,
        AVG(CASE WHEN recommendation_score > 0 THEN recommendation_score END) as avg_free_score,
        MAX(recommendation_score) as best_free_score
    FROM final_recommendations
    WHERE availability_status = 'Available' 
    AND availability_multiplier > 0
    GROUP BY 1
),

-- Final output with VAR and drop priority
with_intelligence AS (
    SELECT 
        f.*,
        -- VAR: Value Above Replacement (how much better than avg free agent at same position)
        CASE WHEN pr.avg_free_score > 0 
             THEN ROUND((f.recommendation_score / pr.avg_free_score)::numeric, 2)
             ELSE 0 
        END as var_score,
        -- Best available free agent at this position
        COALESCE(pr.best_free_score, 0) as best_free_at_position,
        -- Drop Priority: positive = upgrade available on waivers
        CASE WHEN f.owner_name != 'Free Agent' 
             THEN ROUND((pr.best_free_score - f.recommendation_score)::numeric, 2)
             ELSE NULL
        END as drop_priority
    FROM final_recommendations f
    LEFT JOIN position_replacement pr ON f.position_id = pr.position_id
)

SELECT * FROM with_intelligence
ORDER BY recommendation_score DESC
  );
  