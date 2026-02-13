
  
    

  create  table "fpl_elo"."public_silver"."stg_github__players__dbt_tmp"
  
  
    as
  
  (
    WITH source AS (
    SELECT * FROM "fpl_elo"."bronze"."github_data_players"
),

players AS (
    SELECT
        player_id,
        player_code,
        first_name,
        second_name,
        web_name,
        team_code,
        position
    FROM source
)

SELECT * FROM players
  );
  