
  
    

  create  table "fpl_elo"."public_silver"."stg_ml__projections__dbt_tmp"
  
  
    as
  
  (
    with source as (
    select * from "fpl_elo"."public"."ml_projections"
),

renamed as (
    select
        player_id,
        web_name,
        gameweek,
        ml_xp
    from source
)

select * from renamed
  );
  