WITH source AS (
    SELECT * FROM "fpl_elo"."bronze"."betting_odds_h2h_odds"
),

parsed_odds AS (
    SELECT
        id AS match_id,
        home_team,
        away_team,
        commence_time,
        -- Extract first bookmaker's H2H market outcomes
        -- Using jsonb traversal: bookmakers -> 0 -> markets -> 0 -> outcomes
        CAST(bookmakers AS JSONB)->0->'markets'->0->'outcomes' as outcomes
    FROM source
),

probabilities AS (
    SELECT
        match_id,
        home_team,
        away_team,
        commence_time,
        -- Extract prices for Home, Away, and Draw
        (SELECT CAST(value->>'price' AS FLOAT) FROM jsonb_array_elements(outcomes) WHERE value->>'name' = home_team) as home_price,
        (SELECT CAST(value->>'price' AS FLOAT) FROM jsonb_array_elements(outcomes) WHERE value->>'name' = away_team) as away_price,
        (SELECT CAST(value->>'price' AS FLOAT) FROM jsonb_array_elements(outcomes) WHERE value->>'name' = 'Draw') as draw_price
    FROM parsed_odds
),

normalized_probs AS (
    SELECT
        *,
        (1.0 / home_price) as raw_home_prob,
        (1.0 / away_price) as raw_away_prob,
        (1.0 / draw_price) as raw_draw_prob,
        (1.0 / home_price) + (1.0 / away_price) + (1.0 / draw_price) as total_margin
    FROM probabilities
)

SELECT 
    match_id,
    home_team,
    away_team,
    commence_time,
    raw_home_prob / total_margin as home_win_prob,
    raw_away_prob / total_margin as away_win_prob,
    raw_draw_prob / total_margin as draw_prob
FROM normalized_probs