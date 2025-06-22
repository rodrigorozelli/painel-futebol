import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# ==========================
# Funções
# ==========================

# Usar o cache do Streamlit para evitar fazer a mesma requisição várias vezes seguidas
@st.cache_data(ttl=60)  # Cache por 60 segundos
def buscar_jogo(time_procurado):
    """Busca um jogo que contenha o nome do time fornecido."""
    if not time_procurado:
        return None, "Por favor, digite o nome de um time."

    url = "https://api-web.365scores.com/web/games/current"
    params = {"sport": 1, "lang": "pt", "timezone": "-3"}
    # Usar um User-Agent mais comum pode ajudar a evitar bloqueios simples
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()  # Lança um erro para status 4xx/5xx
    except requests.exceptions.RequestException as e:
        # Retorna uma mensagem de erro amigável em caso de falha na conexão
        return None, f"Erro de conexão ao buscar jogos. A plataforma pode estar bloqueando o acesso. Tente novamente mais tarde. Detalhe: {e}"

    jogos = response.json().get("games", [])
    for jogo in jogos:
        time_casa = jogo["homeTeam"]["name"]
        time_visitante =jogo["awayTeam"]["name"]

        # Busca pelo nome do time (ignorando maiúsculas/minúsculas)
        if time_procurado.lower() in time_casa.lower() or time_procurado.lower() in time_visitante.lower():
            game_id = jogo["id"]
            hora = datetime.fromtimestamp(jogo["startTime"] / 1000).strftime("%d/%m/%Y %H:%M")

            dados_basicos = {
                "Data/Hora": hora,
                "Time Casa": time_casa,
                "Placar Casa": jogo.get("homeScore", {}).get("current", 0),
                "Time Visitante": time_visitante,
                "Placar Visitante": jogo.get("awayScore", {}).get("current", 0),
                "Status": jogo.get("status", {}).get("description", "Desconhecido"),
                "Game ID": game_id
            }
            return dados_basicos, None  # Retorna o jogo e nenhuma mensagem de erro

    return None, f"Nenhum jogo ao vivo ou recente encontrado para '{time_procurado}'."

@st.cache_data(ttl=60) # Cache por 60 segundos
def buscar_estatisticas(game_id):
    """Busca as estatísticas de um jogo específico pelo seu ID."""
    url = f"https://api-web.365scores.com/web/games/{game_id}/stats"
    params = {"lang": "pt"}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
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

st.set_page_config(page_title="Painel de Jogo ao Vivo", layout="wide", initial_sidebar_state="collapsed")

st.title("⚽ Painel de Futebol Ao Vivo")
st.markdown("Acompanhe placares e estatísticas de jogos em tempo real. Digite o nome de um time e clique em buscar.")

# --- Campo de busca ---
time_digitado = st.text_input("Digite o nome do time:", placeholder="Ex: Flamengo, Real Madrid, Corinthians...")

# --- Botão de busca ---
if st.button("🔍 Buscar Jogo / Atualizar"):
    with st.spinner(f"Buscando jogo para '{time_digitado}'..."):
        jogo, erro = buscar_jogo(time_digitado)

    if erro:
        st.error(erro)
    elif jogo:
        st.success(f"Jogo encontrado para '{time_digitado}'!")

        # --- Exibição do Placar ---
        st.subheader(f"Status: {jogo['Status']} ({jogo['Data/Hora']})")
        col1, col2, col3 = st.columns([2, 1, 2])
        with col1:
            st.metric(label=f"🏟️ {jogo['Time Casa']}", value=jogo['Placar Casa'])
        with col2:
            st.markdown("<h1 style='text-align: center; margin-top: 15px;'>X</h1>", unsafe_allow_html=True)
        with col3:
            st.metric(label=f"✈️ {jogo['Time Visitante']}", value=jogo['Placar Visitante'])

        st.divider()

        # --- Exibição das Estatísticas ---
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
