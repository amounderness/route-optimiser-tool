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

uploaded_file = st.file_uploader("Upload Electoral Register CSV", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    if 'Street' not in df.columns or 'Address' not in df.columns:
        st.error("CSV must contain at least 'Street' and 'Address' columns.")
    else:
        st.success("File uploaded successfully!")

        streets = sorted(df['Street'].dropna().unique().tolist())

        st.markdown("### 📜 Drag streets to set your walking route:")
        ordered_streets = sort_items(streets, direction="vertical")

        canvassers = st.text_input("Enter canvasser names (comma-separated):", value="Keenan, Damien")
        canvasser_list = [c.strip() for c in canvassers.split(',') if c.strip() != ""]

        if st.button("🏋️ Generate Route Plan"):
            df_processed = assign_route_order(df.copy(), ordered_streets)

            # Show route chunks and allow assignment
            unique_chunks = df_processed['Route Chunk'].unique()
            st.markdown("### 🛋️ Assign Canvassers to Route Chunks")
            chunk_assignments = {}
            for chunk in unique_chunks:
                selected = st.selectbox(f"Assign for {chunk}", options=["Unassigned"] + canvasser_list, key=chunk)
                chunk_assignments[chunk] = selected

            df_processed['Canvasser'] = df_processed['Route Chunk'].map(chunk_assignments)

            st.success("Route plan generated with chunk-based assignments!")
            st.dataframe(df_processed.head(20))

            st.download_button(
                label="📂 Download Final CSV",
                data=df_processed.to_csv(index=False).encode('utf-8'),
                file_name="Optimised_Route_Plan.csv",
                mime="text/csv"
            )
