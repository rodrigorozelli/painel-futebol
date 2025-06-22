import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta

# ==========================
# Funções - Agora recebem a data como parâmetro
# ==========================

@st.cache_data(ttl=300) # Aumentar o cache pois os dados de dias passados não mudam
def buscar_jogo(time_procurado, data_selecionada):
    if not time_procurado:
        return None, "Por favor, digite o nome de um time."

    try:
        api_key = st.secrets["SCRAPERAPI_KEY"]
    except KeyError:
        return None, "ERRO: Chave SCRAPERAPI_KEY não encontrada nos Secrets."

    # Usa a data fornecida pelo usuário
    data_formatada = data_selecionada.strftime("%Y-%m-%d")
    url_alvo = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{data_formatada}"
    payload = {'api_key': api_key, 'url': url_alvo}

    try:
        response = requests.get('http://api.scraperapi.com', params=payload, timeout=25)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return None, f"Erro de conexão através do proxy: {e}"

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

# ... (a função buscar_estatisticas não precisa mudar) ...
@st.cache_data(ttl=60)
def buscar_estatisticas(event_id):
    try:
        api_key = st.secrets["SCRAPERAPI_KEY"]
    except KeyError: return None
    url_alvo = f"https://api.sofascore.com/api/v1/event/{event_id}/statistics"
    payload = {'api_key': api_key, 'url': url_alvo}
    try:
        response = requests.get('http://api.scraperapi.com', params=payload, timeout=25)
        response.raise_for_status()
        dados = response.json()
        if "error" in dados: return None
    except (requests.exceptions.RequestException, ValueError): return None
    all_stats = dados.get("statistics", [])
    if not all_stats: return None
    estatisticas = {}
    for grupo in all_stats:
        if grupo.get("period") == "ALL":
            for stat_item in grupo.get("groups", []):
                for row in stat_item.get("rows", []):
                    nome = row.get("name")
                    valor_casa = row.get("home")
                    valor_visitante = row.get("away")
                    estatisticas[nome] = {"Casa": valor_casa, "Visitante": valor_visitante}
    return estatisticas if estatisticas else None

# ==========================
# Interface do Streamlit (com seletor de data)
# ==========================
st.set_page_config(page_title="Painel de Futebol Ao Vivo", layout="wide", initial_sidebar_state="collapsed")
st.title("⚽ Painel de Futebol Ao Vivo")
st.markdown("Dados fornecidos pela API do Sofascore.")

# --- SELETORES DE BUSCA ---
col1, col2 = st.columns(2)
with col1:
    time_digitado = st.text_input("Digite o nome do time:", placeholder="Ex: Botafogo, Real Madrid...")
with col2:
    # Seletor de data, começando com a data de hoje
    data_jogo = st.date_input("Selecione a data do jogo", date.today())

if st.button("🔍 Buscar Jogo / Atualizar"):
    if not time_digitado:
        st.warning("Por favor, digite o nome de um time.")
    else:
        with st.spinner(f"Buscando jogo para '{time_digitado}' na data {data_jogo.strftime('%d/%m/%Y')}..."):
            # Passa a data selecionada para a função
            jogo, erro = buscar_jogo(time_digitado, data_jogo)
        
        if erro:
            st.error(erro)
        elif jogo:
            st.success(f"Jogo encontrado!")
            # ... (o resto da interface para exibir o jogo continua igual)
            st.subheader(f"Status: {jogo['Status']} ({jogo['Data/Hora']})")
            c1, c2, c3 = st.columns([2, 1, 2])
            with c1:
                st.metric(label=f"🏟️ {jogo['Time Casa']}", value=jogo['Placar Casa'])
            with c2:
                st.markdown("<h1 style='text-align: center; margin-top: 15px;'>X</h1>", unsafe_allow_html=True)
            with c3:
                st.metric(label=f"✈️ {jogo['Time Visitante']}", value=jogo['Placar Visitante'])
            st.divider()
            stats = buscar_estatisticas(jogo["Event ID"])
            if stats:
                st.subheader("📊 Estatísticas da Partida")
                df_stats = pd.DataFrame(stats).T.reset_index()
                df_stats.columns = ["Estatística", jogo['Time Casa'], jogo['Time Visitante']]
                st.dataframe(df_stats, use_container_width=True, hide_index=True)
            else:
                st.info("ℹ️ Estatísticas não disponíveis para esta partida.")
else:
    st.info("Digite um time, escolha uma data e clique no botão para buscar.")
