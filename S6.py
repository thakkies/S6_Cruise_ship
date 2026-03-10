import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# streamlit run C:\Users\thoma\Documents\S6_Cruise_ship\S6.py

# --- WACHTWOORD BEVEILIGING ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    # Toon invoerveld
    pwd = st.text_input("Enter the password:", type="password")
    if pwd:
        if pwd == st.secrets["password"]:
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("Wrong password")
    return False

if not check_password():
    st.stop()  # De rest van de code wordt niet uitgevoerd
# ------------------------------

# HIER GAAT JE BESTAANDE CODE VERDER (bijv. st.title, etc.)
st.title("Vessel Performance Dashboard")

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
    fuel_cols = [c for c in df.columns if 'Fuel Rate' in c]

    if fuel_cols:
        # Zorg dat de data numeriek is (vervang fouten door 0)
        for col in fuel_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Bereken het gemiddelde verbruik per sensor
        averages = df[fuel_cols].mean()
        
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
        
        # Controle-tabelletje eronder
        st.write("Fuelsources found:", fuel_cols)
    else:
        st.warning("No columns found with the name 'Fuel Rate'.")

# --- SECTION: TREND ANALYSIS ---
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