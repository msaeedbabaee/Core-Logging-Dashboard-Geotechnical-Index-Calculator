
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

# ==========================================
# 1. CORE LOGGING COMPUTATION FUNCTIONS
# ==========================================


def calculate_core_indices(
    run_length: float, pieces_df: pd.DataFrame
) -> dict:
    """Calculates RQD, TCR, SCR, and Fracture Frequency (FF/m) based on ISRM standards.

    Parameters:
    - run_length: Total length of the core run (m)
    - pieces_df: DataFrame containing piece lengths (cm), piece types, and fracture origins
    """
    if run_length <= 0 or pieces_df.empty:
        return {"RQD": 0.0, "TCR": 0.0, "SCR": 0.0, "FF_m": 0.0}

    # Convert run length to cm for consistent units
    run_length_cm = run_length * 100.0

    # 1. Total Core Recovery (TCR): Sum of all recovered pieces / Run Length
    total_recovered_length = pieces_df["length_cm"].sum()
    tcr = (total_recovered_length / run_length_cm) * 100.0

    # 2. Solid Core Recovery (SCR): Sum of solid full-diameter pieces / Run Length
    solid_pieces = pieces_df[pieces_df["is_solid"] == True]
    solid_recovered_length = solid_pieces["length_cm"].sum()
    scr = (solid_recovered_length / run_length_cm) * 100.0

    # 3. Rock Quality Designation (RQD): Merging pieces across mechanical fractures
    # Mechanical breaks (drilling-induced) are ignored by combining adjacent pieces.
    merged_pieces = []
    current_length = 0.0

    for idx, row in pieces_df.iterrows():
        current_length += row["length_cm"]
        # If the fracture at the end of the piece is natural (or it's the last piece), finalize piece length
        if row["fracture_type"] == "Natural":
            merged_pieces.append(current_length)
            current_length = 0.0

    if current_length > 0.0:
        merged_pieces.append(current_length)

    # Sum only merged intact pieces >= 10 cm
    rqd_length = sum(length for length in merged_pieces if length >= 10.0)
    rqd = (rqd_length / run_length_cm) * 100.0

    # 4. Fracture Frequency (FF/m): Count of natural fractures per meter
    natural_fractures_count = len(
        pieces_df[pieces_df["fracture_type"] == "Natural"]
    )
    ff_m = natural_fractures_count / run_length

    return {
        "RQD": min(float(rqd), 100.0),
        "TCR": min(float(tcr), 100.0),
        "SCR": min(float(scr), 100.0),
        "FF_m": float(ff_m),
    }


def get_rqd_classification(rqd: float) -> tuple:
    """Returns rock quality description and color according to Deere (1963)."""
    if rqd < 25.0:
        return "Very Poor", "#ff4d4d"
    elif rqd < 50.0:
        return "Poor", "#ffa64d"
    elif rqd < 75.0:
        return "Fair", "#ffff4d"
    elif rqd < 90.0:
        return "Good", "#85e085"
    else:
        return "Excellent", "#33cc33"


def plot_core_log(run_length: float, pieces_df: pd.DataFrame):
    """Draws a visual representation of the core barrel with color-coded piece classifications."""
    fig, ax = plt.subplots(figsize=(10, 2.5))

    run_length_cm = run_length * 100.0
    ax.set_xlim(0, run_length_cm)
    ax.set_ylim(0, 1)

    current_pos = 0.0

    for idx, row in pieces_df.iterrows():
        length = row["length_cm"]
        frac_type = row["fracture_type"]

        # Color scheme based on classification
        if frac_type == "Mechanical":
            color = "#ff9999"  # Light red for mechanical / drilling breaks
        elif length >= 10.0:
            color = "#66b3ff"  # Blue for valid RQD pieces (>= 10 cm)
        else:
            color = "#ffcc99"  # Orange for short natural pieces (< 10 cm)

        # Draw core piece rectangle
        rect = patches.Rectangle(
            (current_pos, 0.2),
            length,
            0.6,
            linewidth=1,
            edgecolor="black",
            facecolor=color,
        )
        ax.add_patch(rect)

        # Label piece length if wide enough
        if length > 4:
            ax.text(
                current_pos + length / 2.0,
                0.5,
                f"{length:.0f}cm",
                ha="center",
                va="center",
                fontsize=8,
                fontweight="bold",
            )

        current_pos += length

    # Draw core barrel boundary
    barrel = patches.Rectangle(
        (0, 0.2),
        run_length_cm,
        0.6,
        linewidth=2,
        edgecolor="black",
        facecolor="none",
    )
    ax.add_patch(barrel)

    ax.set_xlabel("Core Run Distance (cm)", fontsize=10)
    ax.set_yticks([])
    ax.set_title("Visual Core Barrel Log", fontsize=11, fontweight="bold")
    ax.grid(True, axis="x", linestyle="--", alpha=0.5)

    st.pyplot(fig)


# ==========================================
# 2. STREAMLIT USER INTERFACE
# ==========================================

st.set_page_config(
    page_title="Core Logging & RQD Dashboard", page_icon="🪵", layout="wide"
)

st.title("🪵 Core Logging & Geotechnical Indices Dashboard")
st.write(
    "Digital interface for logging core runs and calculating **RQD**, **TCR**, **SCR**, and **Fracture Frequency ($FF/m$)** per ISRM standards."
)

st.sidebar.header("📋 Core Run Metadata")
borehole_id = st.sidebar.text_input("Borehole ID", value="BH-01")
from_depth = st.sidebar.number_input(
    "From Depth (m)", min_value=0.0, value=12.0, step=0.5
)
to_depth = st.sidebar.number_input(
    "To Depth (m)", min_value=0.0, value=13.5, step=0.5
)

run_length = to_depth - from_depth
st.sidebar.info(
    f"**Total Run Length:** `{run_length:.2f} m` ({run_length * 100:.0f} cm)"
)

# Default piece logging dataset
if "pieces_data" not in st.session_state:
    st.session_state.pieces_data = pd.DataFrame(
        [
            {
                "Piece ID": 1,
                "length_cm": 25.0,
                "is_solid": True,
                "fracture_type": "Natural",
            },
            {
                "Piece ID": 2,
                "length_cm": 8.0,
                "is_solid": True,
                "fracture_type": "Mechanical",
            },
            {
                "Piece ID": 3,
                "length_cm": 15.0,
                "is_solid": True,
                "fracture_type": "Natural",
            },
            {
                "Piece ID": 4,
                "length_cm": 30.0,
                "is_solid": True,
                "fracture_type": "Natural",
            },
            {
                "Piece ID": 5,
                "length_cm": 12.0,
                "is_solid": False,
                "fracture_type": "Natural",
            },
            {
                "Piece ID": 6,
                "length_cm": 5.0,
                "is_solid": False,
                "fracture_type": "Natural",
            },
        ]
    )

st.subheader("1. Core Piece Logging Table")
st.write(
    "Record individual recovered pieces. Specify mechanical fractures (drilling-induced) to combine them during RQD evaluation:"
)

edited_df = st.data_editor(
    st.session_state.pieces_data,
    num_rows="dynamic",
    column_config={
        "Piece ID": st.column_config.NumberColumn("Piece #", disabled=True),
        "length_cm": st.column_config.NumberColumn(
            "Length (cm)",
            min_value=0.0,
            max_value=200.0,
            step=1.0,
            required=True,
        ),
        "is_solid": st.column_config.CheckboxColumn(
            "Solid Core (Full Diameter)?", default=True
        ),
        "fracture_type": st.column_config.SelectboxColumn(
            "Fracture at End of Piece",
            options=["Natural", "Mechanical"],
            default="Natural",
            help="Mechanical breaks are ignored in RQD calculations by recombining adjacent pieces.",
        ),
    },
    use_container_width=True,
)

# Compute Geotechnical Indices
indices = calculate_core_indices(run_length, edited_df)
quality_desc, quality_color = get_rqd_classification(indices["RQD"])

st.markdown("---")
st.subheader("📊 Calculated Geotechnical Indices")

m1, m2, m3, m4 = st.columns(4)
m1.metric("RQD (Rock Quality)", f"{indices['RQD']:.1f} %")
m2.metric("TCR (Total Recovery)", f"{indices['TCR']:.1f} %")
m3.metric("SCR (Solid Recovery)", f"{indices['SCR']:.1f} %")
m4.metric("FF/m (Fracture Frequency)", f"{indices['FF_m']:.2f} /m")

st.markdown(
    f"**Rock Quality Classification (Deere, 1963):** "
    f"<span style='color:{quality_color}; font-weight:bold; font-size:18px;'>{quality_desc}</span>",
    unsafe_allow_html=True,
)

st.markdown("---")
st.subheader("🎨 Core Barrel Visualization")
plot_core_log(run_length, edited_df)

```
