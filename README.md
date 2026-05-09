# PetroDCA Production Analytics

PetroDCA is a Streamlit web application for petroleum production analysis and decline curve forecasting. The main application file, `app.py`, provides a browser-based dashboard for loading well production data, visualizing oil/gas/water trends, fitting Arps decline models, estimating EUR, and exporting engineering results.

This project was developed for the PE 565 Computer Programming for Petroleum Engineers capstone project.

## What `app.py` Does

`app.py` runs the full PetroDCA web app. It includes:

- Multi-well production data upload from Excel or CSV files
- Automatic production data cleaning and unit conversion
- Oil, gas, water, and on-stream production visualization
- Arps decline curve analysis using:
  - Exponential decline
  - Harmonic decline
  - Hyperbolic decline
- Automatic best-model selection using fit quality metrics
- Estimated Ultimate Recovery (EUR) forecasting to an economic limit
- Dashboard-level field summaries and well comparisons
- Interactive Plotly charts with light and dark themes
- Model settings for forecast horizon, economic limit, smoothing, and model selection
- Reports and export tools for CSV and Excel outputs
- AI interaction log page documenting AI-assisted development activity

The app is designed for petroleum engineers who need a practical way to inspect production history, compare well performance, and generate decline-curve forecasts from real production data.

## Main Engineering Workflow

1. Upload production data in Excel or CSV format.
2. Select the field name and wells to analyze from the sidebar.
3. Review production trends in the dashboard and production data pages.
4. Run decline curve analysis for selected wells.
5. Compare Exponential, Harmonic, and Hyperbolic model fits.
6. Estimate EUR using the selected model and economic limit.
7. Review field-level insights and export results.

## Data Format

### Excel Input

The preferred Excel format is one sheet per well, with the sheet name representing the well name.

Expected columns include:

- `Date`
- `Oil Rate`
- `Gas Rate`
- `Water Rate`
- `On-Stream Hrs`

The app is built to handle flexible column naming, but the dataset should contain date and production-rate information for each well.

### CSV Input

CSV files should contain production records with columns similar to:

- `date`
- `oil`
- `gas`
- `water`
- `well`

### Included Dataset

This repository includes `Well Production Data.xlsx`, which can be uploaded through the app sidebar and used as a sample multi-well production dataset.

## Installation

Create and activate a Python virtual environment, then install the required packages:

```bash
pip install -r requirements.txt
```

The main dependencies are:

- Streamlit
- pandas
- NumPy
- SciPy
- Plotly
- scikit-learn
- matplotlib
- python-dotenv

## How to Run the App

From the project folder, run:

```bash
streamlit run app.py
```

Streamlit will start a local web server and provide a browser URL, usually:

```text
http://localhost:8501
```

Open the URL in a web browser to use the dashboard.

## How to Use the App

1. Start the app with `streamlit run app.py`.
2. Use the sidebar to upload an Excel or CSV production dataset.
3. Enter or confirm the field name.
4. Select one or more wells for analysis.
5. Use the navigation buttons in the sidebar:
   - `Dashboard Overview` for field-level KPIs and summary plots
   - `Production Data` for raw and cleaned production records
   - `Decline Curve Analysis (DCA)` for Arps model fitting
   - `EUR Prediction` for recovery forecasts
   - `Model Settings` for decline model and forecast controls
   - `Field Insights` for comparative well analytics
   - `Reports & Export` for downloadable results
   - `AI Interaction Log` for AI-assisted coding documentation
6. Adjust filters, date ranges, production phase, smoothing, and rate type as needed.
7. Export production data, DCA results, or EUR results from the reports page.

## Decline Curve Analysis

The app fits Arps decline models to production-rate history:

- Exponential decline for constant percentage decline behavior
- Harmonic decline for slower long-term decline behavior
- Hyperbolic decline for more general decline behavior using a `b` factor

For each model, the app calculates fit statistics such as R-squared, RMSE, and AIC. EUR is estimated by integrating the selected decline forecast until the economic limit or forecast horizon is reached.

## Project Files

- `app.py` - Main Streamlit web application
- `requirements.txt` - Python package requirements
- `README.md` - Project documentation
- `AI_Interaction_Log.md` - AI-assisted development log, if included
- `Volve_Production_By_Well.xlsx` - Sample production dataset
- `PE 565 Capstone Project 2026.pdf` - Original capstone project brief

## Notes

- The app requires enough positive production history to fit decline models reliably.
- DCA results are engineering estimates and should be reviewed with reservoir, operational, and economic context.
- Forecast accuracy depends on production data quality, selected model assumptions, and the chosen economic limit.
