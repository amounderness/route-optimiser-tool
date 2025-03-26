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

def get_email_by_name(name, canvassers):
    for person in canvassers:
        if person['Name'] == name:
            return person['Email']
    return ""

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
5. Allow assignment of canvassers (including optional pairing)
6. Add necessary columns and export to CSV for Glide
""")

# -------------------------
# Step 1: Upload Canvasser CSV or Enter Manually
# -------------------------
st.markdown("### 📂 Step 1: Upload or Enter Canvasser Details")
canvasser_data = None
uploaded_canvasser_file = st.file_uploader("Upload Canvasser CSV (with 'Name' and 'Email' columns)", type=["csv"], key="canvasser_upload")

if uploaded_canvasser_file:
    canvasser_data = pd.read_csv(uploaded_canvasser_file)
    canvasser_data.columns = canvasser_data.columns.str.strip().str.lower()
    if 'name' in canvasser_data.columns and 'email' in canvasser_data.columns:
        canvasser_data = canvasser_data.rename(columns={'name': 'Name', 'email': 'Email'})
        st.success("Canvasser data uploaded successfully!")
        st.session_state['canvassers'] = canvasser_data.to_dict(orient='records')
    else:
        st.error("CSV must contain columns labelled 'Name' and 'Email' (case insensitive). Please check your file.")
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
# Step 2: Optional Pairing Setup
# -------------------------
st.markdown("### 👥 Step 2: Are your canvassers working in pairs?")
use_pairs = st.radio("Pair up canvassers for shared routes?", ["No", "Yes"], horizontal=True)

if use_pairs == "Yes" and 'canvassers' in st.session_state:
    canvasser_names = [c['Name'] for c in st.session_state['canvassers']]
    num_pairs = st.number_input("How many pairs do you want to create?", min_value=1, max_value=len(canvasser_names)//2, step=1)
    st.markdown("Organise your canvassers into pairs. List names for each pair:")

    pairs = {}
    for i in range(num_pairs):
        pair_name = f"Pair {i+1}"
        pair_members = st.multiselect(f"{pair_name} Members", options=canvasser_names, key=f"pair_{i+1}")
        pairs[pair_name] = pair_members

    st.session_state['pairs'] = pairs

# -------------------------
# Upload and Setup
# -------------------------
uploaded_file = st.file_uploader("Upload Electoral Register CSV", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    expected_cols = ['Elector Number', 'Full Name', 'Address', 'Street', 'Postcode', 'Polling District', 'Ward Name', 'Constituency Name', 'Elector Type']
    if not all(col in df.columns for col in expected_cols):
        st.error("CSV must contain expected base columns for the electoral register.")
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

    if use_pairs == "Yes" and 'pairs' in st.session_state:
        assignment_options = list(st.session_state['pairs'].keys())
    else:
        assignment_options = [c['Name'] for c in st.session_state['canvassers']]

    st.markdown("### 🏡 Assign Canvassers or Pairs to Route Chunks")
    chunk_assignments = {}
    for chunk in df_processed['Route Chunk'].unique():
        key = f"assign_{chunk}"
        default = st.session_state['assignments'].get(chunk, "Unassigned")
        options = ["Unassigned"] + assignment_options
        default_index = options.index(default) if default in options else 0
        selected = st.selectbox(f"Assign for {chunk}", options=options, key=key, index=default_index)
        chunk_assignments[chunk] = selected

    st.session_state['assignments'] = chunk_assignments

    # Split chunks among individuals if assigned to pairs
    final_names = []
    final_emails = []
    for i, row in df_processed.iterrows():
        assignment = chunk_assignments.get(row['Route Chunk'], "Unassigned")
        if use_pairs == "Yes" and assignment.startswith("Pair"):
            pair_members = st.session_state['pairs'].get(assignment, [])
            if pair_members:
                selected_individual = pair_members[i % len(pair_members)]
                final_names.append(selected_individual)
                final_emails.append(get_email_by_name(selected_individual, st.session_state['canvassers']))
            else:
                final_names.append("")
                final_emails.append("")
        else:
            final_names.append(assignment if assignment != "Unassigned" else "")
            final_emails.append(get_email_by_name(assignment, st.session_state['canvassers']))

    df_processed['Canvasser Name'] = final_names
    df_processed['Canvasser Email'] = final_emails

    # Add Glide-compatible fields
    df_processed['Voter Intention'] = ""
    df_processed['Contacted?'] = ""
    df_processed['Date Contacted'] = ""
    df_processed['GOTV?'] = ""
    df_processed['Notes'] = ""

    output_columns = expected_cols + ['Route Chunk', 'Route Order', 'Canvasser Name', 'Canvasser Email', 'Voter Intention', 'Contacted?', 'Date Contacted', 'GOTV?', 'Notes']
    df_processed = df_processed[output_columns]

    st.markdown("### 📂 Final Output")
    st.dataframe(df_processed.head(20))

    if "Unassigned" in chunk_assignments.values():
        st.warning("🚧 Please assign a canvasser or pair to every route chunk before downloading.")
    else:
        st.download_button(
            label="📂 Download Final CSV",
            data=df_processed.to_csv(index=False).encode('utf-8'),
            file_name="Optimised_Route_Plan.csv",
            mime="text/csv"
        )
