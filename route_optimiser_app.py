import streamlit as st
import pandas as pd
import numpy as np
from streamlit_sortables import sort_items

# -------------------------
# Helper Functions
# -------------------------
def parse_house_number(address):
    import re
    match = re.search(r'(\d+)', str(address))
    return int(match.group(1)) if match else np.nan

def label_route_chunk(row):
    number = parse_house_number(row['Address'])
    if pd.isna(number):
        return f"{row['Street']} (Unknown)"
    return f"{row['Street']} (Odd)" if number % 2 == 1 else f"{row['Street']} (Even)"

def assign_route_chunks(df):
    df['Route Chunk'] = df.apply(label_route_chunk, axis=1)
    return df

def sort_addresses_by_chunk(df):
    sorted_df = pd.DataFrame()
    for chunk in df['Route Chunk'].unique():
        chunk_df = df[df['Route Chunk'] == chunk].copy()
        chunk_df['HouseNum'] = chunk_df['Address'].apply(parse_house_number)
        chunk_df = chunk_df.sort_values('HouseNum')
        sorted_df = pd.concat([sorted_df, chunk_df])
    return sorted_df.drop(columns=['HouseNum'])

def assign_route_order(df, ordered_streets):
    df['Street'] = pd.Categorical(df['Street'], categories=ordered_streets, ordered=True)
    df = df.sort_values(['Street'])
    df = assign_route_chunks(df)
    df = sort_addresses_by_chunk(df)
    df = df.reset_index(drop=True)
    df['Route Order'] = df.index + 1
    return df

# -------------------------
# Streamlit App UI
# -------------------------
st.set_page_config(page_title="Route Optimiser", layout="wide")
st.title("🚚 Route Optimiser Tool (HQ Edition)")

st.markdown("""
Upload your electoral register CSV below. The app will:
1. Detect streets and split them into route chunks (odd/even sides)
2. Let you define walking order
3. Sort house numbers within each chunk
4. Assign route numbers
5. Allow assignment of canvassers to each route chunk
6. Export the result to CSV
""")

# -------------------------
# Step 1: Upload Canvasser CSV or Enter Manually
# -------------------------
st.markdown("### 📂 Step 1: Upload or Enter Canvasser Details")
canvasser_data = None
uploaded_canvasser_file = st.file_uploader("Upload Canvasser CSV (with 'Name' and 'Email' columns)", type=["csv"], key="canvasser_upload")

if uploaded_canvasser_file:
    canvasser_data = pd.read_csv(uploaded_canvasser_file)
    if 'Name' in canvasser_data.columns and 'Email' in canvasser_data.columns:
        st.success("Canvasser data uploaded successfully!")
        st.session_state['canvassers'] = canvasser_data.to_dict(orient='records')
    else:
        st.error("CSV must contain 'Name' and 'Email' columns.")
else:
    manual_names = st.text_area("Or enter names manually (comma-separated):", value="Keenan Clough, Damien Smith")
    manual_emails = st.text_area("Enter corresponding emails (comma-separated):", value="keenan@example.com, damien@example.com")
    if st.button("Save Manual Canvassers"):
        names = [n.strip() for n in manual_names.split(',') if n.strip()]
        emails = [e.strip() for e in manual_emails.split(',') if e.strip()]
        if len(names) == len(emails):
            canvasser_data = pd.DataFrame({'Name': names, 'Email': emails})
            st.session_state['canvassers'] = canvasser_data.to_dict(orient='records')
            st.success("Manual canvasser data saved!")
        else:
            st.error("Number of names and emails must match.")

# -------------------------
# Upload and Setup
# -------------------------
uploaded_file = st.file_uploader("Upload Electoral Register CSV", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    if 'Street' not in df.columns or 'Address' not in df.columns:
        st.error("CSV must contain at least 'Street' and 'Address' columns.")
    else:
        streets = sorted(df['Street'].dropna().unique().tolist())
        st.markdown("### 📜 Drag streets to set your walking route:")
        ordered_streets = sort_items(streets, direction="vertical")

        if st.button("Generate Route Plan"):
            df_processed = assign_route_order(df.copy(), ordered_streets)
            st.session_state['route_data'] = df_processed
            st.session_state['assignments'] = {}  # Reset assignments if rerun
            st.success("Route plan generated. Proceed to assignment below.")

# -------------------------
# Assign Canvassers
# -------------------------
if 'route_data' in st.session_state and 'canvassers' in st.session_state:
    df_processed = st.session_state['route_data']
    canvasser_list = [c['Name'] for c in st.session_state['canvassers']]

    st.markdown("### 🏡 Assign Canvassers to Route Chunks")
    chunk_assignments = {}
    for chunk in df_processed['Route Chunk'].unique():
        key = f"assign_{chunk}"
        default = st.session_state['assignments'].get(chunk, "Unassigned")
        options = ["Unassigned"] + canvasser_list
        default_index = options.index(default) if default in options else 0
        selected = st.selectbox(f"Assign for {chunk}", options=options, key=key, index=default_index)
        chunk_assignments[chunk] = selected

    st.session_state['assignments'] = chunk_assignments
    df_processed['Canvasser'] = df_processed['Route Chunk'].map(chunk_assignments)

    st.markdown("### 📂 Final Output")
    st.dataframe(df_processed.head(20))

    if "Unassigned" in chunk_assignments.values():
        st.warning("🚧 Please assign a canvasser to every route chunk before downloading.")
    else:
        st.download_button(
            label="📂 Download Final CSV",
            data=df_processed.to_csv(index=False).encode('utf-8'),
            file_name="Optimised_Route_Plan.csv",
            mime="text/csv"
        )
