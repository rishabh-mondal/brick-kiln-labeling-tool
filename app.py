import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
from datetime import datetime
import glob

st.set_page_config(page_title="Brick Kiln Labeling Tool", layout="wide")

st.title("🧱 Brick Kiln Labeling Tool")
st.markdown("Filter locations by land cover probability and label brick kiln presence")

@st.cache_data
def load_data(csv_file):
    """Load the selected CSV data with error handling"""
    try:
        # Try with error handling for malformed CSV
        df = pd.read_csv(csv_file, on_bad_lines='skip', encoding='utf-8')
        return df
    except Exception as e:
        st.error(f"Error reading CSV {csv_file}: {e}")
        # Try with different parameters
        try:
            df = pd.read_csv(csv_file, on_bad_lines='skip', encoding='latin-1', sep=',')
            st.warning(f"Loaded {csv_file} with fallback encoding")
            return df
        except Exception as e2:
            st.error(f"Failed to load CSV: {e2}")
            return pd.DataFrame()

def get_available_csvs():
    """Get list of available CSV files"""
    csvs = []
    # Check main directory
    for csv in glob.glob("*.csv"):
        csvs.append(csv)
    # Check data directory if it exists
    if os.path.exists("data"):
        for csv in glob.glob("data/*.csv"):
            csvs.append(csv)
    return csvs

def extract_coordinates(filename):
    """Extract lat, lon from filename like '28.6583_76.2294.png'"""
    coords = filename.replace('.png', '').split('_')
    return float(coords[0]), float(coords[1])

def initialize_session_state():
    """Initialize session state variables"""
    if 'filtered_data' not in st.session_state:
        st.session_state.filtered_data = pd.DataFrame()
    if 'current_index' not in st.session_state:
        st.session_state.current_index = 0
    if 'labels' not in st.session_state:
        st.session_state.labels = {}
    if 'labeled_count' not in st.session_state:
        st.session_state.labeled_count = 0

initialize_session_state()

# CSV Selection
st.sidebar.header("📁 Data Selection")
available_csvs = get_available_csvs()

if not available_csvs:
    st.error("No CSV files found! Please add CSV files to the main directory or data/ folder.")
    st.stop()

selected_csv = st.sidebar.selectbox(
    "Choose CSV file:",
    available_csvs,
    index=0
)

# Load selected data
df = load_data(selected_csv)

if df.empty:
    st.error("Failed to load CSV file! Please check the file format.")
    st.stop()

st.sidebar.success(f"Loaded: {selected_csv}")
st.sidebar.write(f"Total locations: {len(df)}")

# Show CSV info for debugging
with st.sidebar.expander("📊 CSV Info"):
    st.write(f"Columns: {list(df.columns)}")
    st.write(f"Shape: {df.shape}")
    if len(df) > 0:
        st.write("First few rows:")
        st.write(df.head(2))

# Sidebar for filtering
st.sidebar.header("🔍 Filtering Options")

# Get all numeric columns (excluding filename)
numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()

# Filtering mode selection
filter_mode = st.sidebar.radio(
    "Filter by:",
    ["Specific Category", "Any Category (Max %)", "All Locations"],
    index=1
)

if filter_mode == "Specific Category":
    # Category selection
    selected_category = st.sidebar.selectbox(
        "Select land cover category:",
        numeric_cols,
        index=4 if 'Built-up' in numeric_cols else 0
    )
    
    # Direct number input for threshold
    threshold = st.sidebar.number_input(
        f"Minimum {selected_category} percentage:",
        min_value=0.0,
        max_value=100.0,
        value=99.90,
        step=0.01,
        format="%.2f"
    )
    
    filter_description = f"{selected_category} >= {threshold}%"

elif filter_mode == "Any Category (Max %)":
    # Direct number input for threshold
    threshold = st.sidebar.number_input(
        "Minimum percentage (any category):",
        min_value=0.0,
        max_value=100.0,
        value=99.90,
        step=0.01,
        format="%.2f"
    )
    
    # Use all categories by default
    categories_to_consider = numeric_cols
    
    filter_description = f"Max % across {len(categories_to_consider)} categories >= {threshold}%"

else:  # All Locations
    threshold = 0.0
    filter_description = "All locations (no filter)"

# Filter button
if st.sidebar.button("Apply Filter", type="primary"):
    if filter_mode == "Specific Category":
        filtered_df = df[df[selected_category] >= threshold].copy()
        filtered_df['max_category'] = selected_category
        filtered_df['max_percentage'] = filtered_df[selected_category]
    elif filter_mode == "Any Category (Max %)":
        # Find max percentage across selected categories for each row
        filtered_df = df.copy()
        filtered_df['max_percentage'] = filtered_df[categories_to_consider].max(axis=1)
        filtered_df['max_category'] = filtered_df[categories_to_consider].idxmax(axis=1)
        filtered_df = filtered_df[filtered_df['max_percentage'] >= threshold]
    else:  # All Locations
        filtered_df = df.copy()
        filtered_df['max_percentage'] = filtered_df[numeric_cols].max(axis=1)
        filtered_df['max_category'] = filtered_df[numeric_cols].idxmax(axis=1)
    
    # Add coordinates
    filtered_df['lat'], filtered_df['lon'] = zip(*filtered_df['filename'].apply(extract_coordinates))
    
    st.session_state.filtered_data = filtered_df
    st.session_state.current_index = 0
    st.session_state.labels = {}
    st.session_state.labeled_count = 0
    st.success(f"Found {len(filtered_df)} locations matching: {filter_description}")

# Main content
if not st.session_state.filtered_data.empty:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📍 Location Map")
        
        current_data = st.session_state.filtered_data.iloc[st.session_state.current_index]
        lat, lon = current_data['lat'], current_data['lon']
        
        # Debug coordinate info
        st.info(f"📍 Location: {current_data['filename']} → Lat: {lat:.4f}, Lon: {lon:.4f}")
        
        # Create folium map with satellite imagery
        m = folium.Map(location=[lat, lon], zoom_start=16)
        
        # Add high-quality satellite tiles
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri World Imagery',
            name='Satellite',
            overlay=False,
            control=True
        ).add_to(m)
        
        # Add marker for location
        folium.Marker(
            [lat, lon],
            popup=f"Image: {current_data['filename']}",
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(m)
        
        # Display map
        st_folium(m, width=700, height=500)
    
    with col2:
        # Current image info - BIG FONT at top
        total_locations = len(st.session_state.filtered_data)
        st.markdown(f"# **IMAGE #{st.session_state.current_index + 1}** / {total_locations}")
        
        # Navigation FIRST (most used)
        col_prev, col_next = st.columns(2)
        with col_prev:
            if st.button("⬅️ **PREV**", disabled=(st.session_state.current_index == 0), use_container_width=True, key="prev"):
                st.session_state.current_index -= 1
                st.rerun()
        with col_next:
            if st.session_state.current_index < total_locations - 1:
                if st.button("➡️ **NEXT**", use_container_width=True, key="next"):
                    st.session_state.current_index += 1
                    st.rerun()
            else:
                st.success("🎉 **DONE!**")
        
        # Kiln tracking - compact
        if 'kiln_images' not in st.session_state:
            st.session_state.kiln_images = ""
        
        kiln_images = st.text_area(
            "🧱 **Kiln image numbers:**",
            value=st.session_state.kiln_images,
            height=80,
            help="e.g: 5, 12, 23"
        )
        
        if kiln_images != st.session_state.kiln_images:
            st.session_state.kiln_images = kiln_images
            st.rerun()
        
        # Current status - compact
        current_image_num = st.session_state.current_index + 1
        kiln_image_numbers = [int(x.strip()) for x in kiln_images.split(',') if x.strip().isdigit()]
        
        if current_image_num in kiln_image_numbers:
            st.success(f"✅ #{current_image_num} HAS KILN")
        else:
            st.info(f"❌ #{current_image_num} NO KILN")
        
        # Export results
        if st.session_state.kiln_images.strip():
            st.write("**💾 Export Results**")
            
            # Create results from image numbers
            kiln_image_numbers = [int(x.strip()) for x in st.session_state.kiln_images.split(',') if x.strip().isdigit()]
            
            results = []
            for idx, row in st.session_state.filtered_data.iterrows():
                image_num = idx + 1
                has_kiln = 1 if image_num in kiln_image_numbers else 0
                
                results.append({
                    'image_number': image_num,
                    'filename': row['filename'],
                    'lat': row['lat'],
                    'lon': row['lon'],
                    'brick_kiln': has_kiln,
                    'dominant_category': row['max_category'],
                    'max_percentage': row['max_percentage']
                })
            
            results_df = pd.DataFrame(results)
            
            # Download button
            csv = results_df.to_csv(index=False)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"brick_kiln_results_{timestamp}.csv"
            
            st.download_button(
                label="💾 Download Results",
                data=csv,
                file_name=filename,
                mime="text/csv",
                type="primary"
            )
            
            # Show summary
            kiln_count = len(kiln_image_numbers)
            total_images = len(st.session_state.filtered_data)
            st.write(f"**Summary:** {kiln_count} kilns found in {total_images} total images")
            st.write(f"**Kiln images:** {', '.join(map(str, sorted(kiln_image_numbers)))}")

else:
    st.info("👆 Please apply a filter to start labeling locations.")
    st.markdown("**Instructions:**")
    st.markdown("1. Select a land cover category from the sidebar")
    st.markdown("2. Set a minimum percentage threshold")
    st.markdown("3. Click 'Apply Filter' to load locations")
    st.markdown("4. Use the map to examine each location")
    st.markdown("5. Label the presence or absence of brick kilns")
    st.markdown("6. Export your results when finished")