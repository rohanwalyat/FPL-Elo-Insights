
  
    

  create  table "fpl_elo"."public_silver"."stg_fpl_draft__players__dbt_tmp"
  
  
    as
  
  (
    WITH source AS (
    SELECT * FROM "fpl_elo"."bronze"."draft_league_bootstrap-static_elements"
),

players AS (
    SELECT
        id AS player_id,
        code AS player_code,
        first_name,
        second_name,
        web_name,
        team AS team_id,
        element_type AS position_id,
        CAST(form AS FLOAT) AS form,
        CAST(ep_next AS FLOAT) AS ep_next,
        CAST(points_per_game AS FLOAT) AS points_per_game,
        total_points,
        minutes,
        starts,
        goals_scored,
        assists,
        clean_sheets,
        goals_conceded,
        own_goals,
        penalties_saved,
        penalties_missed,
        yellow_cards,
        red_cards,
        saves,
        bonus,
        bps,
        CAST(influence AS FLOAT) AS influence,
        CAST(creativity AS FLOAT) AS creativity,
        CAST(threat AS FLOAT) AS threat,
        CAST(ict_index AS FLOAT) AS ict_index,
        CAST(expected_goals AS FLOAT) AS expected_goals,
        CAST(expected_assists AS FLOAT) AS expected_assists,
        CAST(expected_goal_involvements AS FLOAT) AS expected_goal_involvements,
        CAST(expected_goals_conceded AS FLOAT) AS expected_goals_conceded,
        -- Availability & Injury
        status AS player_status,
        chance_of_playing_next_round,
        news,
        draft_rank,
        -- Defensive stats
        clearances_blocks_interceptions,
        recoveries,
        tackles,
        defensive_contribution,
        -- Set piece duty (text in Draft API, may be null)
        corners_and_indirect_freekicks_order AS corner_order_text,
        direct_freekicks_order AS fk_order_text,
        penalties_order AS penalty_order_text
    FROM source
)

SELECT * FROM players
  );
  