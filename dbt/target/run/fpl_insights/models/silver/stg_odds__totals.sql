
  
    

  create  table "fpl_elo"."public_silver"."stg_odds__totals__dbt_tmp"
  
  
    as
  
  (
    WITH source AS (
    SELECT * FROM "fpl_elo"."bronze"."betting_odds_totals_odds"
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
  );
  