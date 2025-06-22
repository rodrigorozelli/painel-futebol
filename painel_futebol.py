import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# ==========================
# Funções
# ==========================

@st.cache_data(ttl=60)
def buscar_jogo(time_procurado):
    """Busca um jogo usando o ScraperAPI com renderização de JavaScript."""
    if not time_procurado:
        return None, "Por favor, digite o nome de um time."

    try:
        api_key = st.secrets["SCRAPERAPI_KEY"]
    except KeyError:
        return None, "ERRO DE CONFIGURAÇÃO: A chave SCRAPERAPI_KEY não foi encontrada nos Secrets do seu app Streamlit."

    url_alvo = f"https://api-web.365scores.com/web/games/current?sport=1&lang=pt&timezone=-3"
    
    # ATUALIZAÇÃO 1: Habilitar o renderizador de JavaScript do ScraperAPI
    # Adicionamos o parâmetro '&render=true'
    proxy_url = f"http://api.scraperapi.com?api_key={api_key}&url={url_alvo}&render=true"

    try:
        # ATUALIZAÇÃO 2: Aumentar o timeout para dar tempo da página ser renderizada
        response = requests.get(proxy_url, timeout=40)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return None, f"Erro de conexão através do proxy. O site alvo pode estar lento ou bloqueando. Detalhe: {e}"

    jogos = response.json().get("games", [])
    for jogo in jogos:
        time_casa = jogo["homeTeam"]["name"]
        time_visitante = jogo["awayTeam"]["name"]
        if time_procurado.lower() in time_casa.lower() or time_procurado.lower() in time_visitante.lower():
            game_id = jogo["id"]
            hora = datetime.fromtimestamp(jogo["startTime"] / 1000).strftime("%d/%m/%Y %H:%M")
            dados_basicos = {
                "Data/Hora": hora, "Time Casa": time_casa, "Placar Casa": jogo.get("homeScore", {}).get("current", 0),
                "Time Visitante": time_visitante, "Placar Visitante": jogo.get("awayScore", {}).get("current", 0),
                "Status": jogo.get("status", {}).get("description", "Desconhecido"), "Game ID": game_id
            }
            return dados_basicos, None

    return None, f"Nenhum jogo ao vivo ou recente encontrado para '{time_procurado}'."

@st.cache_data(ttl=60)
def buscar_estatisticas(game_id):
    """Busca estatísticas usando o ScraperAPI com renderização de JavaScript."""
    try:
        api_key = st.secrets["SCRAPERAPI_KEY"]
    except KeyError:
        return None
    
    url_alvo = f"https://api-web.365scores.com/web/games/{game_id}/stats?lang=pt"
    proxy_url = f"http://api.scraperapi.com?api_key={api_key}&url={url_alvo}&render=true"
    
    try:
        response = requests.get(proxy_url, timeout=40)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return None
        
    stats_data = response.json().get("stats", [])
    if not stats_data:
        return None

    estatisticas = {}
    for item in stats_data:
        nome = item.get("name", "Desconhecido")
        home_value = item.get("homeValue", 0)
        away_value = item.get("awayValue", 0)
        estatisticas[nome] = {"Casa": home_value, "Visitante": away_value}

    return estatisticas

# ==========================
# Interface do Streamlit
# ==========================
# A interface não precisa de alterações.

st.set_page_config(page_title="Painel de Jogo ao Vivo", layout="wide", initial_sidebar_state="collapsed")

st.title("⚽ Painel de Futebol Ao Vivo")
st.markdown("Acompanhe placares e estatísticas de jogos em tempo real. Digite o nome de um time e clique em buscar.")

time_digitado = st.text_input("Digite o nome do time:", placeholder="Ex: Flamengo, Real Madrid, Corinthians...")

if st.button("🔍 Buscar Jogo / Atualizar"):
    with st.spinner(f"Buscando jogo para '{time_digitado}'... (via proxy com JS)"):
        jogo, erro = buscar_jogo(time_digitado)

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

        stats = buscar_estatisticas(jogo["Game ID"])
        if stats:
            st.subheader("📊 Estatísticas da Partida")
            df_stats = pd.DataFrame(stats).T.reset_index()
            df_stats.columns = ["Estatística", jogo['Time Casa'], jogo['Time Visitante']]
            st.dataframe(df_stats, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ Estatísticas ainda não disponíveis para esta partida.")
else:
    st.info("Digite o nome de um time e clique no botão para carregar os dados.")
