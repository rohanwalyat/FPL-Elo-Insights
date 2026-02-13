WITH source AS (
    SELECT CAST(league_entries AS JSON) as league_entries_json
    FROM {{ source('bronze_fpl', 'draft_league_league-details') }}
),

flattened AS (
    SELECT
        (json_array_elements(league_entries_json)->>'entry_id')::INT as owner_id,
        json_array_elements(league_entries_json)->>'entry_name' as entry_name,
        json_array_elements(league_entries_json)->>'player_first_name' as first_name,
        json_array_elements(league_entries_json)->>'player_last_name' as last_name,
        json_array_elements(league_entries_json)->>'short_name' as short_name
    FROM source
)

SELECT * FROM flattened
