import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os

# Page config
st.set_page_config(page_title="Radio Tamazuj News Dashboard", page_icon="📰", layout="wide")
st.title("📰 Radio Tamazuj News Articles Dashboard")

st.write("This dashboard is a pilot. It extracted news articles from two media sources for "
         "two months and analyzed them via AI to get a summary, identify locations and  "
         "assign keywords. This analysis is a proof of concept and not meant to inform decisions.")


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =========================
# DATA LOADING
# =========================
@st.cache_data
def load_data(file):
    df = pd.read_csv(file)

    def parse_locations_and_coords(location_str, coord_str):
        locations = []
        if pd.isna(location_str) or pd.isna(coord_str):
            return locations

        try:
            location_names = [loc.strip() for loc in str(location_str).split(';')]
            coord_parts = str(coord_str).split(';')

            for i, coord_part in enumerate(coord_parts):
                coord_part = coord_part.strip().strip('()')
                lon, lat = coord_part.split(',')

                name = location_names[i] if i < len(location_names) else f"Location {i+1}"

                locations.append({
                    'name': name,
                    'longitude': float(lon.strip()),
                    'latitude': float(lat.strip())
                })
        except:
            pass

        return locations

    df['Locations_Parsed'] = df.apply(
        lambda r: parse_locations_and_coords(r['Location'], r['Coordinates']),
        axis=1
    )

    df['Keywords_List'] = df['Keywords'].apply(
        lambda x: [k.strip() for k in str(x).split(',') if k.strip()] if pd.notna(x) else []
    )

    return df


def combine_dataframes(df_list, names):
    dfs = []
    for df, name in zip(df_list, names):
        temp = df.copy()
        temp['Source_File'] = name
        dfs.append(temp)
    return pd.concat(dfs, ignore_index=True)


# =========================
# FILE INPUT (SIMPLIFIED)
# =========================
st.sidebar.header("📁 Data Source")

uploaded_files = st.sidebar.file_uploader(
    "Upload CSV file(s)",
    type=['csv'],
    accept_multiple_files=True
)


default_files = [
    os.path.join(BASE_DIR, 'radiotamazuj_2025_12_summary.csv'),
    os.path.join(BASE_DIR, 'southsudanherald_2025_12_summary.csv'),
    os.path.join(BASE_DIR, 'southsudanherald_2026_1_summary.csv')
]

# Combine sources
all_files = []

# Add defaults
for f in default_files:
    all_files.append((f, f))

# Add uploads
if uploaded_files:
    for f in uploaded_files:
        all_files.append((f, f.name))

# Load all
df_list = []
file_names = []

for file_obj, name in all_files:
    try:
        df_temp = load_data(file_obj)
        df_list.append(df_temp)
        file_names.append(name)
        st.sidebar.success(f"✓ Loaded: {name}")
    except Exception as e:
        st.sidebar.error(f"✗ {name}: {e}")

if not df_list:
    st.error("No valid data loaded.")
    st.stop()

df = combine_dataframes(df_list, file_names)
st.sidebar.info(f"Total files loaded: {len(df_list)}")


# =========================
# FILTERS
# =========================
st.sidebar.header("🔍 Filters")

unique_sources = sorted(df['Source_File'].unique())
selected_source = st.sidebar.selectbox(
    "Select Source",
    ['All'] + unique_sources
)

dates = ['All'] + sorted(df['Date'].dropna().unique())
selected_date = st.sidebar.selectbox("Select Date", dates)

all_keywords = sorted(set(k for lst in df['Keywords_List'] for k in lst))
selected_keyword = st.sidebar.selectbox(
    "Select Keyword",
    ['All'] + all_keywords
)

# Apply filters
filtered_df = df.copy()

if selected_source != 'All':
    filtered_df = filtered_df[filtered_df['Source_File'] == selected_source]

if selected_date != 'All':
    filtered_df = filtered_df[filtered_df['Date'] == selected_date]

if selected_keyword != 'All':
    filtered_df = filtered_df[
        filtered_df['Keywords_List'].apply(lambda x: selected_keyword in x)
    ]

map_df = filtered_df[
    filtered_df['Locations_Parsed'].apply(lambda x: len(x) > 0)
]


# =========================
# METRICS
# =========================
col1, col2, col3, col4 = st.columns(4)

col1.metric("Source Files", len(unique_sources))
col2.metric("Total Articles", len(filtered_df))
col3.metric("With Location", len(map_df))
col4.metric(
    "Location Points",
    sum(len(l) for l in map_df['Locations_Parsed'])
)


st.markdown("---")

# =========================
# MAP
# =========================
st.subheader("🗺️ Article Locations Map")

if len(map_df) > 0:
    all_lats = []
    all_lons = []

    for locations in map_df['Locations_Parsed']:
        for loc in locations:
            all_lats.append(loc['latitude'])
            all_lons.append(loc['longitude'])

    center_lat = sum(all_lats) / len(all_lats)
    center_lon = sum(all_lons) / len(all_lons)

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=6,
        tiles='OpenStreetMap'
    )

    colors = ['red', 'blue', 'green', 'purple', 'orange',
              'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen']

    for idx, row in map_df.iterrows():
        color = colors[idx % len(colors)]

        for loc_idx, location in enumerate(row['Locations_Parsed']):

            # ✅ FULL POPUP (your original rich box)
            popup_html = f"""
            <div style="width: 350px; max-height: 400px; overflow-y: auto;">
                <h4 style="margin-top: 0; margin-bottom: 10px; position: sticky; top: 0; background: white; padding: 10px 0; border-bottom: 2px solid #ddd;">
                    {row['Title']}
                </h4>

                <div style="padding: 5px 0;">
                    <p><strong>Summary:</strong></p>
                    <p style="font-size: 13px; line-height: 1.5;">{row['Summary']}</p>

                    <hr>

                    <p><strong>Date:</strong> {row['Date']}</p>
                    <p><strong>Location:</strong> {location['name']}</p>
                    <p><strong>All Locations:</strong> {row['Location']}</p>
                    <p><strong>Keywords:</strong> {row['Keywords']}</p>

                    <hr>

                    <p>
                        <a href="{row['URL']}" target="_blank"
                        style="color:#0066cc; text-decoration:none; font-weight:bold;">
                        📖 Read full article →
                        </a>
                    </p>
                </div>
            </div>
            """

            tooltip_text = f"{location['name']}: {row['Title'][:40]}..."

            folium.Marker(
                location=[location['latitude'], location['longitude']],
                popup=folium.Popup(popup_html, max_width=370),
                tooltip=tooltip_text,
                icon=folium.Icon(color=color, icon='info-sign')
            ).add_to(m)

    st_folium(m, width=1400, height=600)

else:
    st.warning("No map data for current filters.")

# =========================
# TABLE
# =========================
st.subheader("📊 Articles")

display_df = filtered_df[
    ['Title','Date','Location','Summary','Keywords','URL','Word Count']
].copy()

st.write(f"Showing {len(display_df)} articles")

st.dataframe(display_df, width='stretch')

# =========================
# DOWNLOAD
# =========================
csv = filtered_df.to_csv(index=False).encode('utf-8')

st.sidebar.download_button(
    "Download filtered CSV",
    csv,
    file_name="filtered_articles.csv"
)
