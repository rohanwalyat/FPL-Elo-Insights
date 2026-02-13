import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Load environment variables
load_dotenv()

# Database configuration
password = os.getenv('PGPASSWORD')
encoded_password = quote_plus(password) if password else ""
DB_URL = f"postgresql://{os.getenv('PGUSER')}:{encoded_password}@{os.getenv('PGHOST')}:{os.getenv('PGPORT')}/{os.getenv('PGDATABASE')}"

def get_data(query):
    engine = create_engine(DB_URL)
    return pd.read_sql(query, engine)

st.set_page_config(page_title="FPL Draft Insights", page_icon="⚽", layout="wide")

# Professional High-Contrast UI: Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #1e293b !important;
    }
    
    .stApp { background-color: #f8fafc; }
    
    h1 {
        color: #0f172a !important;
        font-size: 2.2rem !important;
        font-weight: 800 !important;
        margin-bottom: 0.2rem !important;
    }
    
    h2, h3 {
        color: #1e293b !important;
        border-left: 5px solid #3b82f6;
        padding-left: 15px;
        margin-top: 1.5rem !important;
        font-weight: 700 !important;
    }
    
    [data-testid="stMetric"] {
        background: #ffffff !important;
        padding: 20px !important;
        border-radius: 8px !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1) !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #64748b !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        font-size: 0.8rem !important;
    }
    
    [data-testid="stMetricValue"] {
        color: #2563eb !important;
    }
    
    .stDataFrame { border-radius: 8px !important; }
    
    section[data-testid="stSidebar"] {
        background-color: #0f172a !important;
    }
    
    section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] p,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #ffffff !important;
        font-weight: 500 !important;
    }
    
    section[data-testid="stSidebar"] img {
        margin-bottom: 20px;
        border-radius: 8px;
    }
    
    .subtext { font-size: 1.1rem; color: #475569; margin-bottom: 2rem; }
    .bolt { color: #2563eb; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

st.title("⚽ FPL Draft Insights")

st.markdown("""
<div class='subtext'>
    Advanced transaction intelligence for your FPL Draft league. Blending <span class='bolt'>Form</span>, 
    <span class='bolt'>Expected Returns</span>, and <span class='bolt'>Fixture Quality</span>.
</div>
""", unsafe_allow_html=True)

try:
    # Load Recommendations
    df = get_data("SELECT * FROM public_gold.rec_draft_transactions")
    
    # Sidebar Navigation
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/en/thumb/f/f2/Premier_League_Logo.svg/280px-Premier_League_Logo.svg.png", width=120)
    page = st.sidebar.radio("Navigation", ["Dashboard", "Model Logic"])
    
    if page == "Dashboard":
        # Sidebar Controls
        st.sidebar.divider()
        st.sidebar.subheader("Controls")
        
        # Position Mapping
        pos_map = {1: 'GKP', 2: 'DEF', 3: 'MID', 4: 'FWD'}
        pos_options = ['GKP', 'DEF', 'MID', 'FWD']
        selected_positions = st.sidebar.multiselect("Filter Position", options=pos_options, default=pos_options)
        
        # Team Filter
        team_options = sorted(df['team_name'].unique().tolist())
        selected_teams = st.sidebar.multiselect("Filter Teams", options=team_options, default=team_options)
        
        # Apply Filters
        df['pos_name'] = df['position_id'].map(pos_map)
        filtered_df = df[
            (df['pos_name'].isin(selected_positions)) & 
            (df['team_name'].isin(selected_teams))
        ]
        
        # ═══════════════════════════════════════════════════════
        # HERO: Top 3 Targets
        # ═══════════════════════════════════════════════════════
        top_available = filtered_df[filtered_df['availability_status'] == 'Available'].sort_values('recommendation_score', ascending=False).head(3)
        
        if not top_available.empty:
            st.subheader("🔥 Top Transfer Targets")
            mcols = st.columns(3)
            for i, (idx, row) in enumerate(top_available.iterrows()):
                with mcols[i]:
                    var_label = f"{row['var_score']}x VAR" if pd.notnull(row.get('var_score')) else ""
                    st.metric(
                        label=f"{row['web_name']} ({row['team_name']})", 
                        value=f"{row['recommendation_score']:.2f}",
                        delta=var_label,
                        delta_color="normal"
                    )

        st.divider()

        # ═══════════════════════════════════════════════════════
        # FEATURE 1: Free Agent Scout (with VAR) — FULL WIDTH
        # ═══════════════════════════════════════════════════════
        st.subheader("💎 Free Agent Scout")
        free_agents = filtered_df[filtered_df['availability_status'] == 'Available'].sort_values('recommendation_score', ascending=False)
        
        detailed_cols = [
            'web_name', 'pos_name', 'team_name', 'recommendation_score', 'var_score',
            'form', 'ml_xp', 'expected_goal_involvements', 
            'fixture_factor', 'minutes_reliability'
        ]
        
        fa_display = free_agents[detailed_cols].copy()
        fa_display['minutes_reliability'] = (fa_display['minutes_reliability'] * 100).round(0)
        
        st.dataframe(
            fa_display.rename(columns={
                'web_name': 'Player',
                'pos_name': 'Pos',
                'team_name': 'Team',
                'recommendation_score': 'Score',
                'var_score': 'VAR',
                'ml_xp': 'xP (ML)',
                'expected_goal_involvements': 'xGI',
                'fixture_factor': 'Fix',
                'minutes_reliability': 'Min%'
            }), 
            hide_index=True,
            use_container_width=True,
            column_config={
                "Player": st.column_config.TextColumn(width="medium"),
                "Pos": st.column_config.TextColumn(width="small"),
                "Team": st.column_config.TextColumn(width="medium"),
                "Score": st.column_config.NumberColumn(format="%.2f", width="small", help="V4 Weighted Score"),
                "VAR": st.column_config.NumberColumn(format="%.1fx", width="small", help="Value Above Replacement"),
                "form": st.column_config.NumberColumn(format="%.1f", width="small"),
                "xP (ML)": st.column_config.NumberColumn(format="%.1f", width="small", help="Machine Learning Expected Points"),
                "xGI": st.column_config.NumberColumn(format="%.2f", width="small"),
                "Fix": st.column_config.NumberColumn(format="%.2f", width="small"),
                "Min%": st.column_config.NumberColumn(format="%.0f%%", width="small")
            }
        )

        st.divider()

        # ═══════════════════════════════════════════════════════
        # FEATURE 2: Squad Health (with Drop Priority) — FULL WIDTH
        # ═══════════════════════════════════════════════════════
        st.subheader("📉 Squad Health")
        managers = sorted([m for m in df['owner_name'].unique() if m != 'Free Agent'])
        default_index = managers.index("Mudryk and Morty") if "Mudryk and Morty" in managers else 0
        selected_manager = st.selectbox("Select Manager", options=managers, index=default_index)
        
        if selected_manager:
            squad = filtered_df[filtered_df['owner_name'] == selected_manager].sort_values('recommendation_score', ascending=False)
            
            squad_display = squad[['web_name', 'pos_name', 'team_name', 'recommendation_score', 'var_score',
                                   'form', 'ml_xp', 'expected_goal_involvements', 
                                   'fixture_factor', 'minutes_reliability', 'drop_priority']].copy()
            squad_display['minutes_reliability'] = (squad_display['minutes_reliability'] * 100).round(0)
            
            st.dataframe(
                squad_display.rename(columns={
                    'web_name': 'Player',
                    'pos_name': 'Pos',
                    'team_name': 'Team',
                    'recommendation_score': 'Score',
                    'var_score': 'VAR',
                    'ml_xp': 'xP (ML)',
                    'expected_goal_involvements': 'xGI',
                    'fixture_factor': 'Fix',
                    'minutes_reliability': 'Min%',
                    'drop_priority': 'Drop?'
                }), 
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Player": st.column_config.TextColumn(width="medium"),
                    "Pos": st.column_config.TextColumn(width="small"),
                    "Team": st.column_config.TextColumn(width="medium"),
                    "Score": st.column_config.NumberColumn(format="%.2f", width="small"),
                    "VAR": st.column_config.NumberColumn(format="%.1fx", width="small"),
                    "xP (ML)": st.column_config.NumberColumn(format="%.1f", width="small", help="Machine Learning Expected Points"),
                    "xGI": st.column_config.NumberColumn(format="%.2f", width="small"),
                    "Fix": st.column_config.NumberColumn(format="%.2f", width="small"),
                    "Min%": st.column_config.NumberColumn(format="%.0f%%", width="small"),
                    "Drop?": st.column_config.NumberColumn(format="%.2f", width="small",
                        help="Positive = a better FA exists. Higher = more urgent to drop.")
                }
            )
            
            # Drop candidate callout
            drop_candidates = squad[squad['drop_priority'] > 0].sort_values('drop_priority', ascending=False)
            if not drop_candidates.empty:
                top_drop = drop_candidates.iloc[0]
                st.warning(
                    f"⚠️ **Drop candidate:** {top_drop['web_name']} (Drop priority: +{top_drop['drop_priority']:.2f}) — "
                    f"a better {pos_map.get(top_drop['position_id'], '?')} is available as a free agent."
                    )

        st.divider()

        # ═══════════════════════════════════════════════════════
        # FEATURE 3: Opponent Weakness Panel
        # ═══════════════════════════════════════════════════════
        st.subheader("🔍 Opponent Intel — Weakest Links")
        st.caption("Each manager's worst-performing available player — likely waiver drop candidates.")
        
        # Find weakest active player per manager
        owned_active = df[
            (df['owner_name'] != 'Free Agent') & 
            (df['availability_multiplier'] > 0)
        ].copy()
        
        weakness_rows = []
        for manager in sorted(owned_active['owner_name'].unique()):
            mgr_squad = owned_active[owned_active['owner_name'] == manager].sort_values('recommendation_score')
            if not mgr_squad.empty:
                weakest = mgr_squad.iloc[0]
                # Second weakest for context
                second_weakest = mgr_squad.iloc[1] if len(mgr_squad) > 1 else None
                
                # Manager squad total
                squad_total = mgr_squad['recommendation_score'].sum()
                squad_avg = mgr_squad['recommendation_score'].mean()
                
                weakness_rows.append({
                    'Manager': manager,
                    'Squad Power': round(squad_total, 1),
                    'Avg Score': round(squad_avg, 2),
                    'Weakest Player': weakest['web_name'],
                    'Weak Pos': pos_map.get(weakest['position_id'], '?'),
                    'Weak Score': round(weakest['recommendation_score'], 2),
                    'Drop?': round(weakest['drop_priority'], 2) if pd.notnull(weakest.get('drop_priority')) else None,
                    '2nd Weakest': second_weakest['web_name'] if second_weakest is not None else '-',
                })
        
        if weakness_rows:
            weakness_df = pd.DataFrame(weakness_rows).sort_values('Squad Power', ascending=False)
            st.dataframe(
                weakness_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Squad Power": st.column_config.NumberColumn(format="%.1f", help="Sum of all player scores"),
                    "Avg Score": st.column_config.NumberColumn(format="%.2f"),
                    "Weak Score": st.column_config.NumberColumn(format="%.2f"),
                    "Drop?": st.column_config.NumberColumn(format="+%.2f", help="How much better the best free agent is at this position"),
                }
            )
        
        st.divider()

        # ═══════════════════════════════════════════════════════
        # FEATURE 4: Fixture Streaming (GKP/DEF Pick)
        # ═══════════════════════════════════════════════════════
        st.subheader("📅 Fixture Streaming — GKP/DEF Picks")
        st.caption("Which goalkeeper or defender to start based on fixture difficulty. Lower opponent strength = easier fixture.")
        
        col_stream_left, col_stream_right = st.columns(2)
        
        with col_stream_left:
            st.markdown("##### 🧤 GKP Streaming")
            
            # Get GKPs for selected manager
            if selected_manager:
                mgr_gkps = df[
                    (df['owner_name'] == selected_manager) & 
                    (df['position_id'] == 1) &
                    (df['availability_multiplier'] > 0)
                ].sort_values('recommendation_score', ascending=False)
                
                if len(mgr_gkps) >= 2:
                    gkp1 = mgr_gkps.iloc[0]
                    gkp2 = mgr_gkps.iloc[1]
                    
                    g1_score = gkp1['recommendation_score']
                    g2_score = gkp2['recommendation_score']
                    
                    rec_gkp = gkp1 if g1_score >= g2_score else gkp2
                    alt_gkp = gkp2 if g1_score >= g2_score else gkp1
                    
                    st.success(
                        f"✅ **Start:** {rec_gkp['web_name']} ({rec_gkp['team_name']}) — "
                        f"Score: {rec_gkp['recommendation_score']:.2f}, "
                        f"Fix: {rec_gkp['fixture_factor']:.2f}"
                    )
                    st.info(
                        f"🔄 **Bench:** {alt_gkp['web_name']} ({alt_gkp['team_name']}) — "
                        f"Score: {alt_gkp['recommendation_score']:.2f}, "
                        f"Fix: {alt_gkp['fixture_factor']:.2f}"
                    )
                elif len(mgr_gkps) == 1:
                    gkp1 = mgr_gkps.iloc[0]
                    st.success(f"✅ **Start:** {gkp1['web_name']} ({gkp1['team_name']}) — Score: {gkp1['recommendation_score']:.2f}")
                    st.caption("Only 1 GKP in squad — no rotation possible.")
                else:
                    st.warning("No available GKPs in this manager's squad.")
        
        with col_stream_right:
            st.markdown("##### 🛡️ DEF Streaming")
            
            if selected_manager:
                mgr_defs = df[
                    (df['owner_name'] == selected_manager) & 
                    (df['position_id'] == 2) &
                    (df['availability_multiplier'] > 0)
                ].sort_values('recommendation_score', ascending=False)
                
                if not mgr_defs.empty:
                    # Show top 3 DEFs to start and bottom 2 to bench
                    start_count = min(3, len(mgr_defs))
                    bench_defs = mgr_defs.iloc[start_count:]
                    
                    for i in range(start_count):
                        d = mgr_defs.iloc[i]
                        st.success(
                            f"✅ {d['web_name']} ({d['team_name']}) — "
                            f"Score: {d['recommendation_score']:.2f}, "
                            f"Fix: {d['fixture_factor']:.2f}"
                        )
                    
                    for _, d in bench_defs.iterrows():
                        st.info(
                            f"🔄 {d['web_name']} ({d['team_name']}) — "
                            f"Score: {d['recommendation_score']:.2f}"
                        )
                else:
                    st.warning("No available DEFs in this manager's squad.")
        
        st.divider()

        # ═══════════════════════════════════════════════════════
        # Global Ranking
        # ═══════════════════════════════════════════════════════
        st.subheader("📊 Global Player Ranking")
        st.dataframe(
            filtered_df[['web_name', 'pos_name', 'team_name', 'recommendation_score', 'var_score', 'availability_status', 'owner_name']]
            .sort_values('recommendation_score', ascending=False)
            .rename(columns={
                'web_name': 'Player',
                'pos_name': 'Pos',
                'team_name': 'Team',
                'recommendation_score': 'Score',
                'var_score': 'VAR',
                'availability_status': 'Status',
                'owner_name': 'Owner'
            }), 
            hide_index=True,
            use_container_width=True,
            column_config={
                "Score": st.column_config.NumberColumn(format="%.2f", width="small", help="V4 Weighted Score"),
                "VAR": st.column_config.NumberColumn(format="%.1fx", width="small", help="Value Above Replacement"),
            }
        )
    
    elif page == "Model Logic":
        st.subheader("🧠 How the AI Works")
        st.markdown("""
        Our projected points (**xP ML**) are generated by a **Histogram-based Gradient Boosting Regressor**, a state-of-the-art machine learning algorithm similar to XGBoost. 
        It learns from historical player performance, match difficulty, and team strength to predict future returns.
        """)
        
        st.divider()
        
        st.markdown("### 📊 What drives the predictions?")
        st.caption("The chart below shows which features have the biggest impact on the model's predictions.")
        
        # Load Feature Importance
        try:
            fi_df = pd.read_csv('data/models/feature_importance.csv')
            
            # Position Selector
            if 'position' in fi_df.columns:
                unique_pos = fi_df['position'].unique()
                selected_pos = st.selectbox("Select Position Model", unique_pos)
                fi_df = fi_df[fi_df['position'] == selected_pos]
            
            # Clean feature names
            fi_df['feature'] = fi_df['feature'].str.replace('_', ' ').str.title()
            
            st.bar_chart(fi_df.set_index('feature')['importance'].head(15), color='#3b82f6')
            
        except Exception as e:
            st.warning(f"Feature importance data not found. (Error: {e})")
        
        st.divider()
        
        st.markdown("### 📖 Glossary")
        st.markdown("""
        - **Minutes Played (Roll 5)**: Average minutes played over the last 5 starts. Players with consistent game time are safer assets.
        - **xG (Expected Goals)**: Quality of goal scoring chances. A higher xG means a player is getting into good positions.
        - **xA (Expected Assists)**: Quality of passes leading to shots.
        - **Elo Diff**: The difference in team strength rating between the player's team and the opponent. Positive = Stronger than opponent.
        - **Saves**: Critical metric for Goalkeepers.
        """)

except Exception as e:
    st.error(f"Error loading dashboard: {e}")
    st.info("Ensure dbt models are Materialized: `dbt run`")

# Updated Sidebar Logic Documentation
st.sidebar.divider()
st.sidebar.subheader("🧠 Engine Logic (V4)")
st.sidebar.markdown("""
<div style='background: #1e293b; padding: 15px; border-radius: 8px; border: 1px solid #334155;'>
    <p style='margin-bottom: 5px;'><strong>DEF/GKP (V4):</strong></p>
    <ul style='font-size: 0.9rem; color: #94a3b8;'>
        <li>ML Expected Points: 40%</li>
        <li>Market Factor (Odds): 15%</li>
        <li>Fixture Strength: 25%</li>
        <li>Form: 15%</li>
        <li>Momentum Index: 10%</li>
    </ul>
    <p style='margin-bottom: 5px; margin-top: 10px;'><strong>MID/FWD (V4):</strong></p>
    <ul style='font-size: 0.9rem; color: #94a3b8;'>
        <li>ML Expected Points: 40%</li>
        <li>Expected GI: 20%</li>
        <li>Form: 15%</li>
        <li>Market Factor (Odds): 10%</li>
        <li>Fixture Strength: 10%</li>
        <li>Momentum Index: 5%</li>
    </ul>
    <p style='margin-top: 15px; font-size: 0.8rem; color: #38bdf8;'>
        🏠 <strong>Venue Boost:</strong> +10% for home games.
    </p>
    <p style='margin-top: 5px; font-size: 0.8rem; color: #22c55e;'>
        ⚽ <strong>Set-Piece:</strong> Penalty/Corner/FK taker bonuses.
    </p>
    <p style='margin-top: 5px; font-size: 0.8rem; color: #f43f5e;'>
        🚑 <strong>Injury Zero-Out:</strong> Unavailable → score = 0.
    </p>
    <p style='margin-top: 5px; font-size: 0.8rem; color: #f43f5e;'>
        ⚠️ <strong>Bench Risk:</strong> -20% for &lt;60% mins.
    </p>
</div>
""", unsafe_allow_html=True)

st.sidebar.divider()
st.sidebar.subheader("📊 New: Intelligence")
st.sidebar.markdown("""
<div style='background: #1e293b; padding: 15px; border-radius: 8px; border: 1px solid #334155;'>
    <p style='font-size: 0.85rem; color: #94a3b8;'>
        <strong style='color: #22c55e;'>VAR Score:</strong> Value Above Replacement. 
        Shows how many times better a player is vs. the average free agent at the same position.<br><br>
        <strong style='color: #f59e0b;'>Drop Priority:</strong> Positive = a better FA exists.
        Higher number = more urgently should be dropped.<br><br>
        <strong style='color: #ef4444;'>Opponent Intel:</strong> Weakest player per manager.
        These are likely to appear on waivers soon.<br><br>
        <strong style='color: #38bdf8;'>Fixture Streaming:</strong> GKP/DEF rotation
        based on fixture difficulty for selected manager.
    </p>
</div>
""", unsafe_allow_html=True)
