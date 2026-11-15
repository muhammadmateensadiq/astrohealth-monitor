# AstroHealth Monitor
*Protecting the people who explore beyond Earth.*

> **Research and educational prototype.** Not a clinically validated diagnostic tool. It does not diagnose, treat or predict any disease. All warning thresholds are illustrative.

## What it does
- Shows an astronaut health dashboard for 5 spaceflight challenges: muscle and bone, cardiovascular, sleep, radiation, psychological stress
- Lets you enter sample health measurements
- Shows trends for each astronaut and change from their own pre-flight baseline
- Gives color-coded warnings (green, yellow, red) using lab reference ranges and clearly explained illustrative thresholds
- Gives educational recommendations and prevention tips


## NASA data used
NASA Open Science Data Repository (OSDR), Inspiration4:
- OSD-569: Complete Blood Count
- OSD-575: Comprehensive Metabolic Panel, immune and cardiovascular panels

4 astronauts x 7 timepoints = 28 samples.

## Key findings
- Right after return (R+1), inflammation and immune markers shifted in the same direction in all 4 astronauts (IL-6 about +90%, MCP-1 about +97%, monocytes about +26%, white blood cells about -15%).
- A leave-one-astronaut-out model separated post-return from pre-flight samples better than chance (balanced accuracy 0.83, AUC 0.96, permutation p = 0.025). This is a small-sample pattern, not a predictor.

## How it works
1. Notebook (`notebook/`) cleans and merges the NASA data, compares each astronaut with their own baseline, runs the model and exports 3 small files.
2. The Streamlit app (`app.py`) reads those files and shows the dashboard.

## Run locally
```
pip install -r requirements.txt
streamlit run app.py
```

## Limitations
- Only 4 astronauts and 28 samples, from a short (about 3 day) commercial mission
- Warning thresholds for sleep, heart rate, radiation, stress, bone and muscle are illustrative
- The source data contains two different lab reference sets
- One suspect platelet value was replaced; CRP was converted from pg/mL to mg/L
- Not clinically validated

Built for NASA Space Apps Challenge 2026.