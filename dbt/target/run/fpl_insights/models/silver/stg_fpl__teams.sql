
  
    

  create  table "fpl_elo"."public_silver"."stg_fpl__teams__dbt_tmp"
  
  
    as
  
  (
    WITH source AS (
    SELECT * FROM "fpl_elo"."bronze"."fpl_api_bootstrap-static_teams"
),

teams AS (
    SELECT
        id AS team_id,
        code AS team_code,
        name AS team_name,
        short_name,
        strength,
        strength_overall_home,
        strength_overall_away,
        strength_attack_home,
        strength_attack_away,
        strength_defence_home,
        strength_defence_away,
        pulse_id
    FROM source
)

SELECT * FROM teams
  );
  