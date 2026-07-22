"""app.py — Prey Lang Forest Change Briefing (Streamlit dashboard).

PURPOSE
-------
An educational portfolio prototype for a Geodata Analyst role at Equitable
Earth.  Shows satellite-mapped tree-cover-loss area within an illustrative
~12,000 ha AOI near Prey Lang Wildlife Sanctuary, Cambodia, for years 2021–2023.

HONESTY STATEMENT
-----------------
* The AOI is illustrative and is NOT a surveyed concession, project boundary,
  or precise footprint of any documented logging event.
* "Tree-cover loss" ≠ satellite-mapped tree-cover loss.  Causes include logging, fire, drought,
  crop clearing, plantations, and mapping artefacts.
* This app does NOT calculate biomass, carbon, CO2e, carbon credits,
  additionality, leakage, permanence, or certification outcomes.
* Data source: Hansen/UMD/Google/USGS/NASA Global Forest Change v1.11
  (2000-2023).  License: CC BY 4.0.  Hansen et al., Science 2013.

RUNNING LOCALLY
---------------
    streamlit run app.py

DEPLOYING TO STREAMLIT COMMUNITY CLOUD
---------------------------------------
See README.md → Deployment section.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import geopandas as gpd
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
import streamlit as st

# ---------------------------------------------------------------------------
# Page config (must be the first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Prey Lang Forest Change Briefing",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT           = Path(__file__).parent
AOI_PATH       = ROOT / "data" / "aoi" / "demo_site.geojson"
LOSSYEAR_PATH  = ROOT / "data" / "raw" / "Hansen_GFC-2023-v1.11_lossyear_20N_100E.tif"
OUTPUT_DIR     = ROOT / "outputs"
CSV_PATH       = OUTPUT_DIR / "yearly_loss_summary.csv"
JSON_PATH      = OUTPUT_DIR / "yearly_loss_summary.json"
CLIPPED_TIF    = OUTPUT_DIR / "clipped_lossyear.tif"
LOSS_MAP_PNG   = OUTPUT_DIR / "loss_map.png"

YEARS      = [2021, 2022, 2023]
UTM_EPSG   = 32648  # UTM zone 48N — correct for Prey Lang (~105.6 °E)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Minimal custom CSS — dark forest-green theme, professional and restrained
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .main { background-color: #0f1f17; }
    .stApp { background-color: #0f1f17; }
    h1, h2, h3 { color: #74c69d !important; }
    p, li, label { color: #d8f3dc; }

    .metric-card {
        background: linear-gradient(135deg, #1b4332, #2d6a4f);
        border: 1px solid #40916c;
        border-radius: 10px;
        padding: 18px;
        text-align: center;
        margin-bottom: 10px;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #f4a261;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #95d5b2;
        margin-top: 4px;
    }
    .warning-box {
        background: #1a1a2e;
        border-left: 4px solid #f4a261;
        border-radius: 6px;
        padding: 14px 18px;
        margin: 14px 0;
    }
    .setup-box {
        background: #0d2b1e;
        border: 1px solid #40916c;
        border-radius: 8px;
        padding: 20px 24px;
        margin: 16px 0;
    }
    .data-note {
        background: #0d2b1e;
        border-left: 4px solid #40916c;
        border-radius: 6px;
        padding: 12px 16px;
        margin: 10px 0;
        font-size: 0.88rem;
        color: #95d5b2;
    }
    [data-testid="stSidebar"] { background-color: #0a1a10 !important; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data-loading helpers
# ---------------------------------------------------------------------------

@st.cache_data
def _load_aoi(path: Path) -> gpd.GeoDataFrame:
    from forest_change.geometry import load_aoi
    return load_aoi(path)


@st.cache_data
def _aoi_area_ha(path: Path) -> float:
    from forest_change.geometry import area_hectares, load_aoi
    return area_hectares(load_aoi(path), utm_epsg=UTM_EPSG)


def _load_loss_data() -> tuple[pd.DataFrame | None, dict | None, str]:
    """Return (df, qa_dict, status).

    status is one of: 'csv', 'computed', 'no_data'.
    """
    qa: dict | None = None

    if CSV_PATH.exists():
        df = pd.read_csv(CSV_PATH)
        if JSON_PATH.exists():
            qa = json.loads(JSON_PATH.read_text(encoding="utf-8")).get("qa")
        return df, qa, "csv"

    if LOSSYEAR_PATH.exists():
        from forest_change.process_loss import run_full_pipeline
        with st.spinner("Processing raster (first run — ~30 s) …"):
            df = run_full_pipeline(
                aoi_path=AOI_PATH,
                lossyear_path=LOSSYEAR_PATH,
                output_dir=OUTPUT_DIR,
                years=YEARS,
                utm_epsg=UTM_EPSG,
            )
        if JSON_PATH.exists():
            qa = json.loads(JSON_PATH.read_text(encoding="utf-8")).get("qa")
        return df, qa, "computed"

    return None, None, "no_data"


# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------

def _bar_chart(df: pd.DataFrame) -> plt.Figure:
    """Dark-themed bar chart of annual tree-cover-loss area."""
    fig, ax = plt.subplots(figsize=(7, 4), facecolor="#0f1f17")
    ax.set_facecolor("#0f1f17")

    years  = df["year"].astype(int)
    values = df["loss_area_ha"]
    colours = ["#f4a261" if v == values.max() else "#40916c" for v in values]

    bars = ax.bar(years, values, color=colours, width=0.6,
                  edgecolor="#1b4332", linewidth=1.2)
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + values.max() * 0.025,
            f"{val:.1f} ha",
            ha="center", va="bottom", color="#f4a261", fontsize=11, fontweight="bold",
        )

    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], color="#95d5b2", fontsize=12)
    ax.set_ylabel("Satellite-mapped tree-cover loss (ha)", color="#95d5b2", fontsize=10)
    ax.set_xlabel("Year", color="#95d5b2", fontsize=10)
    ax.set_title(
        "Annual satellite-mapped tree-cover-loss area\n"
        "Prey Lang AOI · Hansen GFC v1.11 · ~30 m",
        color="#74c69d", fontsize=12, pad=14,
    )
    ax.tick_params(colors="#95d5b2")
    for spine in ax.spines.values():
        spine.set_edgecolor("#2d6a4f")
    ax.grid(axis="y", color="#1b4332", linewidth=0.7, alpha=0.8)
    fig.tight_layout()
    return fig


def _aoi_map(aoi_gdf: gpd.GeoDataFrame) -> plt.Figure:
    """Static AOI boundary map."""
    fig, ax = plt.subplots(figsize=(5, 4), facecolor="#0f1f17")
    ax.set_facecolor("#0f1f17")

    aoi_gdf.boundary.plot(ax=ax, color="#40916c", linewidth=2)
    aoi_gdf.plot(ax=ax, color="#2d6a4f", alpha=0.35)

    b  = aoi_gdf.total_bounds
    mx = (b[2] - b[0]) * 0.15
    my = (b[3] - b[1]) * 0.15
    ax.set_xlim(b[0] - mx, b[2] + mx)
    ax.set_ylim(b[1] - my, b[3] + my)

    ax.set_xlabel("Longitude (°E)", color="#95d5b2", fontsize=9)
    ax.set_ylabel("Latitude (°N)", color="#95d5b2", fontsize=9)
    ax.set_title(
        "Illustrative AOI boundary\n(NOT a surveyed project area)",
        color="#74c69d", fontsize=10,
    )
    ax.tick_params(colors="#95d5b2", labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor("#2d6a4f")
    patch = mpatches.Patch(facecolor="#2d6a4f", edgecolor="#40916c", label="AOI (~12,000 ha)")
    ax.legend(handles=[patch], facecolor="#0f1f17", labelcolor="#95d5b2", fontsize=8)
    fig.tight_layout()
    return fig


def _clipped_loss_map() -> plt.Figure | None:
    """Read the saved clipped GeoTIFF and return a display figure, or None."""
    if not CLIPPED_TIF.exists():
        return None
    try:
        with rasterio.open(CLIPPED_TIF) as src:
            data = src.read(1).astype(float)
            nodata = src.nodata if src.nodata is not None else 255
    except Exception:
        return None

    display = np.where((data == 0) | (data == nodata), np.nan, data)

    fig, ax = plt.subplots(figsize=(5, 4), facecolor="#0f1f17")
    ax.set_facecolor("#0f1f17")

    if not np.isnan(display).all():
        encoded_years = [y - 2000 for y in YEARS]
        im = ax.imshow(
            display, cmap="YlOrRd",
            vmin=min(encoded_years), vmax=max(encoded_years),
            interpolation="none",
        )
        cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.04)
        cbar.set_ticks(encoded_years)
        cbar.set_ticklabels([str(y) for y in YEARS])
        cbar.ax.yaxis.set_tick_params(color="#95d5b2", labelcolor="#95d5b2")
        cbar.set_label("Loss year", color="#95d5b2", fontsize=8)
    else:
        ax.text(0.5, 0.5, "No loss pixels detected",
                transform=ax.transAxes, ha="center", va="center",
                color="#95d5b2", fontsize=11)

    ax.set_title(
        "Clipped loss-year raster\n(AOI extent · 2021–2023)",
        color="#74c69d", fontsize=10,
    )
    ax.tick_params(colors="#95d5b2", labelsize=7)
    for spine in ax.spines.values():
        spine.set_edgecolor("#2d6a4f")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## About")
    st.markdown(
        "**Prey Lang Forest Change Briefing** is an educational portfolio "
        "prototype demonstrating the spatial-screening layer of a forest-carbon "
        "MRV workflow, built for a Geodata Analyst portfolio."
    )
    st.markdown("---")
    st.markdown("**Data source**")
    st.markdown(
        "Hansen / UMD / Google / USGS / NASA  \n"
        "Global Forest Change v1.11 (2000–2023)  \n"
        "Landsat-derived lossyear raster · ~30 m  \n"
        "License: CC BY 4.0"
    )
    st.markdown("---")
    st.markdown("**Limitations**")
    st.markdown(
        "- AOI is illustrative, not a surveyed boundary  \n"
        "- Loss ≠ satellite-mapped tree-cover loss (fire, drought, crops, logging, etc.)  \n"
        "- Pixel counts are a screening signal, not a validated area estimate  \n"
        "- No biomass, carbon, or CO₂e calculated  \n"
        "- Not an Equitable Earth product"
    )

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("Prey Lang Forest Change Briefing")
st.markdown(
    "Satellite-mapped tree-cover-loss screening · Prey Lang Wildlife Sanctuary, Cambodia  \n"
    "Data: Hansen GFC v1.11 (Landsat · ~30 m) · Years: 2021–2023 · "
    "Illustrative AOI (not a surveyed project boundary)"
)

# ---------------------------------------------------------------------------
# AOI summary row — always shown
# ---------------------------------------------------------------------------
try:
    aoi_gdf = _load_aoi(AOI_PATH)
    aoi_ha  = _aoi_area_ha(AOI_PATH)
except Exception as e:
    st.error(f"Could not load AOI: {e}")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
for col, value, label in [
    (c1, f"{aoi_ha:.0f} ha",  "AOI area (illustrative)"),
    (c2, "~30 m",             "Source raster resolution"),
    (c3, "2021–2023",         "Years analysed"),
    (c4, "GFC v1.11",         "Hansen / UMD / GFW"),
]:
    col.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-label">{label}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown("---")

# Scientific-honesty banner
st.markdown("""
<div class="warning-box">
<strong>Scientific honesty notice</strong><br>
The figures below are <em>satellite-mapped tree-cover-loss estimates</em>—a screening
signal, not independently verified ground truth. Possible causes include fire, drought,
crop conversion, logging, and mapping artefacts. This app does
<strong>not</strong> calculate biomass, carbon, CO₂e, or certification outcomes.
The AOI is illustrative and not a surveyed project boundary.
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Loss data
# ---------------------------------------------------------------------------
df_loss, qa_data, data_status = _load_loss_data()

if data_status == "no_data":
    st.markdown("---")
    st.markdown("""
<div class="setup-box">
<h3>Data setup required</h3>

The processing pipeline is ready, but the Hansen GFC lossyear raster has not
been placed at the expected path:

<code>data/raw/Hansen_GFC-2023-v1.11_lossyear_20N_100E.tif</code>

See <a href="data/README.md">data/README.md</a> for full instructions.
Below is the short version.

<br><br>

<strong>Step 1 — Download the Cambodia tile (~600 MB)</strong><br>
Open this URL in your browser, or run:
<pre>curl -L -o data/raw/Hansen_GFC-2023-v1.11_lossyear_20N_100E.tif \\
  "https://storage.googleapis.com/earthenginepartners-hansen/GFC-2023-v1.11/Hansen_GFC-2023-v1.11_lossyear_20N_100E.tif"</pre>

<strong>Step 2 — Re-run the app</strong><br>
<pre>streamlit run app.py</pre>
Processing runs automatically on first load (~30 s) and caches results to
<code>outputs/yearly_loss_summary.csv</code>.
</div>
""", unsafe_allow_html=True)

else:
    # --- Headline metrics ---
    st.markdown("### Annual satellite-mapped tree-cover-loss area")
    total_ha  = df_loss["loss_area_ha"].sum()
    peak_row  = df_loss.loc[df_loss["loss_area_ha"].idxmax()]
    peak_year = int(peak_row["year"])
    peak_ha   = peak_row["loss_area_ha"]
    pct       = total_ha / aoi_ha * 100

    m1, m2, m3 = st.columns(3)
    for col, value, label in [
        (m1, f"{total_ha:.1f} ha", "Total flagged 2021–2023"),
        (m2, f"{peak_ha:.1f} ha",  f"Peak year ({peak_year})"),
        (m3, f"{pct:.1f}%",        "% of AOI flagged (3-yr total)"),
    ]:
        col.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-value">{value}</div>'
            f'<div class="metric-label">{label}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("")

    # --- Bar chart + maps ---
    chart_col, aoi_col, loss_col = st.columns([3, 2, 2])

    with chart_col:
        fig_bar = _bar_chart(df_loss)
        st.pyplot(fig_bar, use_container_width=True)
        plt.close(fig_bar)

    with aoi_col:
        fig_aoi = _aoi_map(aoi_gdf)
        st.pyplot(fig_aoi, use_container_width=True)
        plt.close(fig_aoi)

    with loss_col:
        fig_loss = _clipped_loss_map()
        if fig_loss:
            st.pyplot(fig_loss, use_container_width=True)
            plt.close(fig_loss)
        else:
            st.caption("Clipped loss raster not yet generated.")

    # --- Data table ---
    st.markdown("### Year-by-year breakdown")
    display = df_loss.copy()
    display.columns = ["Year", "Loss pixels (~30 m)", "Loss area (ha)"]
    st.dataframe(display.set_index("Year"), use_container_width=True)

    if data_status == "csv":
        note = f"Results loaded from pre-computed `{CSV_PATH.relative_to(ROOT)}`."
    else:
        note = "Results computed from lossyear raster and cached to `outputs/`."
    st.markdown(f'<div class="data-note">{note}</div>', unsafe_allow_html=True)

    st.download_button(
        label="Download summary CSV",
        data=df_loss.to_csv(index=False).encode("utf-8"),
        file_name="prey_lang_loss_summary.csv",
        mime="text/csv",
    )

# ---------------------------------------------------------------------------
# Methodology, QA, and Limitations — always shown
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown("### Methodology and limitations")

with st.expander("What this pipeline does (step by step)", expanded=False):
    st.markdown("""
1. **Load AOI** — Read `data/aoi/demo_site.geojson` with GeoPandas.  Validate
   geometry: single polygon, WGS84, no self-intersections.
2. **Open lossyear raster** — Hansen GFC v1.11, Landsat-derived, ~30 m,
   covering 2001–2023.  Pixel value = year − 2000 (e.g. 21 → 2021, 0 = no loss).
3. **Align CRS** — Reproject the AOI to the raster's CRS if they differ.
   The raster pixel data is never modified.
4. **Clip to AOI** — Use `rasterio.mask()` to keep only pixels inside the polygon.
5. **Pixel area** — Read from the GeoTIFF affine transform; convert
   degrees → metres via Haversine approximation at the site's latitude.
   Never a hard-coded constant.
6. **Count per year** — For each target year, count pixels where
   `value == year − 2000`, multiply by pixel area, convert m² → hectares.
7. **Write outputs** — CSV, JSON (with QA metadata), clipped GeoTIFF, PNG map.
""")

with st.expander("How this compares to Equitable Earth's real MRV workflow", expanded=False):
    st.markdown("""
| Step | Equitable Earth (real MRV) | This prototype |
|---|---|---|
| Boundary | Surveyed project boundary shapefile | Illustrative GeoJSON box |
| Loss detection | Pixel-level AGB data; ESA WorldCover stratification | Hansen GFC lossyear raster |
| Biomass | Per-pixel above-ground biomass model | **Not calculated** |
| Carbon | AGB × root-to-shoot ratio → carbon → CO₂e | **Not calculated** |
| Uncertainty | Monte Carlo bounds, conservative estimates | **Not calculated** |
| Additionality | Jurisdiction-level baselines | **Not calculated** |
| Verification | Independent third-party audit | **Not performed** |

This prototype implements only the spatial screening step — where did
canopy cover likely change — as a transparent demonstration of
geospatial data-engineering skills.  It is not an Equitable Earth product.
""")

if qa_data:
    with st.expander("Data quality report", expanded=False):
        qa_display = {
            "Analysis timestamp":      qa_data.get("analysis_timestamp", "—"),
            "AOI valid":               str(qa_data.get("aoi_valid", "—")),
            "AOI area (ha)":           qa_data.get("aoi_area_ha", "—"),
            "Source raster exists":    str(qa_data.get("source_raster_exists", "—")),
            "Raster CRS":              qa_data.get("raster_crs", "—"),
            "CRS recognized":          str(qa_data.get("crs_recognized", "—")),
            "Source resolution (deg)": (
                f"{qa_data.get('source_resolution_x_deg', '?')} × "
                f"{qa_data.get('source_resolution_y_deg', '?')}"
            ),
            "Pixel area (m²)":         qa_data.get("pixel_area_m2", "—"),
            "Pixel area (ha)":         qa_data.get("pixel_area_ha", "—"),
            "Clipped valid pixels":    qa_data.get("clipped_valid_pixels", "—"),
            "Nodata %":                f"{qa_data.get('nodata_pct', 0):.2f}%",
            "Observed value range":    str(qa_data.get("observed_lossyear_value_range", "—")),
            "Expected value range":    str(qa_data.get("expected_lossyear_value_range", "—")),
        }
        qa_df = pd.DataFrame(
            list(qa_display.items()), columns=["Check", "Value"]
        ).set_index("Check")
        st.dataframe(qa_df, use_container_width=True)

with st.expander("Known limitations", expanded=False):
    st.markdown("""
- **AOI is illustrative** — not a surveyed project, concession, or property boundary.
- **Loss ≠ satellite-mapped tree-cover loss** — the Hansen product maps any canopy change: fire,
  drought, smallholder rotation, plantations, and selective logging all appear.
- **Cause cannot be determined** from this processing alone.
- **No biomass, carbon, or CO₂e** is calculated at any point.
- **30 m resolution** — clearing events smaller than ~900 m² may be missed;
  mixed pixels near boundaries may be misclassified.
- **No per-pixel uncertainty** — raw pixel counts are not a statistically
  validated area estimate per IPCC or GFW guidance.
- **Seasonality** — cloud cover affects Landsat availability across years,
  influencing detection sensitivity.
- **Not an Equitable Earth product or official methodology implementation.**
""")

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown(
    "<small style='color:#4d8c6f'>"
    "Data: Hansen / UMD / Google / USGS / NASA · CC BY 4.0 · Hansen et al., Science 2013 · "
    "Built with Python, GeoPandas, Rasterio, NumPy, Matplotlib, Streamlit · "
    "Portfolio project — not a certified MRV system"
    "</small>",
    unsafe_allow_html=True,
)
