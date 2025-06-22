# painel_futebol.py (Versão para o Render)
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date

# ==========================
# FUNÇÕES (CONEXÃO DIRETA COM HEADERS)
# ==========================
@st.cache_data(ttl=60)
def buscar_jogo(time_procurado, data_selecionada):
    if not time_procurado:
        return None, "Por favor, digite o nome de um time."

    data_formatada = data_selecionada.strftime("%Y-%m-%d")
    url_alvo = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{data_formatada}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.sofascore.com/',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    try:
        response = requests.get(url_alvo, headers=headers, timeout=20)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return None, f"Erro de conexão com a API do Sofascore. O erro foi: {e}"

    eventos = response.json().get("events", [])
    for evento in eventos:
        time_casa = evento["homeTeam"]["name"]
        time_visitante = evento["awayTeam"]["name"]
        if time_procurado.lower() in time_casa.lower() or time_procurado.lower() in time_visitante.lower():
            placar_casa = evento.get("homeScore", {}).get("current", "-")
            placar_visitante = evento.get("awayScore", {}).get("current", "-")
            dados_basicos = {
                "Data/Hora": datetime.fromtimestamp(evento["startTimestamp"]).strftime("%d/%m/%Y %H:%M"),
                "Time Casa": time_casa, "Placar Casa": placar_casa, "Time Visitante": time_visitante,
                "Placar Visitante": placar_visitante, "Status": evento["status"]["description"], "Event ID": evento["id"]
            }
            return dados_basicos, None

    return None, f"Nenhum jogo encontrado para '{time_procurado}' na data {data_selecionada.strftime('%d/%m/%Y')}."

@st.cache_data(ttl=60)
def buscar_estatisticas(event_id):
    url_alvo = f"https://api.sofascore.com/api/v1/event/{event_id}/statistics"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.sofascore.com/',
    }
    
    try:
        response = requests.get(url_alvo, headers=headers, timeout=20)
        response.raise_for_status()
        dados = response.json()
        if "error" in dados: return None
    except (requests.exceptions.RequestException, ValueError):
        return None

    all_stats_periods = dados.get("statistics", [])
    if not all_stats_periods: return None

    estatisticas = {}
    for period_group in all_stats_periods:
        if period_group.get("period") == "ALL":
            for stat_group in period_group.get("groups", []):
                for item in stat_group.get("statisticsItems", []):
                    nome = item.get("name")
                    valor_casa = item.get("home")
                    valor_visitante = item.get("away")
                    estatisticas[nome] = {"Casa": valor_casa, "Visitante": valor_visitante}
    
    return estatisticas if estatisticas else None

# --- A INTERFACE DO STREAMLIT CONTINUA A MESMA ---
st.set_page_config(page_title="Painel de Futebol Ao Vivo", layout="wide", initial_sidebar_state="collapsed")
st.title("⚽ Painel de Futebol Ao Vivo")
st.markdown("Dados fornecidos pela API do Sofascore.")

col1, col2 = st.columns(2)
with col1:
    time_digitado = st.text_input("Digite o nome do time:", placeholder="Ex: Botafogo, Real Madrid...")
with col2:
    data_jogo = st.date_input("Selecione a data do jogo", date.today())

if st.button("🔍 Buscar Jogo / Atualizar"):
    if not time_digitado:
        st.warning("Por favor, digite o nome de um time.")
    else:
        with st.spinner(f"Buscando jogo para '{time_digitado}' na data {data_jogo.strftime('%d/%m/%Y')}..."):
            jogo, erro_jogo = buscar_jogo(time_digitado, data_jogo)
        
        if erro_jogo:
            st.error(erro_jogo)
        elif jogo:
            st.success(f"Jogo encontrado!")
            st.subheader(f"Status: {jogo['Status']} ({jogo['Data/Hora']})")
            c1, c2, c3 = st.columns([2, 1, 2])
            with c1:
                st.metric(label=f"🏟️ {jogo['Time Casa']}", value=jogo['Placar Casa'])
            with c2:
                st.markdown("<h1 style='text-align: center; margin-top: 15px;'>X</h1>", unsafe_allow_html=True)
            with c3:
                st.metric(label=f"✈️ {jogo['Time Visitante']}", value=jogo['Placar Visitante'])
            st.divider()
            with st.spinner("Buscando estatísticas detalhadas..."):
                stats = buscar_estatisticas(jogo["Event ID"])
            if stats:
                st.subheader("📊 Estatísticas da Partida")
                df_stats = pd.DataFrame(stats).T.reset_index()
                df_stats.columns = ["Estatística", jogo['Time Casa'], jogo['Time Visitante']]
                st.dataframe(df_stats, use_container_width=True, hide_index=True)
            else:
                st.info("ℹ️ A API do Sofascore não forneceu dados de estatísticas detalhadas para esta partida.")
else:
    st.info("Digite um time, escolha uma data e clique no botão para buscar.")
