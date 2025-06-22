import streamlit as st
import requests
import pandas as pd
from datetime import datetime


# ==========================
# Funções
# ==========================

def buscar_jogo(times_procurados):
    url = "https://api-web.365scores.com/web/games/current"
    params = {"sport": 1, "lang": "pt", "timezone": "-3"}
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, params=params, headers=headers)
    if response.status_code != 200:
        return None

    jogos = response.json().get("games", [])
    for jogo in jogos:
        time_casa = jogo["homeTeam"]["name"]
        time_visitante = jogo["awayTeam"]["name"]

        if any(t.lower() in time_casa.lower() for t in times_procurados) or \
           any(t.lower() in time_visitante.lower() for t in times_procurados):

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

            return dados_basicos

    return None


def buscar_estatisticas(game_id):
    url = f"https://api-web.365scores.com/web/games/{game_id}/stats"
    params = {"lang": "pt"}
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, params=params, headers=headers)
    if response.status_code != 200:
        return None

    stats = response.json()

    estatisticas = {}
    for item in stats.get("stats", []):
        nome = item.get("name", "Desconhecido")
        home_value = item.get("homeValue", 0)
        away_value = item.get("awayValue", 0)

        estatisticas[nome] = {
            "Casa": home_value,
            "Visitante": away_value
        }

    return estatisticas


# ==========================
# Streamlit UI
# ==========================

st.set_page_config(page_title="Painel de Jogo ao Vivo", layout="centered")

st.title("⚽ Painel do Jogo - Botafogo x PSG")

times = ["Botafogo", "PSG"]

if st.button("🔄 Atualizar Dados"):
    jogo = buscar_jogo(times)

    if jogo:
        st.subheader(f"🕑 {jogo['Data/Hora']} | {jogo['Status']}")

        st.markdown(f"""
        ## 🏟️ {jogo['Time Casa']} {jogo['Placar Casa']} x {jogo['Placar Visitante']} {jogo['Time Visitante']}
        """)

        stats = buscar_estatisticas(jogo["Game ID"])

        if stats:
            df_stats = pd.DataFrame(stats).T.reset_index()
            df_stats.columns = ["Estatística", jogo['Time Casa'], jogo['Time Visitante']]

            st.subheader("📊 Estatísticas da Partida")
            st.dataframe(df_stats, use_container_width=True)

        else:
            st.warning("⚠️ Estatísticas não encontradas no momento.")

    else:
        st.error("❌ Nenhum jogo encontrado com esses times.")
else:
    st.info("Clique no botão acima para carregar os dados do jogo.")
