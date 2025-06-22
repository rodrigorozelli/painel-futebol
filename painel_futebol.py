import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date

# ==========================
# Funções para a API do Sofascore
# ==========================

@st.cache_data(ttl=60)
def buscar_jogo_sofascore(time_procurado):
    """Busca um jogo na API do Sofascore para a data de hoje."""
    if not time_procurado:
        return None, "Por favor, digite o nome de um time."

    # Pega a data de hoje no formato YYYY-MM-DD
    hoje = date.today().strftime("%Y-%m-%d")
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{hoje}"
    
    headers = {"User-Agent": "Mozilla/5.0"} # Sofascore é menos exigente

    try:
        # Conexão direta, sem proxy!
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return None, f"Erro de conexão com a API do Sofascore. Detalhe: {e}"

    # A estrutura do JSON é diferente
    eventos = response.json().get("events", [])
    for evento in eventos:
        time_casa = evento["homeTeam"]["name"]
        time_visitante = evento["awayTeam"]["name"]
        
        if time_procurado.lower() in time_casa.lower() or time_procurado.lower() in time_visitante.lower():
            placar_casa = evento.get("homeScore", {}).get("current", "-")
            placar_visitante = evento.get("awayScore", {}).get("current", "-")
            
            dados_basicos = {
                "Data/Hora": datetime.fromtimestamp(evento["startTimestamp"]).strftime("%d/%m/%Y %H:%M"),
                "Time Casa": time_casa,
                "Placar Casa": placar_casa,
                "Time Visitante": time_visitante,
                "Placar Visitante": placar_visitante,
                "Status": evento["status"]["description"],
                "Event ID": evento["id"]
            }
            return dados_basicos, None

    return None, f"Nenhum jogo encontrado para '{time_procurado}' na data de hoje."

@st.cache_data(ttl=60)
def buscar_estatisticas_sofascore(event_id):
    """Busca estatísticas na API do Sofascore."""
    url = f"https://api.sofascore.com/api/v1/event/{event_id}/statistics"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # A API pode retornar 200 OK mas com erro no corpo do JSON
        dados = response.json()
        if "error" in dados:
            return None

    except (requests.exceptions.RequestException, ValueError):
        return None

    all_stats = dados.get("statistics", [])
    if not all_stats:
        return None

    estatisticas = {}
    # As estatísticas são agrupadas, precisamos iterar sobre elas
    for grupo in all_stats:
        if grupo.get("period") == "ALL": # Pegar estatísticas do jogo todo
            for stat_item in grupo.get("groups", []):
                for row in stat_item.get("rows", []):
                    nome = row.get("name")
                    valor_casa = row.get("home")
                    valor_visitante = row.get("away")
                    estatisticas[nome] = {"Casa": valor_casa, "Visitante": valor_visitante}
    
    return estatisticas if estatisticas else None

# ==========================
# Interface do Streamlit (Adaptada)
# ==========================
st.set_page_config(page_title="Painel de Futebol Ao Vivo", layout="wide", initial_sidebar_state="collapsed")
st.title("⚽ Painel de Futebol Ao Vivo")
st.markdown("Dados fornecidos pela API do Sofascore.")

time_digitado = st.text_input("Digite o nome de um time:", placeholder="Ex: Flamengo, Real Madrid, Corinthians...")

if st.button("🔍 Buscar Jogo / Atualizar"):
    if not time_digitado:
        st.warning("Por favor, digite o nome de um time.")
    else:
        with st.spinner(f"Buscando jogo para '{time_digitado}'..."):
            jogo, erro = buscar_jogo_sofascore(time_digitado)
        
        if erro:
            st.error(erro)
        elif jogo:
            st.success(f"Jogo encontrado para '{time_digitado}'!")

            st.subheader(f"Status: {jogo['Status']} ({jogo['Data/Hora']})")
            col1, col2, col3 = st.columns([2, 1, 2])
            with col1:
                st.metric(label=f"🏟️ {jogo['Time Casa']}", value=jogo['Placar Casa'])
            with col2:
                st.markdown("<h1 style='text-align: center; margin-top: 15px;'>X</h1>", unsafe_allow_html=True)
            with col3:
                st.metric(label=f"✈️ {jogo['Time Visitante']}", value=jogo['Placar Visitante'])

            st.divider()

            stats = buscar_estatisticas_sofascore(jogo["Event ID"])
            if stats:
                st.subheader("📊 Estatísticas da Partida")
                df_stats = pd.DataFrame(stats).T.reset_index()
                df_stats.columns = ["Estatística", jogo['Time Casa'], jogo['Time Visitante']]
                st.dataframe(df_stats, use_container_width=True, hide_index=True)
            else:
                st.info("ℹ️ Estatísticas não disponíveis para esta partida no momento.")
else:
    st.info("Digite o nome de um time e clique no botão para carregar os dados.")
