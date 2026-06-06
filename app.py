"""
app.py - Snowseed Snowmaking
============================

A polished, beginner-friendly Streamlit app for home snowmaking planning.

UI model: a BLOCK DASHBOARD. The landing page shows large clickable tool
cards; selecting one opens that tool (tracked via the ?tool= query param) with
a big centered title and a "Back to dashboard" control. All math lives in
modules/ and is unit-tested in tests/.

Run locally:
    pip install -r requirements.txt
    streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from modules import (
    bucket_test,
    charts,
    config,
    forecast_analysis,
    nozzle_calculator,
    pressure_calculator,
    pump_calculator,
    validation,
    weather,
    wetbulb,
)

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=config.APP_NAME,
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Global styling - larger fonts, bigger emojis, centered titles, smooth cards
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
      /* ---- Layout ---- */
      .block-container {padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1120px;}

      /* ---- Base typography (everything larger) ---- */
      html, body, [data-testid="stAppViewContainer"] {font-size: 18px;}
      .stMarkdown p, .stMarkdown li {font-size: 1.15rem; line-height: 1.6;}
      [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
          font-size: 1.02rem !important; line-height: 1.55;}
      label, .stSelectbox label, .stSlider label, .stNumberInput label,
      .stTextInput label, .stToggle label {
          font-size: 1.08rem !important; font-weight: 600 !important;}

      /* ---- App header (centered) ---- */
      .app-header {text-align: center; margin: .3rem 0 1.4rem 0;}
      .app-header .logo {font-size: 4rem; line-height: 1; display: block;}
      .app-header h1 {font-size: 2.9rem; font-weight: 800; margin: .3rem 0 .1rem 0;}
      .app-header .tagline {font-size: 1.25rem; color: #5b6b7b; margin: 0;}

      /* ---- Tool header (centered, big emoji) ---- */
      .tool-head {text-align: center; margin: .2rem 0 1.6rem 0;}
      .tool-head .tool-emoji {font-size: 3.8rem; line-height: 1; display: block;}
      .tool-head h2 {font-size: 2.3rem; font-weight: 800; margin: .35rem 0 .2rem 0;}
      .tool-head .tool-sub {font-size: 1.18rem; color: #5b6b7b; max-width: 640px;
          margin: 0 auto;}

      /* ---- Dashboard grid of tool blocks ---- */
      .tool-grid {display: grid; grid-template-columns: repeat(3, 1fr);
          gap: 1.3rem; margin-top: .6rem;}
      .tool-card {display: flex; flex-direction: column; align-items: center;
          justify-content: flex-start; text-align: center; text-decoration: none;
          background: #ffffff; border: 1.5px solid #e3e8ef; border-radius: 20px;
          padding: 1.8rem 1.2rem; color: #16222e; transition: all .16s ease;
          box-shadow: 0 1px 3px rgba(16,34,46,.06); min-height: 210px;}
      .tool-card:hover {transform: translateY(-5px); border-color: #1565C0;
          box-shadow: 0 12px 28px rgba(21,101,192,.16);}
      /* Kill Streamlit's default link underline on the cards + children */
      .tool-card, .tool-card:link, .tool-card:visited, .tool-card:hover,
      .tool-card:active, .tool-card * {text-decoration: none !important;}
      .tool-card .emoji {font-size: 3.6rem; line-height: 1; margin-bottom: .6rem;}
      .tool-card .name {font-size: 1.4rem; font-weight: 750; margin-bottom: .4rem;
          color: #16222e;}
      .tool-card .desc {font-size: 1.02rem; color: #5b6b7b; line-height: 1.45;}

      /* ---- Metric cards ---- */
      .metric-card {border-radius: 16px; padding: 1.15rem 1.3rem; color: white;
          box-shadow: 0 1px 4px rgba(0,0,0,.12); height: 100%;}
      .metric-card h3 {margin: 0 0 .25rem 0; font-size: .95rem; font-weight: 700;
          letter-spacing: .03em; text-transform: uppercase; opacity: .92;}
      .metric-card .big {font-size: 2.4rem; font-weight: 800; line-height: 1.05;}
      .metric-card .sub {font-size: .98rem; opacity: .94; margin-top: .15rem;}

      /* ---- Rating badges (category fonts larger) ---- */
      .rating-badge {display: inline-block; padding: .35rem 1rem; border-radius: 999px;
          color: white; font-weight: 700; font-size: 1.08rem;}

      /* ---- Night cards ---- */
      .night-card {border: 1.5px solid #e6ebf1; border-radius: 16px;
          padding: 1.15rem 1.3rem; margin-bottom: .9rem; background: #fff;
          font-size: 1.12rem;}
      .night-card .recommendation {color: #333; font-size: 1.06rem; margin-top: .5rem;
          line-height: 1.55;}

      /* ---- Buttons (larger, smoother) ---- */
      .stButton > button {font-size: 1.12rem; font-weight: 650; padding: .6rem 1.4rem;
          border-radius: 12px;}
      div[data-testid="stExpander"] summary p {font-size: 1.1rem; font-weight: 600;}

      /* ---- Mobile ---- */
      @media (max-width: 820px) {
          .tool-grid {grid-template-columns: 1fr;}
          .app-header h1 {font-size: 2.2rem;}
          .tool-head h2 {font-size: 1.9rem;}
      }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def metric_card(title: str, big: str, sub: str = "", color: str = "#2E7D32") -> str:
    return (
        f'<div class="metric-card" style="background:{color}">'
        f"<h3>{title}</h3>"
        f'<div class="big">{big}</div>'
        f'<div class="sub">{sub}</div>'
        f"</div>"
    )


def show_warnings(warnings):
    for w in warnings:
        st.warning(w)


def tool_header(emoji: str, name: str, subtitle: str):
    st.markdown(
        f'<div class="tool-head"><span class="tool-emoji">{emoji}</span>'
        f"<h2>{name}</h2><p class='tool-sub'>{subtitle}</p></div>",
        unsafe_allow_html=True,
    )


def back_to_dashboard():
    if st.button("⬅  Back to dashboard", key="back"):
        st.query_params.clear()
        st.rerun()


# Tool registry (drives both the dashboard grid and routing).
TOOLS = [
    {
        "key": "forecast", "emoji": "🌡️", "name": "Snowmaking Forecast",
        "desc": "Type your ZIP for a 7-day wet bulb outlook and the best nights.",
        "sub": "Can I make snow this week? Which nights are best?",
    },
    {
        "key": "nozzle", "emoji": "🔩", "name": "Nozzle Calculator",
        "desc": "Enter GPM + PSI to get the total nozzle number you need.",
        "sub": "What nozzle number do I need for my flow and pressure?",
    },
    {
        "key": "pressure", "emoji": "📈", "name": "Pressure Calculator",
        "desc": "Enter GPM + nozzle number to estimate operating pressure.",
        "sub": "What pressure will my gun run at?",
    },
    {
        "key": "pump", "emoji": "⚡", "name": "Pump Horsepower",
        "desc": "Size the electric motor for your pump setup.",
        "sub": "How much horsepower do I need?",
    },
    {
        "key": "bucket", "emoji": "🪣", "name": "Bucket Test",
        "desc": "Time a bucket fill to find your real water flow (GPM).",
        "sub": "What's my home water supply flow rate?",
    },
    {
        "key": "about", "emoji": "ℹ️", "name": "About & Safety",
        "desc": "How it works, the science, assumptions, and safety notes.",
        "sub": "How this works, what it assumes, and how to stay safe.",
    },
]
TOOL_BY_KEY = {t["key"]: t for t in TOOLS}


# ===========================================================================
# Dashboard (landing)
# ===========================================================================
def render_dashboard():
    st.markdown(
        f'<div class="app-header"><span class="logo">❄️</span>'
        f"<h1>{config.APP_NAME}</h1>"
        f'<p class="tagline">{config.APP_TAGLINE}</p></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center;font-size:1.2rem;color:#5b6b7b;margin-bottom:1rem;'>"
        "Pick a tool to get started.</p>",
        unsafe_allow_html=True,
    )

    cards = []
    for t in TOOLS:
        cards.append(
            f'<a class="tool-card" href="?tool={t["key"]}" target="_self">'
            f'<span class="emoji">{t["emoji"]}</span>'
            f'<span class="name">{t["name"]}</span>'
            f'<span class="desc">{t["desc"]}</span></a>'
        )
    st.markdown(f'<div class="tool-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


# ===========================================================================
# Tool 1 - Wet Bulb Snowmaking Forecast
# ===========================================================================
def render_forecast():
    t = TOOL_BY_KEY["forecast"]
    tool_header(t["emoji"], t["name"], t["sub"])

    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        zip_code = st.text_input("ZIP code", value="", max_chars=5, placeholder="e.g. 80424")
    with c2:
        days = st.slider("Forecast days", 1, config.FORECAST_DAYS_MAX, config.FORECAST_DAYS)
    with c3:
        method_label = st.selectbox(
            "Wet bulb method",
            ["Psychrometric (most accurate)", "Stull approximation", "Dew point (2/3,1/3)"],
        )
    strict = st.toggle(
        "Strict mode (conservative: only 'possible / borderline / too warm')",
        value=False,
    )
    method = {
        "Psychrometric (most accurate)": "psychrometric",
        "Stull approximation": "stull",
        "Dew point (2/3,1/3)": "dewpoint",
    }[method_label]

    go = st.button("Get snowmaking forecast", type="primary", use_container_width=True)

    if go:
        errs = validation.validate_zip(zip_code)
        if errs:
            for e in errs:
                st.error(e)
        else:
            try:
                with st.spinner("Looking up location and pulling forecast..."):
                    loc = weather.geocode_zip(zip_code)
                    fc = weather.get_forecast(loc, days=days)
                    nights = forecast_analysis.summarize_nights(fc, strict=strict, method=method)
                st.success(
                    f"Forecast for {loc.place_name}, {loc.state} "
                    f"({loc.latitude:.3f}, {loc.longitude:.3f}) - timezone {fc.timezone}."
                )
                if not nights:
                    st.info("No overnight windows found in the returned forecast.")
                else:
                    best = min(nights, key=lambda n: n.min_wet_bulb_f)
                    can = forecast_analysis.can_make_snow_this_week(nights)
                    headline = (
                        "Yes - you have snowmaking windows this week."
                        if can else "Not really - it looks too warm this week."
                    )
                    st.markdown(
                        f"<h3 style='text-align:center'>{headline}</h3>",
                        unsafe_allow_html=True,
                    )

                    m1, m2, m3, m4 = st.columns(4)
                    with m1:
                        st.markdown(metric_card("Best night", best.label,
                                    best.best_time.strftime("around %-I %p"),
                                    wetbulb.rating_color(best.rating)), unsafe_allow_html=True)
                    with m2:
                        st.markdown(metric_card("Lowest wet bulb", f"{best.min_wet_bulb_f:.0f}F",
                                    best.rating_label, wetbulb.rating_color(best.rating)),
                                    unsafe_allow_html=True)
                    with m3:
                        st.markdown(metric_card("Air temp then", f"{best.temp_at_best_f:.0f}F",
                                    (f"{best.humidity_at_best:.0f}% RH"
                                     if best.humidity_at_best is not None else ""), "#455A64"),
                                    unsafe_allow_html=True)
                    with m4:
                        st.markdown(metric_card("Wind then",
                                    (f"{best.wind_at_best:.0f} mph"
                                     if best.wind_at_best is not None else "n/a"),
                                    "calmer is better", "#455A64"), unsafe_allow_html=True)

                    st.markdown("#### Snowmaking outlook by night")
                    st.plotly_chart(charts.night_quality_bar(nights), use_container_width=True)

                    st.markdown("#### Night-by-night detail")
                    for n in nights:
                        color = wetbulb.rating_color(n.rating)
                        st.markdown(
                            f'<div class="night-card">'
                            f'<span class="rating-badge" style="background:{color}">'
                            f"{n.rating_label}</span> &nbsp; "
                            f"<strong>{n.label}</strong> &nbsp; "
                            f"Lowest wet bulb <strong>{n.min_wet_bulb_f:.0f}F</strong> "
                            + (f"&middot; air {n.temp_at_best_f:.0f}F ")
                            + (f"&middot; {n.humidity_at_best:.0f}% RH "
                               if n.humidity_at_best is not None else "")
                            + (f"&middot; wind {n.wind_at_best:.0f} mph"
                               if n.wind_at_best is not None else "")
                            + f'<div class="recommendation">{n.recommendation}</div>'
                            f"</div>", unsafe_allow_html=True,
                        )
                        with st.expander(f"Hourly detail - {n.label}"):
                            st.plotly_chart(charts.hourly_wetbulb_line(n),
                                            use_container_width=True, key=f"hourly-{n.label}")
            except weather.WeatherError as exc:
                st.error(f"Couldn't get the forecast: {exc}")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Unexpected error: {exc}")

    with st.expander("What do the snowmaking ratings mean?"):
        st.write(
            "Snowmaking depends on **wet bulb temperature**, which combines air "
            "temperature and humidity. Drier air lets water evaporatively cool below "
            "the air temperature, so you can make snow even above freezing."
        )
        for key, _bound in config.DETAILED_THRESHOLDS + [(config.TOO_WARM, None)]:
            st.markdown(
                f'<p style="margin:.4rem 0;"><span class="rating-badge" style="background:'
                f'{wetbulb.rating_color(key)}">{wetbulb.rating_label(key)}</span> '
                f"&nbsp; {wetbulb.rating_explanation(key)}</p>",
                unsafe_allow_html=True,
            )

    with st.expander("Wet Bulb Reference Chart"):
        st.caption(
            "Wet bulb (F) for each air temperature and humidity, computed with the "
            "psychrometric method (the physically correct wet bulb). Cells are colored "
            "by snowmaking rating."
        )
        st.plotly_chart(charts.wetbulb_reference_chart(), use_container_width=True)


# ===========================================================================
# Tool 2 - Nozzle Calculator
# ===========================================================================
def render_nozzle():
    t = TOOL_BY_KEY["nozzle"]
    tool_header(t["emoji"], t["name"], t["sub"])

    c1, c2 = st.columns(2)
    with c1:
        gpm = st.number_input("Water flow (GPM)", min_value=0.1, value=6.0, step=0.5, key="nz_gpm")
    with c2:
        psi = st.number_input("Desired pressure (PSI)", min_value=1.0, value=700.0, step=25.0, key="nz_psi")

    res = nozzle_calculator.calculate(gpm, psi)
    m1, m2 = st.columns(2)
    with m1:
        st.markdown(metric_card("Required nozzle number", f"{res.nozzle_number:.2f}",
                    "exact, unrounded", "#1565C0"), unsafe_allow_html=True)
    with m2:
        orifice = nozzle_calculator.orifice_for(res.nozzle_number_rounded)
        sub = f"{orifice:.3f} in orifice" if orifice else "nearest chart size"
        st.markdown(metric_card("Suggested chart nozzle", f"#{res.nozzle_number_rounded:g}",
                    sub, "#2E7D32"), unsafe_allow_html=True)

    show_warnings(res.warnings)

    st.markdown("#### Suggested nozzle combinations")
    st.caption("Nozzle numbers add up, so you can split the target across several nozzles.")
    if res.combos:
        for combo in res.combos:
            pretty = " + ".join(f"#{c:g}" for c in combo)
            st.write(f"- {pretty}  (total #{sum(combo):g})")
    else:
        st.write("No tidy combinations near that number - use the closest single size.")

    with st.expander("Show formula"):
        st.latex(r"\text{Nozzle Number} = \text{GPM} \times \sqrt{\dfrac{4000}{\text{PSI}}}")
        st.write("Example: 6 GPM at 700 PSI -> 6 x sqrt(4000/700) = **14.35** -> nozzle **14**.")

    with st.expander("Nozzle number -> orifice diameter chart"):
        st.table(nozzle_calculator.chart_rows())

    with st.expander("Nozzle Flow Chart (GPM by nozzle # and PSI)"):
        st.caption("Expected flow (GPM) for a given total nozzle number at each pressure "
                   "(gpm = nozzle# x sqrt(PSI / 4000)).")
        st.dataframe(nozzle_calculator.flow_chart_rows(), use_container_width=True, hide_index=True)


# ===========================================================================
# Tool 3 - Pressure Calculator
# ===========================================================================
def render_pressure():
    t = TOOL_BY_KEY["pressure"]
    tool_header(t["emoji"], t["name"], t["sub"])

    c1, c2 = st.columns(2)
    with c1:
        gpm_p = st.number_input("Water flow (GPM)", min_value=0.1, value=6.0, step=0.5, key="pr_gpm")
    with c2:
        nn = st.number_input("Total nozzle number", min_value=0.1, value=14.0, step=0.5, key="pr_nn")

    pres = pressure_calculator.calculate(gpm_p, nn)
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown(metric_card("Estimated pressure", f"{pres.psi:.0f} PSI",
                    "theoretical - measure to confirm", "#1565C0"), unsafe_allow_html=True)
    show_warnings(pres.warnings)

    with st.expander("Show formula"):
        st.latex(r"\text{PSI} = 4000 \times \left(\dfrac{\text{GPM}}{\text{Nozzle Number}}\right)^2")
        st.write("Example: 6 GPM, nozzle 14 -> 4000 x (6/14)^2 = **735 PSI**.")


# ===========================================================================
# Tool 4 - Pump Horsepower
# ===========================================================================
def render_pump():
    t = TOOL_BY_KEY["pump"]
    tool_header(t["emoji"], t["name"], t["sub"])

    c1, c2, c3 = st.columns(3)
    with c1:
        gpm_h = st.number_input("Water flow (GPM)", min_value=0.1, value=6.0, step=0.5, key="hp_gpm")
        plumbing = st.number_input("Plumbing loss (PSI, optional)", min_value=0.0, value=0.0, step=10.0)
    with c2:
        psi_h = st.number_input("Desired gun pressure (PSI)", min_value=1.0, value=700.0, step=25.0, key="hp_psi")
        safety = st.slider("Safety margin", 0.0, 0.5, config.DEFAULT_SAFETY_MARGIN, 0.05)
    with c3:
        pump_eff = st.slider("Pump efficiency", 0.30, 0.90, config.DEFAULT_PUMP_EFFICIENCY, 0.05)
        motor_eff = st.slider("Motor efficiency", 0.50, 0.98, config.DEFAULT_MOTOR_EFFICIENCY, 0.01)

    pr = pump_calculator.calculate(gpm=gpm_h, desired_psi=psi_h, pump_efficiency=pump_eff,
                                   motor_efficiency=motor_eff, plumbing_loss_psi=plumbing,
                                   safety_margin=safety)
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(metric_card("Hydraulic HP", f"{pr.hydraulic_hp:.2f}",
                    f"at {pr.total_psi:.0f} PSI total", "#455A64"), unsafe_allow_html=True)
    with m2:
        st.markdown(metric_card("Brake (pump) HP", f"{pr.brake_hp:.2f}",
                    f"{pr.pump_efficiency*100:.0f}% pump eff", "#455A64"), unsafe_allow_html=True)
    with m3:
        st.markdown(metric_card("Electric HP", f"{pr.electric_hp:.2f}",
                    f"{pr.motor_efficiency*100:.0f}% motor eff", "#1565C0"), unsafe_allow_html=True)
    with m4:
        st.markdown(metric_card("Recommended motor", f"{pr.recommended_motor_hp:g} HP",
                    f"incl. {pr.safety_margin*100:.0f}% margin", "#2E7D32"), unsafe_allow_html=True)

    show_warnings(pr.warnings)

    with st.expander("Show formula"):
        st.latex(r"\text{Hydraulic HP} = \dfrac{\text{GPM} \times \text{Total PSI}}{1714}")
        st.latex(r"\text{Electric HP} = \dfrac{\text{Hydraulic HP}}{\eta_{pump} \times \eta_{motor}}")
        st.write("Example: 6 GPM at 700 PSI -> 2.45 hydraulic -> 2.45 / (0.60 x 0.85) = 4.80 "
                 "electric -> +20% = 5.76 -> round up to **6 HP** minimum.")


# ===========================================================================
# Tool 5 - Bucket Test
# ===========================================================================
def render_bucket():
    t = TOOL_BY_KEY["bucket"]
    tool_header(t["emoji"], t["name"], t["sub"])

    c1, c2 = st.columns(2)
    with c1:
        bucket = st.number_input("Bucket size (gallons)", min_value=0.1,
                                 value=config.DEFAULT_BUCKET_GALLONS, step=0.5)
    with c2:
        seconds = st.number_input("Fill time (seconds)", min_value=0.1, value=30.0, step=1.0)

    br = bucket_test.calculate(seconds, bucket_gallons=bucket)
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown(metric_card("Estimated flow", f"{br.gpm:.1f} GPM",
                    f"{bucket:g}-gal bucket in {seconds:g} s", "#1565C0"), unsafe_allow_html=True)
    show_warnings(br.warnings)
    st.info("Tip: time it a few times and average. Use this GPM in the Nozzle and Pump tools.")

    with st.expander("Show formula"):
        st.latex(r"\text{GPM} = \dfrac{\text{Bucket Gallons} \times 60}{\text{Fill Time (s)}}")
        st.write("Example: a 5-gallon bucket filling in 30 s -> 300 / 30 = **10 GPM**.")


# ===========================================================================
# Tool 6 - About / Safety
# ===========================================================================
def render_about():
    t = TOOL_BY_KEY["about"]
    tool_header(t["emoji"], t["name"], t["sub"])

    st.markdown(
        """
**What this app does.** It helps a home snowmaker answer practical questions:
can I make snow this week, which nights are best, and what nozzle / pressure /
pump / water flow do I need.

**The science, in plain English.**
- Snowmaking depends on **wet bulb temperature**, not just air temperature.
  Wet bulb combines temperature *and* humidity.
- Snowmaking generally becomes possible **around/below 27-28 F wet bulb**.
- **28-29 F wet bulb is borderline** and can produce slushy snow even with good
  equipment.
- Efficiency improves dramatically into the **mid-20s**; most home guns make
  drier, powderier snow in the **lower 20s and below** (best in the teens).
- **Ideal home conditions are roughly below 20 F wet bulb with little wind.**
- **Droplet size matters:** higher pressure makes smaller droplets that freeze
  faster. Most snow guns run roughly **100-1000 PSI**; home guns are often on
  the higher end.
- Good snow needs the right **droplet size**, **cooling below freezing**,
  **nucleation**, and enough **hang time** before droplets land.

**Assumptions & cautions.**
- Wet bulb uses the **psychrometric** method by default (physically correct),
  with Stull and a dew-point blend as alternatives.
- Pressure from the nozzle formula is **theoretical**. Real pressure at your
  pump or gun differs due to **hose length, fittings, elevation, and
  restrictions** - **always measure with a gauge.**
- Pump HP uses default **60% pump** and **85% motor** efficiency plus a **20%
  safety margin** - adjust to your gear.

**Safety.** Water + electricity + cold is serious. Use GFCI protection and
outdoor-rated cordage, bleed pressure before servicing fittings, and follow your
equipment ratings and local water-use rules.

**Data sources.** ZIP -> location via Zippopotam.us; forecast via Open-Meteo
(both free, no API key). No API keys are stored in this app.
        """
    )
    st.caption(f"{config.APP_NAME} v{config.APP_VERSION}")


# ===========================================================================
# Router
# ===========================================================================
RENDERERS = {
    "forecast": render_forecast,
    "nozzle": render_nozzle,
    "pressure": render_pressure,
    "pump": render_pump,
    "bucket": render_bucket,
    "about": render_about,
}

selected = st.query_params.get("tool")

if selected in RENDERERS:
    back_to_dashboard()
    RENDERERS[selected]()
    st.divider()
    back_to_dashboard()
else:
    render_dashboard()
