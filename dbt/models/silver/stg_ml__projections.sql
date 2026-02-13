
with source as (
    select * from {{ source('public', 'ml_projections') }}
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
