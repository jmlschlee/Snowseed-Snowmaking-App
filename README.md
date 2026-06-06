# ❄️ Snowseed Snowmaking

A polished, beginner-friendly **Streamlit** app by Snowseed Snowmaking that
helps a home snowmaker plan a session. It answers the questions that actually
matter:

1. **Can I make snow this week?**
2. **Which nights are best?**
3. **What snow quality should I expect** from the forecast wet bulb?
4. **What nozzle number** do I need for my pump flow and target PSI?
5. **What pressure** will my gun run at for a given GPM + nozzle number?
6. **How much pump horsepower** do I need?
7. **What's my home water GPM** (bucket test)?

The app runs **locally on Windows, macOS, and Linux**, and is ready to deploy to
**Streamlit Community Cloud**. All the math lives in small, unit-tested modules.

---

## Why wet bulb?

Snowmaking depends on **wet bulb temperature**, which combines air temperature
*and* humidity - not just the thermometer reading. Dry air evaporatively cools
water below the air temperature, so you can sometimes make snow even when it's
above freezing outside.

Categories and labels match the official **wet bulb temperature chart**:

| Wet bulb (F) | Rating | What to expect |
|---|---|---|
| ≤ 20 | **Great Snowmaking** | Dry, powdery snow, good hang time |
| 21–24 | **Good Snowmaking** | Reliable, reasonably dry snow |
| 25–27 | **Marginal Snowmaking** | Possible but wetter; watch the wind |
| 28 | **Borderline** | Edge of possible; may be slushy |
| ≥ 29 | **Too Warm** | Won't freeze reliably |

A **strict mode** collapses these into *Possible (≤27) / Borderline (28) / Too
warm (≥29)*. Thresholds are configurable in [`modules/config.py`](modules/config.py).

**Accuracy:** wet bulb is computed with the **psychrometric equation** (iterative,
physically correct), which reproduces the standard wet bulb chart to within rounding
(e.g. 14°F at 20% RH → 9°F wet bulb, 30°F at 50% → 25°F). The simpler Stull
approximation is off by 2–3°F in the cold, dry air that matters most for
snowmaking, so it's offered only as an alternative. The app's chart values are
validated against published chart cells in the test suite.

---

## Screenshots

> _Placeholders - add your own screenshots after running locally._

| Forecast | Calculators |
|---|---|
| `assets/screenshot-forecast.png` | `assets/screenshot-nozzle.png` |

---

## The math (transparent and tested)

Every formula is in code comments **and** here. See [`tests/`](tests/) for the
validating examples.

**Nozzle number** (standard snowmaking formula):
```
NozzleNumber = GPM × sqrt(4000 / PSI)
# 6 GPM @ 700 PSI -> 6 × sqrt(4000/700) = 14.35 -> 14
```

**Pressure** (inverse):
```
PSI = 4000 × (GPM / NozzleNumber)^2
# 6 GPM, NN 14 -> 4000 × (6/14)^2 = 735 PSI
```

**Flow** (the flow chart, inverse again):
```
GPM = NozzleNumber × sqrt(PSI / 4000)
# NN 6 @ 700 PSI -> 2.5 GPM ; NN 60 @ 1200 PSI -> 32.9 GPM  (matches chart)
```

**Pump horsepower**:
```
Hydraulic HP = (GPM × TotalPSI) / 1714
Electric HP  = Hydraulic HP / (pump_eff × motor_eff)
Recommended  = Electric HP × (1 + safety_margin)
# 6 GPM @ 700 PSI -> 2.45 hydraulic -> 4.80 electric (60%/85%) -> +20% = 5.76 HP
```

**Bucket test**:
```
GPM = (BucketGallons × 60) / FillSeconds
# 5 gal in 30 s -> 10 GPM
```

**Wet bulb**:
```
Method P (psychrometric): solve  e_actual = e_s(Tw) - gamma·(T - Tw)  for Tw
                          (default; matches the standard wet bulb chart)
Method A (Stull):         closed-form approximation from temp + RH
Method B (dew point):     Tw = (2/3)·T + (1/3)·Td
```

> ⚠️ **Pressure is theoretical.** Real pressure at your pump/gun differs due to
> hose length, fittings, elevation, and restrictions. **Always measure with a
> gauge.**

---

## Project structure

```
snowseed-snowmaking-app/
├── app.py                       # Streamlit UI (thin; calls modules)
├── modules/
│   ├── config.py                # thresholds, colors, constants, API settings
│   ├── wetbulb.py               # Stull + dew point wet bulb, rating
│   ├── weather.py               # ZIP geocode + Open-Meteo forecast
│   ├── forecast_analysis.py     # group hours -> best overnight windows
│   ├── nozzle_calculator.py     # NN = GPM·sqrt(4000/PSI) + combos
│   ├── pressure_calculator.py   # PSI = 4000·(GPM/NN)^2
│   ├── pump_calculator.py       # hydraulic/electric HP + safety margin
│   ├── bucket_test.py           # GPM = gal·60/sec
│   ├── charts.py                # Plotly charts
│   └── validation.py            # input checks
├── tests/                       # pytest math validation
├── requirements.txt
├── .streamlit/config.toml       # pinned light theme
└── README.md
```

---

## Run locally

Requires **Python 3.9+**.

```bash
# 1. (optional) create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. install dependencies
pip install -r requirements.txt

# 3. run the app
streamlit run app.py
```

Then open the URL Streamlit prints (usually http://localhost:8501).

### Run the tests
```bash
pytest -q
```

---

## Deploy to Streamlit Community Cloud

1. Push this repo to GitHub (see below).
2. Go to <https://share.streamlit.io> and sign in with GitHub.
3. **New app** → pick this repo, branch `main`, main file `app.py`.
4. Deploy. No secrets are required for the default (key-less) data providers.
5. *(Optional)* If you switch to a provider that needs a key, add it under the
   app's **Settings → Secrets** as `WEATHER_API_KEY`.

---

## Configuration & data sources

- **Geocoding:** [Zippopotam.us](https://www.zippopotam.us/) (free, no key).
- **Forecast:** [Open-Meteo](https://open-meteo.com/) (free, no key); 7-day
  default, up to 16 days supported. Swap providers by editing
  [`modules/config.py`](modules/config.py) and
  [`modules/weather.py`](modules/weather.py).
- **No API keys are hard-coded.** Optional keys come from Streamlit secrets or
  the `WEATHER_API_KEY` environment variable.

---

## Safety

Water + electricity + cold is serious. Use GFCI protection and outdoor-rated
cordage, bleed pressure before servicing fittings, and follow your equipment's
ratings and your local water-use rules. This app is a **planning aid**, not a
substitute for measurement and good judgment.

---

## License

MIT - see [`LICENSE`](LICENSE).
