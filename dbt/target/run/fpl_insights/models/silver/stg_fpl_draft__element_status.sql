
  
    

  create  table "fpl_elo"."public_silver"."stg_fpl_draft__element_status__dbt_tmp"
  
  
    as
  
  (
    WITH source AS (
    SELECT CAST(element_status AS JSON) as element_status_json
    FROM "fpl_elo"."bronze"."draft_league_element-status"
),

flattened AS (
    SELECT
        (json_array_elements(element_status_json)->>'element')::INT as player_id,
        json_array_elements(element_status_json)->>'status' as status,
        (json_array_elements(element_status_json)->>'owner')::INT as owner_id
    FROM source
)

SELECT * FROM flattened
  );
  