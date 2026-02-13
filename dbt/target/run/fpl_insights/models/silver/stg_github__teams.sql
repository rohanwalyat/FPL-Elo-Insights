
  
    

  create  table "fpl_elo"."public_silver"."stg_github__teams__dbt_tmp"
  
  
    as
  
  (
    WITH source AS (
    SELECT * FROM "fpl_elo"."bronze"."github_data_teams"
),

teams AS (
    SELECT
        id AS team_id,
        code AS team_code,
        name AS team_name,
        short_name,
        CAST(elo AS FLOAT) AS elo
        -- attack_elo and defence_elo missing in raw github data?
    FROM source
)

SELECT * FROM teams
  );
  