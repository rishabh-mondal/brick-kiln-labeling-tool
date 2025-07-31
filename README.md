# 🧱 Brick Kiln Labeling Tool

A Streamlit app for labeling brick kilns in satellite imagery based on land cover data.

## Features

- Filter locations by land cover category and threshold
- High-resolution satellite imagery from multiple sources (Esri, Google, Bing)
- Interactive labeling interface with Yes/No buttons
- Progress tracking and navigation
- Export labeled results to CSV

## Local Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the app:
```bash
streamlit run app.py
```

## Deployment Options

### Streamlit Cloud (Recommended)
1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Deploy with main file: `app.py`

### Hugging Face Spaces
1. Create a new Space at [huggingface.co/spaces](https://huggingface.co/spaces)
2. Choose Streamlit as the SDK
3. Upload all files or connect via Git
4. The app will auto-deploy

## Usage

1. **Filter**: Select a land cover category and set threshold
2. **Navigate**: Use the map and navigation buttons to explore locations
3. **Label**: Mark brick kiln presence/absence for each location
4. **Export**: Download your labeled results as CSV

## Data Format

The app expects a CSV with:
- `filename`: PNG files named as `lat_lon.png` (e.g., `28.6583_76.2294.png`)
- Land cover categories as percentage columns

## Satellite Imagery Sources

- **Esri World Imagery**: Very high resolution (default)
- **Google Satellite**: High resolution alternative
- **Bing Satellite**: Additional high-res option
- **OpenStreetMap**: For reference/context