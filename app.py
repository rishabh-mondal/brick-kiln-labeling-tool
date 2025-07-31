import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
from datetime import datetime

st.set_page_config(page_title="Brick Kiln Labeling Tool", layout="wide")

st.title("🧱 Brick Kiln Labeling Tool")
st.markdown("Filter locations by land cover probability and label brick kiln presence")

@st.cache_data
def load_data():
    """Load the CSV data"""
    return pd.read_csv("haryana_land_cover_distribution.csv")

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

# Load data
df = load_data()

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
    
    # Threshold slider
    threshold = st.sidebar.slider(
        f"Minimum {selected_category} percentage:",
        min_value=0.0,
        max_value=100.0,
        value=10.0,
        step=0.1
    )
    
    filter_description = f"{selected_category} >= {threshold}%"

elif filter_mode == "Any Category (Max %)":
    # Threshold for maximum percentage across all categories
    threshold = st.sidebar.slider(
        "Minimum percentage (any category):",
        min_value=0.0,
        max_value=100.0,
        value=50.0,
        step=0.1
    )
    
    # Show which categories to consider
    categories_to_consider = st.sidebar.multiselect(
        "Consider these categories:",
        numeric_cols,
        default=numeric_cols
    )
    
    if not categories_to_consider:
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
        
        # Create map centered on current location with high-res satellite as default
        m = folium.Map(
            location=[lat, lon],
            zoom_start=19,
            tiles=None
        )
        
        # Add multiple high-resolution satellite tile layers
        # Esri World Imagery (very high resolution)
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri World Imagery',
            name='Esri Satellite (Default)',
            overlay=False,
            control=True
        ).add_to(m)
        
        # Google Satellite (high resolution)
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
            attr='Google',
            name='Google Satellite',
            overlay=False,
            control=True
        ).add_to(m)
        
        # Bing Satellite (alternative high-res option)
        folium.TileLayer(
            tiles='https://ecn.t3.tiles.virtualearth.net/tiles/a{q}.jpeg?g=1',
            attr='Microsoft Bing',
            name='Bing Satellite',
            overlay=False,
            control=True,
            subdomains='0123'
        ).add_to(m)
        
        # OpenStreetMap for reference
        folium.TileLayer(
            tiles='OpenStreetMap',
            name='OpenStreetMap',
            overlay=False,
            control=True
        ).add_to(m)
        
        # Add marker for current location
        popup_text = f"Location: {current_data['filename']}<br>"
        popup_text += f"Max Category: {current_data['max_category']}<br>"
        popup_text += f"Max Percentage: {current_data['max_percentage']:.2f}%"
        
        folium.Marker(
            [lat, lon],
            popup=popup_text,
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(m)
        
        folium.LayerControl().add_to(m)
        
        # Display map
        st_folium(m, width=700, height=500)
    
    with col2:
        st.subheader("🏷️ Labeling Interface")
        
        # Progress info
        total_locations = len(st.session_state.filtered_data)
        progress = (st.session_state.current_index + 1) / total_locations
        st.progress(progress)
        st.write(f"Location {st.session_state.current_index + 1} of {total_locations}")
        st.write(f"Labeled: {st.session_state.labeled_count}")
        
        # Current location info
        st.write("**Current Location:**")
        st.write(f"File: `{current_data['filename']}`")
        st.write(f"Coordinates: {lat:.4f}, {lon:.4f}")
        st.write(f"Dominant Category: {current_data['max_category']}")
        st.write(f"Max Percentage: {current_data['max_percentage']:.2f}%")
        
        st.markdown("---")
        
        # Labeling buttons
        st.write("**Is there a brick kiln visible at this location?**")
        
        col_yes, col_no = st.columns(2)
        
        with col_yes:
            if st.button("✅ YES", type="primary", use_container_width=True):
                st.session_state.labels[current_data['filename']] = 1
                if st.session_state.current_index not in [i for i, f in enumerate(st.session_state.filtered_data['filename']) if f in st.session_state.labels]:
                    st.session_state.labeled_count += 1
                if st.session_state.current_index < total_locations - 1:
                    st.session_state.current_index += 1
                st.rerun()
        
        with col_no:
            if st.button("❌ NO", use_container_width=True):
                st.session_state.labels[current_data['filename']] = 0
                if st.session_state.current_index not in [i for i, f in enumerate(st.session_state.filtered_data['filename']) if f in st.session_state.labels]:
                    st.session_state.labeled_count += 1
                if st.session_state.current_index < total_locations - 1:
                    st.session_state.current_index += 1
                st.rerun()
        
        st.markdown("---")
        
        # Navigation
        col_prev, col_next = st.columns(2)
        
        with col_prev:
            if st.button("⬅️ Previous", disabled=(st.session_state.current_index == 0)):
                st.session_state.current_index -= 1
                st.rerun()
        
        with col_next:
            if st.button("➡️ Next", disabled=(st.session_state.current_index >= total_locations - 1)):
                st.session_state.current_index += 1
                st.rerun()
        
        # Skip button
        if st.button("⏭️ Skip", use_container_width=True):
            if st.session_state.current_index < total_locations - 1:
                st.session_state.current_index += 1
                st.rerun()
        
        st.markdown("---")
        
        # Export results
        if st.session_state.labels:
            st.write("**Export Labels**")
            
            # Create results DataFrame
            results = []
            for filename, label in st.session_state.labels.items():
                row_data = st.session_state.filtered_data[st.session_state.filtered_data['filename'] == filename].iloc[0]
                results.append({
                    'filename': filename,
                    'lat': row_data['lat'],
                    'lon': row_data['lon'],
                    'brick_kiln': label,
                    'dominant_category': row_data['max_category'],
                    'max_percentage': row_data['max_percentage']
                })
            
            results_df = pd.DataFrame(results)
            
            # Download button
            csv = results_df.to_csv(index=False)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"brick_kiln_labels_{timestamp}.csv"
            
            st.download_button(
                label="💾 Download Labels",
                data=csv,
                file_name=filename,
                mime="text/csv",
                type="primary"
            )
            
            # Show summary
            kiln_count = sum(st.session_state.labels.values())
            total_labeled = len(st.session_state.labels)
            st.write(f"**Summary:** {kiln_count} kilns found in {total_labeled} labeled locations")

else:
    st.info("👆 Please apply a filter to start labeling locations.")
    st.markdown("**Instructions:**")
    st.markdown("1. Select a land cover category from the sidebar")
    st.markdown("2. Set a minimum percentage threshold")
    st.markdown("3. Click 'Apply Filter' to load locations")
    st.markdown("4. Use the map to examine each location")
    st.markdown("5. Label the presence or absence of brick kilns")
    st.markdown("6. Export your results when finished")