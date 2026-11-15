# AstroHealth Monitor - research & educational prototype
# Run with:  streamlit run app.py
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

HERE = Path(__file__).parent
st.set_page_config(page_title="AstroHealth Monitor", page_icon="🚀", layout="wide")

DISCLAIMER = ("⚠️ **Research and educational prototype.** This is NOT a clinically validated "
              "diagnostic tool. It does not diagnose, treat or predict any disease. All warning "
              "thresholds are illustrative and for learning purposes only.")

# ----------------------------------------------------------------------------- data
@st.cache_data
def load_assets():
    ref = json.loads((HERE / "dashboard_reference.json").read_text(encoding="utf-8"))
    tl = pd.read_csv(HERE / "dashboard_timeline.csv")
    fd = json.loads((HERE / "findings.json").read_text(encoding="utf-8"))
    return ref, tl, fd

try:
    REF, TL, FD = load_assets()
except Exception as e:
    st.error(f"Could not load data files next to app.py: {e}")
    st.stop()

ORDER = FD["timepoints"]
PROFILES = ["Reference set 1", "Reference set 2"]

# ----------------------------------------------------------------------------- rules
AREAS = {
    "Muscle & bone": "Less mechanical load in microgravity can reduce muscle and bone strength.",
    "Cardiovascular": "Fluid shifts and reduced activity change how the heart and blood vessels work.",
    "Sleep & fatigue": "Light/dark cycles, noise and workload disrupt sleep and recovery.",
    "Radiation exposure": "Space radiation is higher than on Earth and is tracked as cumulative dose.",
    "Psychological stress": "Isolation, confinement and workload can affect mood and stress.",
}
AREA_OF = {
    "creatinine_value_milligram_per_deciliter": "Muscle & bone",
    "albumin_value_gram_per_deciliter": "Muscle & bone",
    "alkaline_phosphatase_value_units_per_liter": "Muscle & bone",
    "calcium_value_milligram_per_deciliter": "Muscle & bone",
    "bone_loss_pct": "Muscle & bone", "muscle_change_pct": "Muscle & bone",
    "hemoglobin_value_percent": "Cardiovascular", "hematocrit_value_percent": "Cardiovascular",
    "platelet_count_value_thousand_per_microliter": "Cardiovascular", "resting_hr": "Cardiovascular",
    "sleep_hours": "Sleep & fatigue",
    "radiation_msv": "Radiation exposure",
    "white_blood_cell_count_value_thousand_per_microliter": "Radiation exposure",
    "lymphocytes_value_percent": "Radiation exposure",
    "stress_score": "Psychological stress", "glucose_value_milligram_per_deciliter": "Psychological stress",
    "crp_mg_per_L": "Psychological stress",
}
# ILLUSTRATIVE thresholds for non-blood inputs (NOT medical limits)
RULES = {
    "sleep_hours": {"label": "Sleep (h/night)", "low_watch": 6, "low_attention": 5,
                    "why": "Below 6 h = Watch, below 5 h = Attention."},
    "resting_hr": {"label": "Resting heart rate (bpm)", "low_watch": 50, "low_attention": 40,
                   "high_watch": 100, "high_attention": 120,
                   "why": "Outside 50-100 = Watch; below 40 or above 120 = Attention."},
    "radiation_msv": {"label": "Cumulative radiation dose (mSv)", "high_watch": 300, "high_attention": 480,
                      "why": "Roughly 50% / 80% of an example 600 mSv career-dose reference (illustrative)."},
    "stress_score": {"label": "Self-reported stress (0-10)", "high_watch": 6, "high_attention": 8,
                     "why": "6 or more = Watch, 8 or more = Attention."},
    "bone_loss_pct": {"label": "Bone density loss vs baseline (%)", "high_watch": 5, "high_attention": 10,
                      "why": "5% or more = Watch, 10% or more = Attention."},
    "muscle_change_pct": {"label": "Muscle strength change (%)", "low_watch": -10, "low_attention": -20,
                          "why": "-10% or lower = Watch, -20% or lower = Attention."},
}
RANK = {"Within range": 0, "No reference": 0, "Watch": 1, "Attention": 2}
COLORS = {"Within range": "#d4edda", "No reference": "#e2e3e5", "Watch": "#fff3cd", "Attention": "#f8d7da"}


def classify_range(value, lo, hi):
    if lo is None or hi is None:
        return "No reference"
    if lo <= value <= hi:
        return "Within range"
    dist = (lo - value) if value < lo else (value - hi)
    return "Attention" if dist > 0.25 * (hi - lo) else "Watch"


def classify_rule(value, r):
    if "high_attention" in r and value >= r["high_attention"]:
        return "Attention"
    if "low_attention" in r and value <= r["low_attention"]:
        return "Attention"
    if "high_watch" in r and value >= r["high_watch"]:
        return "Watch"
    if "low_watch" in r and value <= r["low_watch"]:
        return "Watch"
    return "Within range"


def evaluate(entry, profile):
    rows = []
    for col, info in REF.items():
        if col not in entry or entry[col] is None:
            continue
        v = float(entry[col])
        rr = info.get("ranges", {}).get(profile)
        lo, hi = (rr[0], rr[1]) if rr else (None, None)
        status = classify_range(v, lo, hi)
        sd = info["preflight_sd"] if info["preflight_sd"] > 0 else None
        z = (v - info["preflight_mean"]) / sd if sd else None
        note = f"Lab range {lo:g}-{hi:g}" if rr else "No lab range in data"
        if status in ("Within range", "No reference") and z is not None and abs(z) >= 2:
            status = "Watch"
            note += f"; {abs(z):.1f} SD from the pre-flight sample average"
        rows.append({"Area": AREA_OF.get(col, "Other"), "Indicator": f"{info['label']} ({info['unit']})",
                     "Value": v, "Status": status, "How it was judged": note})
    for key, r in RULES.items():
        if key in entry and entry[key] is not None:
            v = float(entry[key])
            rows.append({"Area": AREA_OF[key], "Indicator": r["label"], "Value": v,
                         "Status": classify_rule(v, r), "How it was judged": "Illustrative: " + r["why"]})
    return pd.DataFrame(rows)


def style_status(df):
    def color(v):
        return f"background-color: {COLORS.get(v, '')}"
    s = df.style
    fn = getattr(s, "map", None) or s.applymap
    return fn(color, subset=["Status"])


def area_status(results):
    out = {}
    for area in AREAS:
        sub = results[results["Area"] == area]
        out[area] = "—" if sub.empty else max(sub["Status"], key=lambda s: RANK[s])
    return out


EMOJI = {"Within range": "🟢", "Watch": "🟡", "Attention": "🔴", "No reference": "⚪", "—": "⚫"}

RECS = {
    "Muscle & bone": {
        "what": "Without gravity loading, muscles and bones are used less. Spaceflight research reports measurable muscle and bone loss on long missions.",
        "do": ["Daily resistance exercise (on the ISS, a dedicated resistance device is used).",
               "Weight-bearing style loading and impact exercise where available.",
               "Adequate protein, calcium and vitamin D intake, planned with a nutrition specialist.",
               "Track strength and bone-turnover markers over time against the person's own baseline."]},
    "Cardiovascular": {
        "what": "Body fluids shift toward the head in microgravity and the heart works less against gravity, which can change blood volume and blood-pressure regulation.",
        "do": ["Regular aerobic exercise (treadmill or cycle ergometer).",
               "Hydration and electrolyte planning, especially before return to gravity.",
               "Compression garments and gradual re-adaptation after landing.",
               "Monitor resting heart rate and blood pressure trends, not single readings."]},
    "Sleep & fatigue": {
        "what": "Frequent light/dark changes, noise, workload and a shifted schedule can shorten and fragment sleep, increasing fatigue.",
        "do": ["Keep a consistent sleep schedule and protected sleep time.",
               "Use controlled lighting (bright light in the day, dim and warm light before sleep).",
               "Limit caffeine and screens late in the day.",
               "Track sleep duration and quality; discuss persistent problems with the flight surgeon."]},
    "Radiation exposure": {
        "what": "Space radiation is higher than on Earth. Exposure is tracked as cumulative dose, and agencies set career limits to keep long-term risk low.",
        "do": ["Wear and read personal dosimeters; log cumulative dose.",
               "Use shielded areas of the spacecraft during solar events.",
               "Follow ALARA (As Low As Reasonably Achievable) planning for activities.",
               "Blood-cell counts are only a general indicator, not a dose measurement."]},
    "Psychological stress": {
        "what": "Isolation, confinement, workload and distance from family can affect mood, stress and teamwork.",
        "do": ["Scheduled contact with family and friends.",
               "Regular private psychological support check-ins.",
               "Hobbies, exercise and recreation time; clear workload planning.",
               "Team-building and open communication within the crew."]},
}

# ----------------------------------------------------------------------------- header
st.title("AstroHealth Monitor")
st.caption("Protecting the people who explore beyond Earth.")
st.warning(DISCLAIMER)

tabs = st.tabs(["🏠 Overview", "✍️ Enter measurements", "📈 Trends & indicators",
                "⚠️ Risk indicators", "💡 Recommendations", "🛰️ NASA research & data", "ℹ️ About & limits"])
t_over, t_enter, t_trend, t_risk, t_rec, t_nasa, t_about = tabs

# ----------------------------------------------------------------------------- enter
with t_enter:
    st.subheader("Enter sample health measurements")
    st.write("Defaults are the average **pre-flight** values from the NASA dataset. Change any value, then press **Evaluate**.")
    with st.form("entry_form"):
        profile = st.selectbox("Lab reference set", PROFILES,
                               help="The NASA lab reports use two different sets of reference ranges "
                                    "(for example hemoglobin 13.2-17.1 vs 11.7-15.5 g/dL). Pick one.")
        st.markdown("**Blood measurements**")
        cols = st.columns(3)
        entry = {}
        for i, (col, info) in enumerate(REF.items()):
            with cols[i % 3]:
                entry[col] = st.number_input(f"{info['label']} ({info['unit']})",
                                             value=float(round(info["preflight_mean"], 2)),
                                             format="%.2f", key=f"in_{col}")
        st.markdown("**Other health indicators**")
        c1, c2, c3 = st.columns(3)
        with c1:
            entry["sleep_hours"] = st.number_input("Sleep (hours/night)", 0.0, 24.0, 7.0, 0.5)
            entry["resting_hr"] = st.number_input("Resting heart rate (bpm)", 20.0, 220.0, 65.0, 1.0)
        with c2:
            entry["radiation_msv"] = st.number_input("Cumulative radiation dose (mSv)", 0.0, 2000.0, 0.0, 10.0)
            entry["stress_score"] = st.slider("Self-reported stress (0 = none, 10 = extreme)", 0, 10, 3)
        with c3:
            entry["bone_loss_pct"] = st.number_input("Bone density loss vs baseline (%)", 0.0, 50.0, 0.0, 0.5)
            entry["muscle_change_pct"] = st.number_input("Muscle strength change vs baseline (%)", -80.0, 50.0, 0.0, 1.0)
        submitted = st.form_submit_button("Evaluate")
    if submitted:
        st.session_state["results"] = evaluate(entry, profile)
        st.session_state["entry"] = entry
        st.session_state["profile"] = profile
        st.success("Evaluated. See the **Risk indicators**, **Trends** and **Recommendations** tabs.")
        res = st.session_state["results"]
        st.dataframe(style_status(res), hide_index=True)

RESULTS = st.session_state.get("results")
ENTRY = st.session_state.get("entry", {})
PROFILE = st.session_state.get("profile", PROFILES[0])

# ----------------------------------------------------------------------------- overview
with t_over:
    st.subheader("Astronaut health dashboard")
    st.write("Long missions stress the body in five main ways. After you evaluate measurements, each card shows the "
             "highest illustrative warning level for that area.")
    st_map = area_status(RESULTS) if RESULTS is not None else {a: "—" for a in AREAS}
    for col, (area, text) in zip(st.columns(5), AREAS.items()):
        with col:
            st.markdown(f"### {EMOJI[st_map[area]]} {area}")
            st.caption(text)
            st.write(f"**Status:** {st_map[area]}")
    if RESULTS is None:
        st.info("No measurements evaluated yet. Open **Enter measurements**.")
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Astronauts in dataset", FD["n_crew"])
    m2.metric("Blood samples", FD["n_samples"])
    m3.metric("Measured features", FD["n_features"])
    m4.metric("Timepoints", len(ORDER))
    st.markdown("#### Biggest shifts measured right after return (R+1)")
    top = pd.DataFrame(FD["top_shifted_R1"]).head(10)
    fig, ax = plt.subplots(figsize=(8, 4))
    colors = ["#c0392b" if v > 0 else "#2980b9" for v in top["mean_pct_change"][::-1]]
    ax.barh(top["label"][::-1], top["mean_pct_change"][::-1], color=colors)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_xlabel("Average % change vs each astronaut's own pre-flight baseline")
    st.pyplot(fig)
    plt.close(fig)
    st.caption("Only biomarkers that moved in the same direction in all 4 astronauts are shown. "
               "Small sample: treat as exploratory.")

# ----------------------------------------------------------------------------- trends
with t_trend:
    st.subheader("Health indicators and trends")
    labels = {v["label"]: k for k, v in REF.items()}
    choice = st.selectbox("Biomarker", list(labels.keys()))
    col = labels[choice]
    info = REF[col]
    sub = TL[TL["biomarker"] == col]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for crew, g in sub.groupby("Crew"):
        g = g.set_index("Timepoint").reindex(ORDER)
        ax.plot(ORDER, g["value"].values, marker="o", label=crew)
    rr = info.get("ranges", {}).get(PROFILE)
    if rr:
        ax.axhspan(rr[0], rr[1], color="green", alpha=0.08, label=f"Lab range ({PROFILE})")
    if col in ENTRY:
        ax.axhline(ENTRY[col], color="red", ls="--", label="Your entered value")
    ax.axvline(2.5, color="gray", ls=":")
    ax.text(2.55, ax.get_ylim()[1], " return to Earth", va="top", fontsize=8, color="gray")
    ax.set_ylabel(f"{choice} ({info['unit']})")
    ax.legend(fontsize=8)
    st.pyplot(fig)
    plt.close(fig)
    st.caption("Source: NASA OSDR Inspiration4 blood data (4 astronauts). L = days before launch, R = days after return. "
               "One suspect platelet value (12.9, likely a data-entry error) was replaced by that astronaut's median.")

    st.markdown("#### Change from each astronaut's own pre-flight baseline (average z-score)")
    hm = TL.groupby(["label", "Timepoint"])["z_vs_own_baseline"].mean().unstack("Timepoint")[ORDER]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    im = ax.imshow(hm.values, cmap="coolwarm", vmin=-3, vmax=3, aspect="auto")
    ax.set_xticks(range(len(ORDER)))
    ax.set_xticklabels(ORDER)
    ax.set_yticks(range(len(hm.index)))
    ax.set_yticklabels(hm.index)
    fig.colorbar(im, ax=ax, label="z-score")
    st.pyplot(fig)
    plt.close(fig)
    st.caption("Pre-flight columns are near zero by construction. C-reactive protein varies strongly even before "
               "flight, and the low glucose at R+45 appears in 3 of 4 astronauts (possible sample-handling effect).")

# ----------------------------------------------------------------------------- risk
with t_risk:
    st.subheader("Potential health risk warnings (illustrative)")
    if RESULTS is None:
        st.info("Enter and evaluate measurements first.")
    else:
        stat = area_status(RESULTS)
        for col, (area, _) in zip(st.columns(5), AREAS.items()):
            col.metric(area, f"{EMOJI[stat[area]]} {stat[area]}")
        st.dataframe(style_status(RESULTS), hide_index=True)
        n_att = int((RESULTS["Status"] == "Attention").sum())
        n_w = int((RESULTS["Status"] == "Watch").sum())
        st.write(f"**Summary:** {n_att} indicator(s) at *Attention*, {n_w} at *Watch*. "
                 "These are prompts to review and learn, not medical findings.")
    with st.expander("How the warning levels work (all illustrative)", expanded=True):
        st.markdown(
            "- **Blood markers:** compared with the laboratory reference range printed in the NASA data. "
            "Outside the range = **Watch**; more than 25% of the range width outside = **Attention**.\n"
            "- **Personal-baseline check:** a value 2 or more standard deviations from the average pre-flight "
            "sample is also marked **Watch**, even if inside the range.\n"
            "- **C-reactive protein:** the data has no lab range, so only the baseline check is used.\n"
            "- **Non-blood indicators** use the simple illustrative thresholds below.")
        rules_df = pd.DataFrame([{"Indicator": r["label"], "Rule": r["why"]} for r in RULES.values()])
        st.table(rules_df)

# ----------------------------------------------------------------------------- recommendations
with t_rec:
    st.subheader("Educational recommendations and preventive measures")
    st.caption("General educational information, not medical advice.")
    stat = area_status(RESULTS) if RESULTS is not None else {a: "—" for a in AREAS}
    for area, rec in RECS.items():
        with st.expander(f"{EMOJI[stat[area]]} {area}", expanded=stat[area] in ("Watch", "Attention")):
            st.write(rec["what"])
            st.markdown("**Preventive measures / countermeasures**")
            for item in rec["do"]:
                st.markdown(f"- {item}")

# ----------------------------------------------------------------------------- NASA
with t_nasa:
    st.subheader("NASA research and datasets behind this prototype")
    st.markdown("""
**Datasets used (NASA Open Science Data Repository, OSDR)**

| Dataset | What it contains | Link |
|---|---|---|
| OSD-569 | Complete Blood Count (CBC), Inspiration4 crew | https://osdr.nasa.gov/bio/repo/data/studies/OSD-569 |
| OSD-575 | Comprehensive Metabolic Panel, serum immune and cardiovascular multiplex panels | https://osdr.nasa.gov/bio/repo/data/studies/OSD-575 |

Samples: 4 astronauts x 7 timepoints (92, 44 and 3 days before launch; 1, 45, 82 and 194 days after return).
""")
    st.markdown("#### What this prototype found in the data")
    mdl = FD["model"]
    a, b, c = st.columns(3)
    a.metric("Balanced accuracy", mdl["balanced_accuracy"])
    b.metric("AUC", mdl["auc"])
    c.metric("Permutation p-value", mdl["permutation_p"])
    st.caption("Leave-one-astronaut-out test of whether blood patterns right after return (R+1) differ from pre-flight "
               "patterns. It shows a pattern in this small sample. It is NOT a disease predictor.")
    st.dataframe(pd.DataFrame(FD["top_shifted_R1"]).rename(columns={
        "label": "Biomarker", "mean_pct_change": "Avg % change at R+1", "mean_z": "Avg z-score"}),
        hide_index=True)
    st.markdown("""
**Background research and references**
- NASA Twins Study: Garrett-Bakelman et al., *Science* (2019), https://doi.org/10.1126/science.aau8650
- Inspiration4 multi-omics and medical atlas papers, *Nature* (2024) and related OSDR studies
- NASA Human Research Program: https://www.nasa.gov/hrp/ and the Human Research Roadmap: https://humanresearchroadmap.nasa.gov/
- NASA OSDR portal: https://osdr.nasa.gov/
""")

# ----------------------------------------------------------------------------- about
with t_about:
    st.subheader("About and limitations")
    st.markdown("""
**Purpose:** demonstrate how space-research data can support astronaut wellbeing monitoring on long missions.

**Method:** NASA blood datasets were merged by sample, cleaned, and each astronaut was compared with their own
pre-flight baseline (z-scores). A regularised model with leave-one-astronaut-out validation tested whether the
post-return pattern differs from pre-flight.

**Important limitations**
- Only 4 astronauts and 28 samples on a short (~3 day) commercial mission. Long-duration effects such as bone loss
  are explained from NASA research, not measured here.
- Warning thresholds for sleep, heart rate, radiation, stress, bone and muscle are **illustrative placeholders**.
- The source files list two different lab reference sets, and one astronaut switches between them after flight.
  The measured values are unaffected, but range-based statuses depend on the selected set.
- Possible data issues: one implausible platelet value (replaced), CRP unit conversion (pg/mL to mg/L), and unexplained
  low glucose at R+45.
- This is **not** a clinically validated tool. It does not diagnose or predict disease.
""")