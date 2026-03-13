import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

# streamlit run C:\Users\thoma\Documents\S6_Cruise_ship\S6.py

# HIER GAAT JE BESTAANDE CODE VERDER (bijv. st.title, etc.)

title_text = "Vessel Performance"
st.set_page_config(page_title=title_text, layout="wide")
st.title(title_text)

# 1. Bestands-uploader
uploaded_file = st.file_uploader("Upload Vessel Data", type=["csv", "txt"])

if uploaded_file:
    # Inlezen: tab-scheiding en opschonen van aanhalingstekens in kolomnamen

    df = pd.read_csv(uploaded_file, sep='\t', engine='python', encoding='utf-16')
    df.columns = [str(c).replace('"', '').strip() for c in df.columns]

    # Zoek alle kolommen die "Fuel Rate" bevatten
    fuel_cols2 = [c for c in df.columns if 'Fuel Rate' in c]

    if fuel_cols2:
        # Zorg dat de data numeriek is (vervang fouten door 0)
        for col in fuel_cols2:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        # Bereken het gemiddelde verbruik per sensor
        averages = df[fuel_cols2].mean()
        
        # Filter: alleen sensoren met verbruik > 0.05 L/h (voorkomt ruis in diagram)
        filtered_avg = {k: v for k, v in averages.items() if v > 0.05}
        
        # Voorbereiden van de Sankey data
        labels = ["TOTAL USAGE"] + list(filtered_avg.keys())
        sources = [0] * len(filtered_avg) # Alles komt van bron 0 (Totaal)
        targets = list(range(1, len(filtered_avg) + 1))
        values = list(filtered_avg.values())
        total_val = sum(values)

        # Het diagram maken
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15, thickness=20,
                label=[f"{label} ({val:.1f} L/h)" if i>0 else f"{label} ({total_val:.1f} L/h)" 
                       for i, (label, val) in enumerate(zip(labels, [total_val] + values))],
                color="#006699"
            ),
            link=dict(source=sources, target=targets, value=values, color="rgba(0, 102, 153, 0.2)")
        )])

        st.subheader("Average Fuelrate (L/h)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No columns found with the name 'Fuel Rate'.")

    
    
    # TABEL------------------------------------------------------------------------------------------------------------------
    # 1. Tijd omzetten naar uren (onafhankelijk van interval)
    # Vervang 'Timestamp' door jouw kolomnaam voor tijd


    # 1. Forceer de conversie naar datetime
    # errors='coerce' zorgt dat foute data geen crash veroorzaakt maar NaN wordt
    df['Time'] = pd.to_datetime(df['Time'], errors='coerce')

    # 2. Verwijder rijen waar de tijd niet leesbaar was (optioneel maar veiliger)
    df = df.dropna(subset=['Time'])

    # 3. Nu werkt .min() en .to_pydatetime() wel
    min_tijd = df['Time'].min().to_pydatetime()
    max_tijd = df['Time'].max().to_pydatetime()

# 4. De rest van je session_state en slider code...
if 'slider_val' not in st.session_state:
    st.session_state.slider_val = (min_tijd, max_tijd)

    # 2. Session state initialiseren
    if 'slider_val' not in st.session_state:
        st.session_state.slider_val = (min_tijd, max_tijd)

    # 3. De Reset knop (verandert de waarde in de session state)
    if st.button('Reset naar volledige periode'):
        st.session_state.slider_val = (min_tijd, max_tijd)
        st.rerun()

    # 4. DE ENIGE SLIDER (geen select_slider gebruiken!)
    # Door 'value' te koppelen aan de session_state, luistert hij naar de knop
    gekozen_bereik = st.slider(
        "Selecteer tijdsperiode:",
        min_value=min_tijd,
        max_value=max_tijd,
        value=st.session_state.slider_val
    )

    # 5. Filteren (gebruik de output van de enige slider)
    start_tijd, eind_tijd = gekozen_bereik
    mask = (df['Time'] >= start_tijd) & (df['Time'] <= eind_tijd)
    df_filtered = df.loc[mask].copy()


    # 2. Slider maken voor tijdsselectie
    start_tijd, eind_tijd = st.select_slider(
        'Selecteer tijdsperiode voor analyse:',
        options=df['Time'],
        value=(df['Time'].min(), df['Time'].max())
    )

    # 3. DataFrame filteren op basis van selectie
    mask = (df['Time'] >= start_tijd) & (df['Time'] <= eind_tijd)
    df_filtered = df.loc[mask].copy()

    # 4. Bereken tijd_uren opnieuw voor de gefilterde set
    tijd_uren = (df_filtered['Time'] - df_filtered['Time'].iloc[0]).dt.total_seconds() / 3600

    # 2. Bereken verbruik per categorie (L/h * h = L)
    consumption_enginesb   = np.trapezoid(df_filtered['ME SB Fuel Rate'].fillna(0), tijd_uren).round(0)
    consumption_engineps   = np.trapezoid(df_filtered['ME PS Fuel Rate'].fillna(0), tijd_uren).round(0)
    consumption_genfwd     = np.trapezoid(df_filtered['Generator FWD Fuel Rate'].fillna(0), tijd_uren).round(0)
    consumption_gensb      = np.trapezoid(df_filtered['Generator Starboard AFT Fuel Rate'].fillna(0), tijd_uren).round(0)
    consumption_genps      = np.trapezoid(df_filtered['Generator Port AFT Fuel Rate'].fillna(0), tijd_uren).round(0)
    consumption_heater1    = np.trapezoid(df_filtered['Heater 1 Fuel Rate'], tijd_uren).round(0)
    consumption_heater2    = np.trapezoid(df_filtered['Heater 2 Fuel Rate'], tijd_uren).round(0)
    consumption_total      = consumption_enginesb + consumption_engineps + consumption_genfwd + consumption_gensb + consumption_genps + consumption_heater1 + consumption_heater2

    fuel_consumption = [
        consumption_enginesb, consumption_engineps,
        consumption_genfwd, consumption_gensb, consumption_genps,
        consumption_heater1, consumption_heater2, consumption_total
    ]

    # 1. Lijst met de 7 kolommen
    fuel_cols = [
        'ME SB Fuel Rate', 'ME PS Fuel Rate', 
        'Generator FWD Fuel Rate', 'Generator Starboard AFT Fuel Rate',
        'Generator Port AFT Fuel Rate', 'Heater 1 Fuel Rate', 'Heater 2 Fuel Rate'
    ]

    # 2. Maak een nieuwe kolom voor het totaal (per rij)
    df_filtered['Total Fuel Rate'] = df_filtered[fuel_cols].sum(axis=1)

    # 3. Voeg 'Total Fuel Rate' toe aan je lijst voor de berekening
    all_cols = fuel_cols + ['Total Fuel Rate']

    # 4. Bereken alle gemiddeldes in één keer
    avg_series = df_filtered[all_cols].mean().round(0)

    # Grafiek
    history_data = [df_filtered[col].fillna(0).tolist() for col in all_cols]


    # 5. Resultaat DataFrame
    result_df = pd.DataFrame({
        'Type'                      : avg_series.index,
        'Average Fuel Rate [L/h]'   : avg_series.values,
        'Fuel consumption [L]'      : fuel_consumption,
        'Rate over Time'            : history_data
    })

    st.subheader("Fuel consumption")
    st.dataframe(
        result_df,
        column_config={
            "Rate over Time": st.column_config.LineChartColumn(
                "Fuel Rate Trend",
                width="medium",
                help="Verloop van het verbruik over de geselecteerde periode"
            ),
        },
        hide_index=True,
    )





# --- SECTION: TREND ANALYSIS ---------------------------------------------------------------------------------------
    st.divider()
    st.subheader("Trend Analysis")

    # Filter columns that are suitable for plotting
    exclude_cols = ["Time", "Metric", "Name"]
    plot_options = [c for c in df.columns if c not in exclude_cols]
    
    # Sort options: Total Fuel Rate first, then the rest alphabetically
    if "Total Fuel Rate" in plot_options:
        plot_options.remove("Total Fuel Rate")
        plot_options = ["Total Fuel Rate"] + sorted(plot_options)
    else:
        plot_options = sorted(plot_options)

    st.write("Select measurements to display in the graph:")
    
    # Create a layout with 4 columns for the checkboxes
    cols = st.columns(4)
    selected_sensors = []

    # Create a checkbox for every measurement
    for i, option in enumerate(plot_options):
        # Determine which column to place the checkbox in
        with cols[i % 4]:
            # Default to True only for Total Fuel Rate
            is_checked = st.checkbox(option, value=(option == "Total Fuel Rate"))
            if is_checked:
                selected_sensors.append(option)

    # Display the graph based on the selected checkboxes
    if selected_sensors:
        fig_trend = px.line(
            df, 
            x="Time", 
            y=selected_sensors, 
            title="Trend: Selected Measurements"
        )
        fig_trend.update_layout(
            xaxis_title="Time",
            yaxis_title="Value",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Please select at least one measurement to display the graph.")