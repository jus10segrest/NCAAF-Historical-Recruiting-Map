#imports
import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json

# load school configurations from JSON
CONFIG_FILE = "schools_config_github.json"

@st.cache_data
def load_school_config(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    else:
        st.error(f"Configuration file missing: {filepath}")
        return {}

SCHOOL_CONFIG = load_school_config(CONFIG_FILE)

# page config
st.set_page_config(
    page_title="College Football Recruiting Map",
    layout="wide",
    initial_sidebar_state="expanded"
)

def inject_custom_css(cfg):
    st.markdown(
        f"""
        <style>
        :root {{
            --primary-color: {cfg['primary_color']};
        }}
        html, body, [data-testid="stAppViewContainer"] {{
            --st-profile-primary: {cfg['primary_color']};
        }}
        div[data-testid="stMarkdownContainer"] + div [role="slider"] {{
            background-color: {cfg['primary_color']} !important;
            box-shadow: 0 0 0 2px {cfg['primary_color']} !important;
        }}
        div[data-baseweb="slider"] > div > div {{
            background: linear-gradient(to right, {cfg['primary_color']} 0%, {cfg['primary_color']} 100%) !important;
        }}
        div[data-testid="stAlert"] {{
            background-color: {cfg['alert_bg']} !important; 
            border-left: 5px solid {cfg['secondary_color']} !important; 
            color: #111111 !important;
        }}
        div[data-testid="stAlert"] p {{
            color: #111111 !important;
        }}
        .map-container {{
            border: 2px solid {cfg['primary_color']} !important; 
            border-radius: 8px;
            padding: 10px;
            background-color: #FFFFFF;
            box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.05);
            margin-bottom: 20px;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# data load
@st.cache_data
def load_data(school_name, cfg):
    df = pd.read_csv(cfg["csv_file"])

    position_map = {
        "WDE": "DE", "SDE": "DE", "ILB": "LB", "OLB": "LB", "LB": "LB",
        "OT": "OT", "OG": "IOL", "OC": "IOL", "IOL": "IOL", "RB": "RB",
        "APB": "RB", "FB": "RB", "WR": "WR", "TE": "TE", "DUAL": "QB",
        "PRO": "QB", "QB": "QB"
    }
    df["Position Group"] = df["Position"].map(position_map).fillna(df["Position"])
    df["HS Stars"] = df["HS Stars"].fillna(0).astype(int)
    df["Class Year"] = df["Class Year"].astype(int)

    def get_rating_label(row):
        stars = row["HS Stars"]
        year = row["Class Year"]
        if stars > 0:
            return f"{stars} Stars"
        elif year < 2011:
            return "Pre-2011 (No Data)"
        else:
            return "Unrated"

    df["Rating Label"] = df.apply(get_rating_label, axis=1)

    def get_coach_era(year):
        for start, end, label in cfg["eras"]:
            if start <= year <= end:
                return label
        return "Unknown Era"

    df["Coach Era"] = df["Class Year"].apply(get_coach_era)
    return df

# --- SIDEBAR INTERFACE ---
st.sidebar.header("School Settings")

# sort alphabetically
school_options = sorted(list(SCHOOL_CONFIG.keys()))

selected_school = st.sidebar.selectbox("Choose School", options=school_options, index=0)
cfg = SCHOOL_CONFIG[selected_school]

# Inject brand colors & layout styling
inject_custom_css(cfg)

# Dynamic Sidebar Components (Uniform Logo Container)
st.sidebar.markdown(
    f"""
    <div style="display: flex; justify-content: center; align-items: center; 
                height: 150px; width: 100%; margin-bottom: 20px;">
        <img src="{cfg['logo_url']}" style="max-height: 150px; max-width: 100%; object-fit: contain;">
    </div>
    """,
    unsafe_allow_html=True
)
st.sidebar.markdown("---")
st.sidebar.header("Filters")

# Main Page Title Block (Dynamic)
st.markdown(
    f"""
    <h1 style='color: {cfg['primary_color']}; margin-bottom: 0px;'>{selected_school} Football Recruits by Hometown</h1>
    <p style='color: {cfg['primary_color']}; font-size: 1.1rem; margin-top: 5px; font-weight: 500;'>
        Explore historical pipelines and talent distribution.
    </p>
    """,
    unsafe_allow_html=True
)
st.markdown("---")

# Data fetch
try:
    df = load_data(selected_school, cfg)
except FileNotFoundError:
    st.error(f"Could not locate data file: {cfg['csv_file']}")
    st.stop()

# Coaching Era Filter
available_eras = ["All Coaches"] + [era[2] for era in cfg["eras"]]
selected_era = st.sidebar.selectbox("Select Coach", options=available_eras, index=0, key="selected_era_key")

if selected_era != "All Coaches":
    df_era = df[df["Coach Era"] == selected_era]
else:
    df_era = df.copy()

# Year Slider
min_year = int(df_era["Class Year"].min())
max_year = int(df_era["Class Year"].max())

if min_year == max_year:
    # Single-year era: st.slider requires min_value < max_value, so just lock the range
    st.sidebar.markdown(f"**Class Years:** {min_year} (single-year coach)")
    year_range = (min_year, max_year)
else:
    year_range = st.sidebar.slider(
        "Class Years",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year),
        step=1,
        key="year_range_key"
    )

# Star Rating Dropdown Checkbox
st.sidebar.markdown("**Star Ratings**")
available_labels = sorted(df_era["Rating Label"].unique(), key=lambda x: (not "Pre-2011" in x, not "Unrated" in x, x))

if "star_version" not in st.session_state:
    st.session_state["star_version"] = 0

for label in available_labels:
    if f"star_state_{label}" not in st.session_state:
        st.session_state[f"star_state_{label}"] = True

star_popover = st.sidebar.popover("Select Star Ratings", use_container_width=True)
col1, col2 = star_popover.columns(2)

# Sanitize school name for stable key handling
school_id = selected_school.replace(" ", "_")

if col1.button("Select All", key=f"all_btn_{school_id}", use_container_width=True):
    for label in available_labels:
        st.session_state[f"star_state_{label}"] = True
    st.session_state["star_version"] += 1
    st.rerun()

if col2.button("Clear All", key=f"clear_btn_{school_id}", use_container_width=True):
    for label in available_labels:
        st.session_state[f"star_state_{label}"] = False
    st.session_state["star_version"] += 1
    st.rerun()

selected_rating_labels = []
for label in available_labels:
    state_key = f"star_state_{label}"
    v_key = f"chk_{school_id}_v{st.session_state['star_version']}_{label}"
    is_checked = star_popover.checkbox(label, value=st.session_state[state_key], key=v_key)
    st.session_state[state_key] = is_checked
    if is_checked:
        selected_rating_labels.append(label)

# Position Group Dropdown Checkbox
st.sidebar.markdown("**Position Groups**")
available_groups = sorted(df_era["Position Group"].dropna().unique())

if "pos_version" not in st.session_state:
    st.session_state["pos_version"] = 0

for group in available_groups:
    if f"pos_state_{group}" not in st.session_state:
        st.session_state[f"pos_state_{group}"] = True

pos_popover = st.sidebar.popover("Select Position Groups", use_container_width=True)
col1_pos, col2_pos = pos_popover.columns(2)

if col1_pos.button("Select All", key=f"all_pos_btn_{school_id}", use_container_width=True):
    for group in available_groups:
        st.session_state[f"pos_state_{group}"] = True
    st.session_state["pos_version"] += 1
    st.rerun()

if col2_pos.button("Clear All", key=f"clear_pos_btn_{school_id}", use_container_width=True):
    for group in available_groups:
        st.session_state[f"pos_state_{group}"] = False
    st.session_state["pos_version"] += 1
    st.rerun()

selected_position_groups = []
with pos_popover.container(height=200, border=False):
    for group in available_groups:
        state_key = f"pos_state_{group}"
        v_key_pos = f"chk_pos_{school_id}_v{st.session_state['pos_version']}_{group}"
        is_checked = st.checkbox(group, value=st.session_state[state_key], key=v_key_pos)
        st.session_state[state_key] = is_checked
        if is_checked:
            selected_position_groups.append(group)

# Master Reset Filters Button
st.sidebar.markdown("---")
def reset_all_filters_callback():
    st.session_state["selected_era_key"] = "All Coaches"
    st.session_state["year_range_key"] = (int(df["Class Year"].min()), int(df["Class Year"].max()))
    for label in sorted(df["Rating Label"].unique()):
        st.session_state[f"star_state_{label}"] = True
    st.session_state["star_version"] += 1
    for group in sorted(df["Position Group"].dropna().unique()):
        st.session_state[f"pos_state_{group}"] = True
    st.session_state["pos_version"] += 1

st.sidebar.button("🔄 Reset All Filters", on_click=reset_all_filters_callback, use_container_width=True)

# Filter Dataframe
filtered_df = df_era[
    (df_era["Class Year"] >= year_range[0]) &
    (df_era["Class Year"] <= year_range[1]) &
    (df_era["Rating Label"].isin(selected_rating_labels)) &
    (df_era["Position Group"].isin(selected_position_groups))
]

city_counts = filtered_df.groupby(["Hometown City", "Hometown State", "lat", "lon"]).size().reset_index(name="Count")
global_city_max = int(df.groupby(["Hometown City", "Hometown State"]).size().max())

anchor_row = pd.DataFrame([{
    "Hometown City": "ANCHOR", "Hometown State": "ANCHOR",
    "lat": 0.0, "lon": 0.0, "Count": global_city_max
}])

if not city_counts.empty:
    map_df = pd.concat([city_counts, anchor_row], ignore_index=True)
else:
    map_df = anchor_row

fig_bubble = px.scatter_geo(
    map_df,
    lat="lat",
    lon="lon",
    size="Count",
    hover_name="Hometown City",
    hover_data={"Hometown State": True, "Count": True, "lat": False, "lon": False},
    scope="usa",
    size_max=25,
)

fig_bubble.update_traces(
    marker=dict(
        color=cfg["primary_color"],
        line=dict(width=1.5, color="#111111"),
        opacity=0.85,
        sizemin=4
    )
)

if city_counts.empty:
    fig_bubble.update_traces(visible=False)

fig_bubble.update_layout(
    geo=dict(
        showland=True,
        landcolor="#FDFDFD",
        subunitcolor="rgb(180, 180, 180)",
        countrycolor="rgb(100, 100, 100)",
        bgcolor="rgba(0,0,0,0)",
        lakecolor="rgb(255, 255, 255)",
        showlakes=True
    ),
    margin={"r": 0, "t": 10, "l": 0, "b": 0},
    height=650
)

with st.container(border=True):
    selected_point = st.plotly_chart(
        fig_bubble,
        use_container_width=True,
        on_select="rerun"
    )

# Active filters banner
active_coach = selected_era
active_years = f"{year_range[0]} - {year_range[1]}"
active_stars = "All Ratings" if len(selected_rating_labels) == len(available_labels) else (", ".join(selected_rating_labels) if selected_rating_labels else "None Selected")
active_positions = "All Positions" if len(selected_position_groups) == len(available_groups) else (", ".join(selected_position_groups) if selected_position_groups else "None Selected")

st.info(
    f" **Active Filters ({selected_school}):**  \n"
    f" **Coach/Era:** {active_coach}  \n"
    f" **Years:** {active_years}  \n"
    f" **Stars:** `{active_stars}`  \n"
    f" **Positions:** `{active_positions}`"
)

# Insight tables
st.markdown("---")
col_table1, col_table2 = st.columns(2)

with col_table1:
    st.markdown("### Recruits by Star Rating")
    if not filtered_df.empty:
        stars_summary_df = filtered_df["Rating Label"].value_counts().reset_index()
        stars_summary_df.columns = ["Star Rating", "Total Recruits"]
        stars_summary_df = stars_summary_df.sort_values(
            by="Star Rating",
            ascending=False,
            key=lambda col: col.str.extract(r'(\d+)').fillna(0).astype(int)[0]
        )
        st.dataframe(stars_summary_df, use_container_width=True, hide_index=True)
    else:
        st.info("No rating data available for current filter selection.")

with col_table2:
    st.markdown("### Top Hometown States")
    if not filtered_df.empty:
        top_states_df = filtered_df["Hometown State"].value_counts().reset_index()
        top_states_df.columns = ["State", "Total Recruits"]
        st.dataframe(top_states_df.head(10), use_container_width=True, hide_index=True)
    else:
        st.info("No state data available for current filter selection.")

# Roster Explorer Panel
st.markdown("---")
st.markdown("### Selected Bubble Player Information")

if (
    selected_point
    and "selection" in selected_point
    and "points" in selected_point["selection"]
    and len(selected_point["selection"]["points"]) > 0
):
    point_data = selected_point["selection"]["points"][0]
    clicked_city = point_data.get("hovertext", "ANCHOR")

    if clicked_city != "ANCHOR":
        matched_row = map_df[(map_df["lat"] == point_data["lat"]) & (map_df["lon"] == point_data["lon"])]

        if not matched_row.empty:
            clicked_state = matched_row.iloc[0]["Hometown State"]
            roster_df = filtered_df[
                (filtered_df["Hometown City"] == clicked_city) &
                (filtered_df["Hometown State"] == clicked_state)
            ].sort_values(by="Class Year", ascending=False)

            st.success(f" Showing **{len(roster_df)}** recruits from **{clicked_city}, {clicked_state}**")
            clean_display_df = roster_df[[
                "Class Year", "Name", "Position Group", "Position",
                "HS Stars", "Rating Label", "High School", "Coach Era"
            ]]
            st.dataframe(clean_display_df, use_container_width=True, hide_index=True)
        else:
            st.info("Click on any city bubble on the map above to view the player information from that hometown")
    else:
        st.info("Click on any city bubble on the map above to view the player information from that hometown")
else:
    st.info("Click on any city bubble on the map above to view the player information from that hometown")