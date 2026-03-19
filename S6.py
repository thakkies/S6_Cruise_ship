import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import datetime

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



    if 'slider_key_v' not in st.session_state:
        st.session_state.slider_key_v = 0
    
    if st.button('Reset'):
        st.session_state.slider_key_v += 1
        st.rerun()

    # 4. DE ENIGE SLIDER (geen select_slider gebruiken!)
    # Door 'value' te koppelen aan de session_state, luistert hij naar de knop
    gekozen_bereik = st.slider(
        "Select timeperiod:",
        min_value = min_tijd,
        max_value = max_tijd,
        value = (min_tijd, max_tijd),
        format = "DD/MM/YY HH:mm",
        step = datetime.timedelta(minutes=5),
        key = f"slider_{st.session_state.slider_key_v}"
    )

    # 5. Filteren (gebruik de output van de enige slider)
    start_tijd, eind_tijd = gekozen_bereik
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
                help="Consumption trend over the selected period"
            ),
        },
        hide_index=True,
    )

    # 1. Kolommen definiëren
    bunker_cols = ['Bunker Aft Current Volume', 'Bunker FWD Current Volume']

    # 2. Eerst interpoleren om NaN-waardes op te vullen
    # 'linear' trekt een rechte lijn tussen het laatste bekende punt en het volgende punt
    df_filtered[bunker_cols] = df_filtered[bunker_cols].interpolate(method='linear', limit_direction='both')

    # 1. Instellen van het venster (bijv. 60 metingen als je per minuut logt)
    window_size = 10 

    # 2. Moving Average berekenen voor de bunkers
    df_filtered['Bunker_AFT_Smooth'] = df_filtered['Bunker Aft Current Volume'].rolling(window=window_size, center=True).mean()
    df_filtered['Bunker_FWD_Smooth'] = df_filtered['Bunker FWD Current Volume'].rolling(window=window_size, center=True).mean()

    # 3. Totaal volume berekenen op basis van de gladgestreken data
    df_filtered['Total_Bunker_Smooth'] = df_filtered['Bunker_AFT_Smooth'] + df_filtered['Bunker_FWD_Smooth']

    # 4. Gebruik de eerste en laatste GELDIGE (niet-NaN) waarde voor het verbruik
    # Rolling mean introduceert NaN aan het begin/eind, bfill/ffill lost dit op
    vol_start = df_filtered['Total_Bunker_Smooth'].bfill().iloc[0]
    vol_eind = df_filtered['Total_Bunker_Smooth'].ffill().iloc[-1]

    verbruik_bunker = vol_start - vol_eind    




    # 4. Haal je berekende integraal op (Total Fuel Rate)
    # verbruik_integraal = consumption_total # De waarde uit je vorige stap

    # 5. Bereken de afwijking
    afwijking_procent = ((consumption_total - verbruik_bunker) / verbruik_bunker) * 100 if verbruik_bunker != 0 else 0

    # 6. Weergave in Streamlit
    col1, col2, col3 = st.columns(3)
    col1.metric("Consumption based on bunkervolumes", f"{verbruik_bunker:.0f} L")
    col2.metric("Consumption based on integrating the fuelrates", f"{consumption_total:.0f} L")
    col3.metric("Afwijking", f"{afwijking_procent:.1f}%", delta=f"{afwijking_procent:.1f}%", delta_color="inverse")


# --- SECTION: TREND ANALYSIS ---------------------------------------------------------------------------------------
    st.header("Trend analysis")
    LAYOUT = {
    "Column 1": ["General", "Extern", "Heaters"],
    "Column 2": ["Engines"],
    "Column 3": ["Generators"]
}

    GROUPS = {
        "**General**": ["Speed Over Ground", "Depth", "Course Over Ground", "Bunker Aft Current Volume", "Bunker FWD Current Volume"
        ],
        "**Extern**": ["Humidity Air", "Temperature Air", "App Wind Speed", "App Wind Angle"],
        "**Heaters**": [
            "Heater 1 Fuel Rate", "Heater 1 Fuel Temp", "Heater 2 Fuel Rate", "Heater 2 Fuel Temp"],

        "**Engines**": [
            "ME SB Alternator Voltage", "ME SB Boost Pressure", "ME SB Coolant Pressure", "ME SB Coolant Temp", "ME SB Load", "ME SB Exhaust Temp",
            "ME SB Fuel Rate", "ME SB Fuel Temp", "ME SB Oil Pressure", "ME SB Oil Temp", "ME SB RPM", "ME PS Alternator Voltage",
            "ME PS Boost Pressure", "ME PS Coolant Pressure", "ME PS Coolant Temp", "ME PS Load", "ME PS Exhaust Temp", "ME PS Fuel Rate",
            "ME PS FuelTemp", "ME PS Oil Pressure", "ME PS Oil Temp", "ME PS RPM"
        ],
        "**Generators**": [
            "Generator FWD Fuel Rate", "Generator FWD Real Power", "Generator FWD Apparent Power", "Generator FWD Phase A Current",
            "Generator FWD Phase B Current", "Generator FWD Phase C Current", "Generator Port AFT Fuel Rate", "Generator Port AFT Real Power",
            "Generator Port AFT Apparent Power", "Generator Port AFT Phase A Current", "Generator Port AFT Phase B Current",
            "Generator Port AFT Phase C Current", "Generator Starboard AFT Fuel Rate", "Generator Starboard AFT Real Power",
            "Generator Starboard AFT Apparent Power", "Generator Starboard AFT Phase A Current", "Generator Starboard AFT Phase B Current",
            "Generator Starboard AFT Phase C Current"
        ],
    }

    COL_MAPPING = [
        ["**General**", "**Extern**", "**Heaters**"], # Kolom 1
        ["**Engines**"],                      # Kolom 2
        ["**Generators**"]                    # Kolom 3
    ]
        
    selected_metrics = []
        
    # Maak 3 kolommen aan
    ui_cols = st.columns(5)
    
    for i, groups_in_col in enumerate(COL_MAPPING):
        with ui_cols[i]:
            for group_name in groups_in_col:
                st.markdown(f"###### {group_name}")
                for m in GROUPS[group_name]:
                    if m in df.columns:
                        # Unieke key voorkomt fouten bij dubbele variabelen (zoals Boost Pressure)
                        if st.checkbox(m, key=f"cb_{group_name}_{m}"):
                            selected_metrics.append(m)
                st.write("") # Spacer

    st.divider()

    if selected_metrics:
        fig = px.line(df, x='Time', y=selected_metrics)
        fig.update_layout(
            hovermode="x unified",
            xaxis_title="Tijd",
            yaxis_title="Waarde"
        )
        st.plotly_chart(fig, use_container_width=True)

    