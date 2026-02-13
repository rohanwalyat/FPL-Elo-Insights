WITH source AS (
    SELECT * FROM {{ source('bronze_fpl', 'betting_odds_totals_odds') }}
),

odds AS (
    SELECT
        id AS match_id,
        sport_key,
        sport_title,
        commence_time,
        home_team,
        away_team,
        bookmakers
    FROM source
)

SELECT * FROM odds
