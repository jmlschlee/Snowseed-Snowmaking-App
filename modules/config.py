"""
modules/config.py
=================

Central configuration for the Snowmaking Planner app.

Everything that a user or maintainer might want to tune lives here:
  * Wet bulb snowmaking quality thresholds (two modes: detailed + strict)
  * Quality colors used across the UI and charts
  * Nozzle calculator constants
  * Pump calculator default efficiencies / safety margin
  * Weather API settings (URLs, forecast length)
  * The Snow State nozzle-number -> orifice-diameter chart

Keeping these in one place means the "science" is transparent and easy to audit.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# App metadata
# ---------------------------------------------------------------------------
APP_NAME = "Snowmaking Planner"
APP_TAGLINE = "Home snowmaking planning, made simple."
APP_VERSION = "1.1.0"

# ---------------------------------------------------------------------------
# Wet bulb quality categories
# ---------------------------------------------------------------------------
# All thresholds are in DEGREES FAHRENHEIT and describe the *upper bound*
# (inclusive) of each category. They are evaluated from coldest -> warmest.
#
# Science note (baked into these numbers):
#   - Snowmaking generally becomes possible around/below 27 F wet bulb.
#   - Snow State language: snowmaking becomes possible below 28 F wet bulb.
#   - 28-29 F wet bulb is borderline and may produce slushy snow.
#   - Efficiency improves dramatically as wet bulb drops into the mid-20s.
#   - Ideal home conditions are roughly below 20 F wet bulb with little wind.

# Rating keys (stable identifiers used by charts / styling)
EXCELLENT = "excellent"
GOOD = "good"
MARGINAL = "marginal"
BORDERLINE = "borderline"
TOO_WARM = "too_warm"
POSSIBLE = "possible"

# Human-friendly labels (match the Snow State Wet Bulb Temperature Chart exactly).
RATING_LABELS = {
    EXCELLENT: "Great Snowmaking",
    GOOD: "Good Snowmaking",
    MARGINAL: "Marginal Snowmaking",
    BORDERLINE: "Borderline",
    TOO_WARM: "Too Warm",
    POSSIBLE: "Possible",
}

# Colors (used in metric cards, badges, and Plotly charts)
RATING_COLORS = {
    EXCELLENT: "#1565C0",   # deep blue  - best / driest powder
    GOOD: "#2E7D32",        # green      - reliably good snow
    MARGINAL: "#F9A825",    # amber      - usable but watch conditions
    BORDERLINE: "#EF6C00",  # orange     - slushy risk
    TOO_WARM: "#C62828",    # red        - don't bother
    POSSIBLE: "#2E7D32",    # green      - strict-mode "possible"
}

# Plain-English explanations shown in the UI.
RATING_EXPLANATIONS = {
    EXCELLENT: (
        "Great snowmaking. Wet bulb is deep enough that a properly set up "
        "home gun should throw dry, powdery snow with good hang time. Snow "
        "State notes dry, powdery snow is often produced in the teens."
    ),
    GOOD: (
        "Good snowmaking. You should make solid, reasonably dry snow. "
        "These are dependable production nights."
    ),
    MARGINAL: (
        "Marginal snowmaking. Snow is possible but tends to be wetter. "
        "Favor lower flow / higher pressure and watch the wind."
    ),
    BORDERLINE: (
        "Borderline / slushy. Right at the edge of what's possible. Even good "
        "equipment may produce wet, slushy snow. Make snow only if you must."
    ),
    TOO_WARM: (
        "Too warm. Wet bulb is above the practical snowmaking limit. "
        "Water will not freeze reliably before hitting the ground."
    ),
    POSSIBLE: (
        "Snowmaking is possible. Wet bulb is at or below the practical limit."
    ),
}

# DETAILED mode thresholds (default).
# Each entry: (rating_key, inclusive_upper_bound_F)
# Evaluated coldest first; the first bound the wet bulb is <= to wins.
DETAILED_THRESHOLDS = [
    (EXCELLENT, 20.0),    # wb <= 20            -> Excellent
    (GOOD, 24.0),         # 20 < wb <= 24       -> Good
    (MARGINAL, 27.0),     # 24 < wb <= 27       -> Marginal
    (BORDERLINE, 28.0),   # 27 < wb <= 28       -> Borderline / slushy
    # anything warmer (wb > 28, i.e. >= 29 rounded) -> Too Warm
]

# STRICT mode thresholds (conservative "can I make snow at all?" view).
STRICT_THRESHOLDS = [
    (POSSIBLE, 27.0),     # wb <= 27            -> Possible
    (BORDERLINE, 28.0),   # 27 < wb <= 28       -> Borderline possible
    # warmer -> Too Warm
]

# Numeric "quality score" for ranking days/nights in charts (higher = better).
RATING_SCORE = {
    EXCELLENT: 5,
    GOOD: 4,
    POSSIBLE: 4,
    MARGINAL: 3,
    BORDERLINE: 2,
    TOO_WARM: 1,
}

# ---------------------------------------------------------------------------
# Forecast / overnight-window settings
# ---------------------------------------------------------------------------
# Overnight snowmaking window, expressed in local hours [start, end).
# Default: 6 PM (18:00) through 9 AM (09:00) next morning.
OVERNIGHT_START_HOUR = 18
OVERNIGHT_END_HOUR = 9

# How many forecast days to request. Open-Meteo supports up to 16 on the
# standard model; 7 is the practical free default. Bump to 14 to test longer.
FORECAST_DAYS = 7
FORECAST_DAYS_MAX = 16

# Wind speed (mph) above which we add a "windy" caution to recommendations.
WIND_CAUTION_MPH = 10.0

# ---------------------------------------------------------------------------
# Nozzle calculator constants
# ---------------------------------------------------------------------------
# Snow State nozzle formula:  NozzleNumber = GPM * sqrt(NOZZLE_K / PSI)
# Validated against the published chart (6 GPM @ 700 PSI -> ~14.35 -> 14).
NOZZLE_K = 4000.0

# Snow State nozzle-number -> orifice diameter (inches).
# Used for combination suggestions and the reference table.
NOZZLE_CHART = {
    1.0: 0.025,
    1.5: 0.030,
    2.0: 0.034,
    2.5: 0.039,
    3.0: 0.043,
    3.5: 0.048,
    4.0: 0.052,
    4.5: 0.055,
    5.0: 0.057,
    5.5: 0.060,
    6.0: 0.062,
    6.5: 0.064,
    7.0: 0.067,
    7.5: 0.070,
    8.0: 0.072,
    8.5: 0.074,
    9.0: 0.076,
    9.5: 0.078,
    10.0: 0.080,
    11.0: 0.083,
    12.0: 0.087,
    13.0: 0.091,
    15.0: 0.096,
    20.0: 0.109,
    25.0: 0.125,
    30.0: 0.141,
    40.0: 0.156,
    50.0: 0.172,
    60.0: 0.188,
}

# Typical snow-gun operating pressure range (PSI) for sanity warnings.
PSI_MIN_TYPICAL = 100.0
PSI_MAX_TYPICAL = 1000.0

# Recommended operating pressure (Snow State: ~700 psi for optimal performance
# across a wide range of temperatures).
RECOMMENDED_PSI = 700.0

# Pressure columns used by the Snow State nozzle FLOW chart (PSI).
FLOW_CHART_PRESSURES = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200]

# ---------------------------------------------------------------------------
# Wet bulb chart grid (matches the Snow State Wet Bulb Temperature Chart axes)
# ---------------------------------------------------------------------------
# Dry-bulb air temperature rows (F): 14..38 inclusive.
WETBULB_CHART_TEMPS_F = list(range(14, 39))
# Relative humidity columns (%): 20..100 step 5.
WETBULB_CHART_RH = list(range(20, 101, 5))

# Standard sea-level atmospheric pressure (kPa) used by the psychrometric
# wet-bulb solver. The Snow State chart is computed at standard pressure.
STANDARD_PRESSURE_KPA = 101.325

# ---------------------------------------------------------------------------
# Pump horsepower calculator defaults
# ---------------------------------------------------------------------------
# Hydraulic HP = (GPM * PSI) / HP_CONSTANT
HP_CONSTANT = 1714.0

DEFAULT_PUMP_EFFICIENCY = 0.60     # 60%
DEFAULT_MOTOR_EFFICIENCY = 0.85    # 85%
DEFAULT_SAFETY_MARGIN = 0.20       # 20%
DEFAULT_PLUMBING_LOSS_PSI = 0.0

# Above this electric HP we warn that the setup looks unrealistic for a home.
HP_SANITY_WARN = 25.0

# ---------------------------------------------------------------------------
# Bucket test defaults
# ---------------------------------------------------------------------------
DEFAULT_BUCKET_GALLONS = 5.0

# ---------------------------------------------------------------------------
# Weather / geocoding API settings (no API key required by default)
# ---------------------------------------------------------------------------
# ZIP -> lat/lon geocoder. Zippopotam.us is free and key-less for US ZIPs.
GEOCODE_PROVIDER = "zippopotam"
ZIPPOPOTAM_URL = "https://api.zippopotam.us/us/{zip}"

# Forecast provider. Open-Meteo is free and key-less.
WEATHER_PROVIDER = "open-meteo"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Network timeout (seconds) for all outbound API calls.
HTTP_TIMEOUT = 20

# Optional: read an API key from Streamlit secrets / env if a future provider
# needs one. Never hard-code keys here.
WEATHER_API_KEY_ENV = "WEATHER_API_KEY"
