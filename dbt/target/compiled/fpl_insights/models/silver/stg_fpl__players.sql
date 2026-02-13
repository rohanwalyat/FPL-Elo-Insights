WITH source AS (
    SELECT * FROM "fpl_elo"."bronze"."fpl_api_bootstrap-static_elements"
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
        CAST(now_cost AS FLOAT) / 10 AS current_price,
        selected_by_percent,
        CAST(form AS FLOAT) AS form,
        CAST(points_per_game AS FLOAT) AS points_per_game,
        total_points,
        minutes,
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
        -- Set piece duties
        penalties_order,
        corners_and_indirect_freekicks_order,
        direct_freekicks_order
    FROM source
)

SELECT * FROM players