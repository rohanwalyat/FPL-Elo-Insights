
  
    

  create  table "fpl_elo"."public_silver"."dim_teams__dbt_tmp"
  
  
    as
  
  (
    WITH fpl_teams AS (
    SELECT * FROM "fpl_elo"."public_silver"."stg_fpl__teams"
),

final AS (
    SELECT
        f.team_id,
        f.team_code,
        f.team_name,
        f.short_name,
        f.strength,
        -- Replace GitHub ELO with FPL composite strength
        (f.strength_overall_home + f.strength_overall_away) / 2.0 AS elo,
        f.strength_overall_home,
        f.strength_overall_away,
        f.strength_attack_home,
        f.strength_attack_away,
        f.strength_defence_home,
        f.strength_defence_away
    FROM fpl_teams f
)

SELECT * FROM final
  );
  