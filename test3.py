import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import base64
import numpy as np

# ── Pagina instellingen ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="Johan Cruijff ArenA Dashboard",
    layout="wide"
)
# ── Data laden ────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    ac = pd.read_csv("dummy/fct_access_control.csv")
    tk = pd.read_csv("dummy/tickets.csv")
    ac["Datum"] = pd.to_datetime(ac["Datum"])
    ac["Tijd"]  = pd.to_datetime(ac["Tijd"], format="%H:%M:%S.%f", errors="coerce")

    
    tk["EventDate"] = pd.to_datetime(tk["EventDate"])
    return ac, tk

access_control, tickets = load_data()

# --- Side Bar -----------------------------------------------------------------

with st.sidebar:
    st.title("Menu")
    st.image("/Users/martijnzuijderwijk/Documents/streamlit/Johan_Cruijff_ArenA_logo.png", width=180)
    
    option = st.selectbox(
        'Kies een datum:',
        ["16 maart 2025", "12 juli 2025"]
    )

    datum_mapping = {
        "16 maart 2025": "2025-03-16",
        "12 juli 2025":  "2025-07-12",
    }
    event_mapping = {
        "16 maart 2025": "Ajax - PSV | 16 maart 2025",
        "12 juli 2025":  "Concert Coldplay | 12 juli 2025",
    }

    gekozen_datum = pd.to_datetime(datum_mapping[option])
    gekozen_event = event_mapping[option]

    ac_filtered = access_control[
        access_control["Datum"].dt.date == gekozen_datum.date()
    ]

    ingangen_opties = ["Alle ingangen"] + sorted(
        access_control["Ingang"].dropna().unique().tolist()
    )
    gekozen_ingang = st.selectbox("Ingang", ingangen_opties)

    tickets_filtered = tickets[tickets["EventDate"].dt.date == gekozen_datum.date()]
    if gekozen_ingang != "Alle ingangen":
        tickets_filtered = tickets_filtered[tickets_filtered["Gate"] == gekozen_ingang]
        ac_filtered = ac_filtered[ac_filtered["Ingang"] == gekozen_ingang]

    st.markdown("---")
    st.markdown("### Instellingen")
    interval_min = st.slider(
        "Tijdsinterval instroomgrafiek (min)",
        min_value=5, max_value=60, value=15, step=5
    )

    st.markdown("---")
    st.markdown(
        "<small style='color:#7A9BB5'>BSc Informatiekunde — UvA<br>"
        "Martijn Zuijderwijk</small>",
        unsafe_allow_html=True
    )

# --- Hoofdpagina ---------------------------------------------------------------------------
import base64

def image_to_base64(path):
    with open(path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()

logo_path = "/Users/martijnzuijderwijk/Documents/streamlit/Johan_Cruijff_ArenA_logo.png"
logo_base64 = image_to_base64(logo_path)

st.markdown(
    f"""
    <div style="display: flex; justify-content: center; align-items: center; margin-top: 20px; margin-bottom: 20px;">
        <img src="data:image/png;base64,{logo_base64}" width="220">
    </div>
    """,
    unsafe_allow_html=True
)
st.markdown(
    """
    <h1 style='text-align: center;'>
        Johan Cruijff ArenA Dashboard
    </h1>
    """,
    unsafe_allow_html=True
)
bezoekers_per_ingang = ac_filtered.groupby("Ingang")["AantalToegang"].sum().reset_index()
stewards_per_ingang = tickets_filtered.groupby("Gate").size().reset_index(name="AantalStewards")
stewards_per_ingang = stewards_per_ingang.rename(columns={"Gate": "Ingang"})

combinatie = bezoekers_per_ingang.merge(stewards_per_ingang, on="Ingang", how="left").fillna(0)
combinatie["BezoekersPerSteward"] = combinatie["AantalToegang"] / combinatie["AantalStewards"].replace(0, 1)

st.subheader(gekozen_event)

tab1, tab2, tab3 = st.tabs(["Operationeel overzicht", "Drukte Analyse", "Steward Inzet"])
# Pagina 1 -------------------------------------------------------------------------------
with tab1:
    DREMPEL = 200 

    onderbezet = combinatie[combinatie["BezoekersPerSteward"] > DREMPEL]["Ingang"].tolist()

    if onderbezet:
        st.warning(f"Onderbezetting gedetecteerd bij ingang(en): {', '.join(sorted(onderbezet))}")

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("Aantal gescande kaarten", len(ac_filtered))
    with col2:
        st.metric("Aantal bezoekers binnen", int(ac_filtered["AantalToegang"].sum()))
    with col3:
        st.metric("Aantal Ingangen", ac_filtered["Ingang"].nunique())
    with col4:
        geweigerd = len(ac_filtered) - int(ac_filtered["AantalToegang"].sum())
        st.metric("Geweigerde toegangskaarten", geweigerd)
    with col5:
        aantal_stewards = len(tickets_filtered)
        st.metric("Aantal stewards aanwezig", aantal_stewards)
    with col6:
        bezoekers = int(ac_filtered["AantalToegang"].sum())
        ratio = round(bezoekers / aantal_stewards) if aantal_stewards > 0 else 0
        st.metric("Bezoekers per steward", ratio)

    col_links, col_rechts = st.columns(2)
    with col_links:
        st.markdown("##### Instroom over tijd")

        instroom_df = ac_filtered[ac_filtered["AantalToegang"] > 0].copy()

        if not instroom_df.empty and instroom_df["Tijd"].notna().any():
            instroom_df["TijdBlok"] = instroom_df["Tijd"].dt.floor(f"{interval_min}min")
            instroom_df["TijdLabel"] = instroom_df["TijdBlok"].dt.strftime("%H:%M")

        if gekozen_ingang == "Alle ingangen":
            instroom_tijd = (
                instroom_df.groupby(["TijdLabel", "Ingang"])["AantalToegang"]
                .sum()
                .reset_index()
            )
            st.line_chart(
                instroom_tijd,
                x="TijdLabel",
                y="AantalToegang",
                color="Ingang",
                x_label="Tijd",
                y_label="Aantal toegangen",
                height=300
            )
        else:
            instroom_tijd = (
                instroom_df.groupby("TijdLabel")["AantalToegang"]
                .sum()
                .reset_index()
            )
            st.line_chart(
                instroom_tijd,
                x="TijdLabel",
                y="AantalToegang",
                x_label="Tijd",
                y_label="Aantal toegangen",
                color="#C8102E",
                height=300
            )
    with col_rechts:

        # Cumulatieve instroom
        st.markdown("##### Cumulatieve bezoekersinstroom")
        bezoekers_tijd= ac_filtered[ac_filtered["AantalToegang"] > 0].copy()
        bezoekers_tijd["Tijdblok"] = bezoekers_tijd["Tijd"].dt.floor(f"{interval_min}min").dt.strftime("%H:%M")
        bezoekers_grouped = bezoekers_tijd.groupby(["Tijdblok"])["AantalToegang"].sum().cumsum().reset_index()
        bezoekers_grouped["Cumulatief"] = bezoekers_grouped["AantalToegang"]
        
        fig = px.line(
            bezoekers_grouped,
            x = "Tijdblok",
            y = "AantalToegang",
            labels = {
                "Tijdblok" : "Tijd",
                "AantalToegang" : "Aantal bezoekers binnen cumulatief",
            },
            height=300
        )
    
        st.plotly_chart(fig, use_container_width=True)



# Pagina 2 ----------------------------------------------------
with tab2:
    col_links, col_rechts = st.columns(2)
    with col_links:
    # --- staafdiagram
        st.markdown("##### Bezoekers per ingang over tijd")
        bezoekers_tijd = ac_filtered[ac_filtered["AantalToegang"] > 0].copy()
        bezoekers_tijd["Tijdblok"] = bezoekers_tijd["Tijd"].dt.floor(f"{interval_min}min").dt.strftime("%H:%M")
        bezoekers_grouped = bezoekers_tijd.groupby(["Ingang", "Tijdblok"])["AantalToegang"].sum().reset_index()

            #fig = go.figure()
            #for tijdblok in sorted(bezoekers_grouped["Tijdblok"].unique()):
            #    data = bezoekers_grouped[bezoekers_grouped["Tijdblok"] == tijdblok]
            #    fig.add_trace

        fig = px.bar(
            bezoekers_grouped,
            x="Ingang",
            y="AantalToegang",
            color="Tijdblok",
            barmode="stack",
            labels={
                "AantalToegang": "Aantal bezoekers binnen",
                "Ingang": "Ingang",
                    
            },
            height=300
        )

        fig.update_layout(
            xaxis_title="Ingang",
            yaxis_title="Aantal bezoekers binnen",
            legend_title="Tijdblok",
            margin=dict(t=20, b=40)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col_rechts:
    # --- Heatmap -----------------
        st.markdown("##### Heatmap drukte per ingang en tijdvak")
        heatmap_df = ac_filtered[ac_filtered["AantalToegang"] > 0].copy()
        heatmap_df["Tijdblok"] = heatmap_df["Tijd"].dt.floor(f"{interval_min}min").dt.strftime("%H:%M")

        heatmap_grouped = (
            heatmap_df.groupby(["Ingang", "Tijdblok"])["AantalToegang"].sum().reset_index()
        )
        heatmap_pivot = heatmap_grouped.pivot(
            index="Ingang",
            columns="Tijdblok",
            values="AantalToegang"
        ).fillna(0)

        fig = px.imshow(
            heatmap_pivot,
            labels=dict(x="Tijdvak", y="Ingang", color="Aantal bezoekers binnen"),
            color_continuous_scale="Reds",
            aspect="auto",
            height=400
        )
        fig.update_layout(
            xaxis_title="Tijdvak",
            yaxis_title="Ingang",
            margin=dict(t=20, b=80),
            xaxis_tickangle=-45
        )

        st.plotly_chart(fig, use_container_width=True)

    st.markdown("##### Afwijkingen overzicht per ingang")
    anomalie_df = (
        ac_filtered.groupby("Ingang")[[
        "AantalDubbeleStoel",
        "AantalNoodknop", 
        "AantalBlacklist",
        "AantalFouilleren",
        "AantalVerkeerdeIngang",
        "AantalOnbekendeKaart",
        "AantalDubbelAangeboden"
        ]].sum().reset_index()
    )

    st.dataframe(anomalie_df, use_container_width=True, hide_index=True)


with tab3:
    col_links, col_rechts = st.columns(2)
    with col_links:
        st.markdown("##### Stewards vs. bezoekers per ingang")
        combinatie_long = pd.melt(combinatie,id_vars= "Ingang", value_vars= ["AantalToegang", "AantalStewards"], var_name= "Type")
        fig = go.Figure()

        fig.add_trace(go.Bar(
            name="Bezoekers",
            x=combinatie["Ingang"],
            y=combinatie["AantalToegang"],
            marker_color="#C8102E",
            yaxis="y"
        ))

        fig.add_trace(go.Scatter(
        name="Stewards",
        x=combinatie["Ingang"],
        y=combinatie["AantalStewards"],
        mode="lines+markers",
        marker_color="#1D4E8F",
        yaxis="y2"
        ))

        fig.update_layout(
            barmode="group",
            yaxis=dict(title="Aantal bezoekers"),
            yaxis2=dict(
                title="Aantal stewards",
                overlaying="y",
                side="right"
            ),
            legend=dict(orientation="h", y=1.1),
            height=400,
            margin=dict(t=40, b=40)
        )

        st.plotly_chart(fig, use_container_width=True)
    with col_rechts:
        st.markdown("#### Taakverdeling Personeel")
        taak_counts = tickets_filtered["Task"].value_counts().reset_index()
        taak_counts.columns = ["Taak", "Aantal"]

        fig = px.bar(
            taak_counts,
            x="Taak",
            y="Aantal",
            labels={
                "Taak": "Taak",
                "Aantal": "Aantal stewards"
            },
            color="Taak",
            height=350
        )

        fig.update_layout(
            xaxis_title="Taak",
            yaxis_title="Aantal stewards",
            showlegend=False,
            margin=dict(t=20, b=40)
        )

        st.plotly_chart(fig, use_container_width=True)
    
    
