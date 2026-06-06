"""
app.py - Snowmaking Planner
===========================

A polished, beginner-friendly Streamlit app for home snowmaking planning.

Run locally:
    pip install -r requirements.txt
    streamlit run app.py

Sections (tabs):
    1. Wet Bulb Snowmaking Forecast
    2. Nozzle Calculator
    3. Pressure Calculator
    4. Pump Horsepower Calculator
    5. Bucket Test GPM Calculator
    6. About / Safety / Assumptions

All math lives in modules/ and is unit-tested in tests/. The UI here is
intentionally thin: collect inputs, call a module, show results + plain English.
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
    weather,
    wetbulb,
)

# ---------------------------------------------------------------------------
# Page setup + light styling
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=config.APP_NAME,
    page_icon="snowflake",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      /* Tighten the top padding and give cards a clean look */
      .block-container {padding-top: 2rem; max-width: 1100px;}
      .metric-card {
          border-radius: 14px; padding: 1rem 1.2rem; color: white;
          box-shadow: 0 1px 4px rgba(0,0,0,.12);
      }
      .metric-card h3 {margin: 0 0 .2rem 0; font-size: .85rem; font-weight: 600;
          letter-spacing: .03em; text-transform: uppercase; opacity: .9;}
      .metric-card .big {font-size: 2rem; font-weight: 700; line-height: 1.1;}
      .metric-card .sub {font-size: .85rem; opacity: .92;}
      .rating-badge {
          display: inline-block; padding: .15rem .6rem; border-radius: 999px;
          color: white; font-weight: 600; font-size: .8rem;
      }
      .night-card {
          border: 1px solid #e6e6e6; border-radius: 12px; padding: 1rem 1.2rem;
          margin-bottom: .8rem; background: #fff;
      }
      .night-card .recommendation {color: #333; font-size: .95rem; margin-top: .4rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


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


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title(f"❄️ {config.APP_NAME}")
st.caption(config.APP_TAGLINE)

tab_forecast, tab_nozzle, tab_pressure, tab_pump, tab_bucket, tab_about = st.tabs(
    [
        "🌡️ Forecast",
        "🔩 Nozzle",
        "📈 Pressure",
        "⚡ Pump HP",
        "🪣 Bucket Test",
        "ℹ️ About / Safety",
    ]
)


# ===========================================================================
# TAB 1 - Wet Bulb Snowmaking Forecast
# ===========================================================================
with tab_forecast:
    st.subheader("Can I make snow this week?")
    st.write(
        "Enter your ZIP code to pull a free 7-day forecast and rank each night "
        "by **wet bulb temperature** - the number that actually drives "
        "snowmaking (not just the air temperature)."
    )

    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        zip_code = st.text_input("ZIP code", value="", max_chars=5, placeholder="e.g. 80424")
    with c2:
        days = st.slider("Forecast days", 1, config.FORECAST_DAYS_MAX, config.FORECAST_DAYS)
    with c3:
        method_label = st.selectbox(
            "Wet bulb method",
            ["Auto (best available)", "Stull (temp + humidity)", "Dew point (2/3,1/3)"],
        )
    strict = st.toggle(
        "Strict mode (conservative: only 'possible / borderline / too warm')",
        value=False,
        help="Detailed mode breaks 'possible' into Excellent / Good / Marginal.",
    )

    method = {
        "Auto (best available)": "auto",
        "Stull (temp + humidity)": "stull",
        "Dew point (2/3,1/3)": "dewpoint",
    }[method_label]

    go = st.button("Get snowmaking forecast", type="primary")

    if go:
        from modules import validation

        errs = validation.validate_zip(zip_code)
        if errs:
            for e in errs:
                st.error(e)
        else:
            try:
                with st.spinner("Looking up location and pulling forecast..."):
                    loc = weather.geocode_zip(zip_code)
                    fc = weather.get_forecast(loc, days=days)
                    nights = forecast_analysis.summarize_nights(
                        fc, strict=strict, method=method
                    )
                st.success(
                    f"Forecast for {loc.place_name}, {loc.state} "
                    f"({loc.latitude:.3f}, {loc.longitude:.3f}) - timezone {fc.timezone}."
                )

                if not nights:
                    st.info("No overnight windows found in the returned forecast.")
                else:
                    # Headline answer
                    best = min(nights, key=lambda n: n.min_wet_bulb_f)
                    can = forecast_analysis.can_make_snow_this_week(nights)
                    headline = (
                        "Yes - you have snowmaking windows this week."
                        if can
                        else "Not really - it looks too warm this week."
                    )
                    st.markdown(f"### {headline}")

                    # Best-night metric cards
                    m1, m2, m3, m4 = st.columns(4)
                    with m1:
                        st.markdown(
                            metric_card(
                                "Best night",
                                best.label,
                                best.best_time.strftime("around %-I %p"),
                                wetbulb.rating_color(best.rating),
                            ),
                            unsafe_allow_html=True,
                        )
                    with m2:
                        st.markdown(
                            metric_card(
                                "Lowest wet bulb",
                                f"{best.min_wet_bulb_f:.0f}F",
                                best.rating_label,
                                wetbulb.rating_color(best.rating),
                            ),
                            unsafe_allow_html=True,
                        )
                    with m3:
                        st.markdown(
                            metric_card(
                                "Air temp then",
                                f"{best.temp_at_best_f:.0f}F",
                                (
                                    f"{best.humidity_at_best:.0f}% RH"
                                    if best.humidity_at_best is not None
                                    else ""
                                ),
                                "#455A64",
                            ),
                            unsafe_allow_html=True,
                        )
                    with m4:
                        st.markdown(
                            metric_card(
                                "Wind then",
                                (
                                    f"{best.wind_at_best:.0f} mph"
                                    if best.wind_at_best is not None
                                    else "n/a"
                                ),
                                "calmer is better",
                                "#455A64",
                            ),
                            unsafe_allow_html=True,
                        )

                    st.markdown("#### Snowmaking outlook by night")
                    st.plotly_chart(
                        charts.night_quality_bar(nights), use_container_width=True
                    )

                    st.markdown("#### Night-by-night detail")
                    for n in nights:
                        color = wetbulb.rating_color(n.rating)
                        st.markdown(
                            f'<div class="night-card">'
                            f'<span class="rating-badge" style="background:{color}">'
                            f"{n.rating_label}</span> &nbsp; "
                            f"<strong>{n.label}</strong> &nbsp; "
                            f"Lowest wet bulb <strong>{n.min_wet_bulb_f:.0f}F</strong> "
                            f"&middot; air {n.temp_at_best_f:.0f}F "
                            + (
                                f"&middot; {n.humidity_at_best:.0f}% RH "
                                if n.humidity_at_best is not None
                                else ""
                            )
                            + (
                                f"&middot; wind {n.wind_at_best:.0f} mph"
                                if n.wind_at_best is not None
                                else ""
                            )
                            + f'<div class="recommendation">{n.recommendation}</div>'
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                        with st.expander(f"Hourly detail - {n.label}"):
                            st.plotly_chart(
                                charts.hourly_wetbulb_line(n),
                                use_container_width=True,
                                key=f"hourly-{n.label}",
                            )
            except weather.WeatherError as exc:
                st.error(f"Couldn't get the forecast: {exc}")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Unexpected error: {exc}")

    with st.expander("What do the snowmaking ratings mean?"):
        st.write(
            "Snowmaking depends on **wet bulb temperature**, which combines air "
            "temperature and humidity. Drier air lets water evaporatively cool "
            "below the air temperature, so you can make snow even when the "
            "thermometer reads above freezing."
        )
        for key, _bound in config.DETAILED_THRESHOLDS + [(config.TOO_WARM, None)]:
            st.markdown(
                f'<span class="rating-badge" style="background:'
                f'{wetbulb.rating_color(key)}">{wetbulb.rating_label(key)}</span> '
                f"&nbsp; {wetbulb.rating_explanation(key)}",
                unsafe_allow_html=True,
            )


# ===========================================================================
# TAB 2 - Nozzle Calculator
# ===========================================================================
with tab_nozzle:
    st.subheader("What nozzle number do I need?")
    st.write(
        "Enter your available water flow and the pressure you want at the gun. "
        "This uses the Snow State nozzle formula."
    )

    c1, c2 = st.columns(2)
    with c1:
        gpm = st.number_input("Water flow (GPM)", min_value=0.1, value=6.0, step=0.5, key="nz_gpm")
    with c2:
        psi = st.number_input("Desired pressure (PSI)", min_value=1.0, value=700.0, step=25.0, key="nz_psi")

    res = nozzle_calculator.calculate(gpm, psi)

    m1, m2 = st.columns(2)
    with m1:
        st.markdown(
            metric_card("Required nozzle number", f"{res.nozzle_number:.2f}",
                        "exact, unrounded", "#1565C0"),
            unsafe_allow_html=True,
        )
    with m2:
        orifice = nozzle_calculator.orifice_for(res.nozzle_number_rounded)
        sub = f"{orifice:.3f} in orifice" if orifice else "nearest chart size"
        st.markdown(
            metric_card("Suggested chart nozzle", f"#{res.nozzle_number_rounded:g}",
                        sub, "#2E7D32"),
            unsafe_allow_html=True,
        )

    show_warnings(res.warnings)

    st.markdown("#### Suggested nozzle combinations")
    st.caption(
        "Nozzle numbers add up, so you can split your target across several "
        "nozzles. These combinations sum to about your suggested number."
    )
    if res.combos:
        for combo in res.combos:
            pretty = " + ".join(f"#{c:g}" for c in combo)
            st.write(f"- {pretty}  (total #{sum(combo):g})")
    else:
        st.write("No tidy combinations found near that number - use the closest single size.")

    with st.expander("Show formula"):
        st.latex(r"\text{Nozzle Number} = \text{GPM} \times \sqrt{\dfrac{4000}{\text{PSI}}}")
        st.write(
            "Example: 6 GPM at 700 PSI -> 6 x sqrt(4000/700) = **14.35** "
            "-> round to nozzle **14**."
        )

    with st.expander("Nozzle number -> orifice diameter chart"):
        st.table(nozzle_calculator.chart_rows())


# ===========================================================================
# TAB 3 - Pressure Calculator
# ===========================================================================
with tab_pressure:
    st.subheader("What pressure will my gun run at?")
    st.write(
        "Enter your flow and total nozzle number to estimate the operating "
        "pressure. This is the inverse of the nozzle formula."
    )

    c1, c2 = st.columns(2)
    with c1:
        gpm_p = st.number_input("Water flow (GPM)", min_value=0.1, value=6.0, step=0.5, key="pr_gpm")
    with c2:
        nn = st.number_input("Total nozzle number", min_value=0.1, value=14.0, step=0.5, key="pr_nn")

    pres = pressure_calculator.calculate(gpm_p, nn)
    st.markdown(
        metric_card("Estimated pressure", f"{pres.psi:.0f} PSI",
                    "theoretical - measure to confirm", "#1565C0"),
        unsafe_allow_html=True,
    )
    show_warnings(pres.warnings)

    with st.expander("Show formula"):
        st.latex(r"\text{PSI} = 4000 \times \left(\dfrac{\text{GPM}}{\text{Nozzle Number}}\right)^2")
        st.write(
            "Example: 6 GPM, nozzle 14 -> 4000 x (6/14)^2 = **735 PSI**."
        )


# ===========================================================================
# TAB 4 - Pump Horsepower Calculator
# ===========================================================================
with tab_pump:
    st.subheader("How much pump horsepower do I need?")
    st.write(
        "Estimate the electric motor horsepower for your pump using standard "
        "hydraulic horsepower math, adjusted for real-world efficiencies."
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        gpm_h = st.number_input("Water flow (GPM)", min_value=0.1, value=6.0, step=0.5, key="hp_gpm")
        plumbing = st.number_input("Plumbing loss (PSI, optional)", min_value=0.0, value=0.0, step=10.0)
    with c2:
        psi_h = st.number_input("Desired gun pressure (PSI)", min_value=1.0, value=700.0, step=25.0, key="hp_psi")
        safety = st.slider("Safety margin", 0.0, 0.5, config.DEFAULT_SAFETY_MARGIN, 0.05,
                           help="Extra headroom added to the required electric HP.")
    with c3:
        pump_eff = st.slider("Pump efficiency", 0.30, 0.90, config.DEFAULT_PUMP_EFFICIENCY, 0.05)
        motor_eff = st.slider("Motor efficiency", 0.50, 0.98, config.DEFAULT_MOTOR_EFFICIENCY, 0.01)

    pr = pump_calculator.calculate(
        gpm=gpm_h, desired_psi=psi_h, pump_efficiency=pump_eff,
        motor_efficiency=motor_eff, plumbing_loss_psi=plumbing, safety_margin=safety,
    )

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(metric_card("Hydraulic HP", f"{pr.hydraulic_hp:.2f}",
                                f"at {pr.total_psi:.0f} PSI total", "#455A64"),
                    unsafe_allow_html=True)
    with m2:
        st.markdown(metric_card("Brake (pump) HP", f"{pr.brake_hp:.2f}",
                                f"{pr.pump_efficiency*100:.0f}% pump eff", "#455A64"),
                    unsafe_allow_html=True)
    with m3:
        st.markdown(metric_card("Electric HP", f"{pr.electric_hp:.2f}",
                                f"{pr.motor_efficiency*100:.0f}% motor eff", "#1565C0"),
                    unsafe_allow_html=True)
    with m4:
        st.markdown(metric_card("Recommended motor", f"{pr.recommended_motor_hp:g} HP",
                                f"incl. {pr.safety_margin*100:.0f}% margin "
                                f"({pr.recommended_hp:.2f} HP)", "#2E7D32"),
                    unsafe_allow_html=True)

    show_warnings(pr.warnings)

    with st.expander("Show formula"):
        st.latex(r"\text{Hydraulic HP} = \dfrac{\text{GPM} \times \text{Total PSI}}{1714}")
        st.latex(r"\text{Electric HP} = \dfrac{\text{Hydraulic HP}}{\eta_{pump} \times \eta_{motor}}")
        st.latex(r"\text{Recommended HP} = \text{Electric HP} \times (1 + \text{margin})")
        st.write(
            "Example: 6 GPM at 700 PSI -> hydraulic 2.45 HP -> electric "
            "2.45 / (0.60 x 0.85) = 4.80 HP -> +20% = 5.76 HP -> pick the next "
            "common motor size."
        )


# ===========================================================================
# TAB 5 - Bucket Test GPM Calculator
# ===========================================================================
with tab_bucket:
    st.subheader("What's my home water supply GPM?")
    st.write(
        "Put a known-size bucket under your spigot, fully open it, and time how "
        "long it takes to fill. That gives you your real flow rate."
    )

    c1, c2 = st.columns(2)
    with c1:
        bucket = st.number_input("Bucket size (gallons)", min_value=0.1,
                                 value=config.DEFAULT_BUCKET_GALLONS, step=0.5)
    with c2:
        seconds = st.number_input("Fill time (seconds)", min_value=0.1, value=30.0, step=1.0)

    br = bucket_test.calculate(seconds, bucket_gallons=bucket)
    st.markdown(
        metric_card("Estimated flow", f"{br.gpm:.1f} GPM",
                    f"{bucket:g}-gal bucket in {seconds:g} s", "#1565C0"),
        unsafe_allow_html=True,
    )
    show_warnings(br.warnings)

    st.info(
        "Tip: time it two or three times and average. Use this GPM in the "
        "Nozzle and Pump calculators."
    )

    with st.expander("Show formula"):
        st.latex(r"\text{GPM} = \dfrac{\text{Bucket Gallons} \times 60}{\text{Fill Time (s)}}")
        st.write("Example: a 5-gallon bucket filling in 30 s -> 300 / 30 = **10 GPM**.")


# ===========================================================================
# TAB 6 - About / Safety / Assumptions
# ===========================================================================
with tab_about:
    st.subheader("About, safety & assumptions")

    st.markdown(
        """
**What this app does.** It helps a home snowmaker answer practical questions:
can I make snow this week, which nights are best, what nozzle/pressure/pump do
I need, and what's my water flow.

**The science, in plain English.**
- Snowmaking depends on **wet bulb temperature**, not just air temperature.
  Wet bulb combines temperature *and* humidity.
- Snowmaking generally becomes possible **around/below 27 F wet bulb**; Snow
  State language puts the threshold **below 28 F**.
- **28-29 F wet bulb is borderline** and can produce slushy snow even with good
  equipment.
- Efficiency improves dramatically as wet bulb drops into the **mid-20s**.
  Most home guns make drier, powderier snow in the **lower 20s and below**.
- **Ideal home conditions are roughly below 20 F wet bulb with little wind.**
- **Droplet size matters:** higher water pressure makes smaller droplets that
  freeze faster. Most snow guns run roughly **100-1000 PSI**; home guns are
  often on the higher end.
- Good snow needs the right **droplet size**, **cooling below freezing**,
  **nucleation**, and enough **hang time** before droplets hit the ground.

**Important assumptions & cautions.**
- Wet bulb is computed with the **Stull (2011)** approximation (temp + humidity)
  or a **dew point blend** (Tw = 2/3 T + 1/3 Td). Both are approximations.
- Pressure from the nozzle formula is **theoretical**. Real pressure at your
  pump or gun differs because of **hose length, fittings, elevation, and
  restrictions**. **Always measure with a gauge.**
- Pump HP uses standard hydraulic horsepower with default **60% pump** and
  **85% motor** efficiency and a **20% safety margin** - adjust to your gear.
- Forecasts are estimates. Conditions change; verify locally before you commit
  water and power to a session.

**Safety.**
- Water + electricity + cold is a serious combination. Use proper GFCI
  protection, rated outdoor cordage, and follow your equipment's ratings.
- High-pressure water can injure. Bleed pressure before servicing fittings.
- Know your local rules on water use and runoff.

**Data sources.**
- ZIP -> location: Zippopotam.us (free, no key).
- Forecast: Open-Meteo (free, no key). The code is structured so another
  provider can be swapped in via `modules/config.py` and `modules/weather.py`.

**No API keys are stored in this app.** If a future provider needs one, set it
via Streamlit secrets or the `WEATHER_API_KEY` environment variable.
        """
    )

    st.caption(f"{config.APP_NAME} v{config.APP_VERSION}")
