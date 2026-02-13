WITH players AS (
    SELECT * FROM {{ ref('stg_fpl_draft__players') }}
),

status AS (
    SELECT * FROM {{ ref('stg_fpl_draft__element_status') }}
),

entries AS (
    SELECT * FROM {{ ref('stg_fpl_draft__league_entries') }}
),

final AS (
    SELECT
        p.player_id,
        p.player_code,
        p.web_name,
        p.team_id,
        p.position_id,
        p.form,
        p.ep_next,
        p.points_per_game,
        p.expected_goal_involvements,
        p.minutes,
        p.starts,
        p.total_points,
        p.clean_sheets,
        -- Injury & Availability
        p.player_status,
        p.chance_of_playing_next_round,
        p.news,
        p.draft_rank,
        -- Defensive
        p.defensive_contribution,
        -- Set pieces
        p.penalty_order_text,
        p.corner_order_text,
        p.fk_order_text,
        -- Ownership
        s.status AS draft_status,
        s.owner_id,
        COALESCE(e.entry_name, 'Free Agent') as owner_name,
        COALESCE(e.first_name || ' ' || e.last_name, 'N/A') as owner_manager,
        CASE 
            WHEN s.status = 'a' THEN 'Available'
            WHEN s.status = 'o' THEN 'Owned'
            WHEN s.status = 'w' THEN 'Waivers'
            ELSE 'Unknown'
        END as availability_status
    FROM players p
    JOIN status s ON p.player_id = s.player_id
    LEFT JOIN entries e ON s.owner_id = e.owner_id
)

SELECT * FROM final
