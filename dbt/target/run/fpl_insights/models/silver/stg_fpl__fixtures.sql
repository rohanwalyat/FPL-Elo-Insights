
  
    

  create  table "fpl_elo"."public_silver"."stg_fpl__fixtures__dbt_tmp"
  
  
    as
  
  (
    WITH source AS (
    SELECT * FROM "fpl_elo"."bronze"."fpl_api_fixtures"
),

fixtures AS (
    SELECT
        id AS fixture_id,
        code AS fixture_code,
        team_h AS home_team_id,
        team_a AS away_team_id,
        team_h_difficulty AS home_difficulty,
        team_a_difficulty AS away_difficulty,
        team_h_score AS home_score,
        team_a_score AS away_score,
        finished,
        event AS gameweek_id,
        kickoff_time,
        minutes,
        provisional_start_time
    FROM source
)

SELECT * FROM fixtures
  );
  