import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
import numpy as np
import locale
from PIL import Image

# --- Configuração da Página ---
# Deve ser a primeira chamada no script
st.set_page_config(
    page_title="Análise de Timeline Musical",
    page_icon="🎶",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuração de locale para lidar com datas em português
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    st.warning("Não foi possível definir o locale 'pt_BR.UTF-8'. As datas podem não ser exibidas corretamente.")
    try:
        locale.setlocale(locale.LC_TIME, 'portuguese')
    except locale.Error:
        st.error("Não foi possível definir o locale para português. As datas podem causar erros.")

# --- Título Geral do Aplicativo ---
st.title("🎶 Análise de Streams por Timeline")
st.markdown("""
Este painel combina a visualização de streams ao longo do tempo com a análise da tendência de popularidad.
""")

#caminho_img = Image.open("nome_na_bio.jpeg")

#st.image(caminho_img,width = 300)

# --- Seção 1: Gráfico de Timeline de Streams ---
st.header("1. Streams Nome na Bio Longo do Tempo")
st.markdown("**Track Score:**" \
"- índice de popularidade global da faixa, consolidando dados de plataformas como Spotify   \nYouTube, TikTok, Airplay, SoundCloud, Pandora e Shazam")

# Caminho do arquivo da timeline
file_path_timeline = 'Nome na Bio-timeline.xlsx'

try:
    df_timeline = pd.read_excel(file_path_timeline)
    df_timeline['date'] = pd.to_datetime(df_timeline['date'])
    df_timeline = df_timeline.sort_values('date')

    fig_timeline = px.area(
        df_timeline,
        x='date',
        y='streams',
        title='Streams Diários',
        labels={'date': 'Data', 'streams': 'Contagem de Streams'}
    )

    fig_timeline.update_layout(xaxis_rangeslider_visible=True)
    st.plotly_chart(fig_timeline, use_container_width=True)

except FileNotFoundError:
    st.error(f"Erro: O arquivo '{file_path_timeline}' não foi encontrado.")
except KeyError:
    st.error("Erro: O arquivo de timeline não contém as colunas esperadas ('date', 'streams').")
except Exception as e:
    st.error(f"Ocorreu um erro ao processar o arquivo de timeline: {e}")


# --- Seção 2: Gráfico de Popularidade com Regressão Linear ---
st.header("2. Popularidade com Regressão Linear")

# Caminho do arquivo de popularidade
file_path_popularity = 'Chartmetric_Score.xlsx'

try:
    df_popularity = pd.read_excel(file_path_popularity)
    df_popularity.columns = ['data', 'valor']
    df_popularity['data'] = pd.to_datetime(df_popularity['data'], format='%d de %b. de %Y')
    df_popularity = df_popularity.sort_values('data')

    max_value = df_popularity['valor'].max()
    if max_value > 0:
        df_popularity['valor_percentual'] = (df_popularity['valor'] / max_value) * 100
    else:
        df_popularity['valor_percentual'] = 0

    X = np.array(df_popularity['data'].apply(lambda x: x.toordinal())).reshape(-1, 1)
    y = df_popularity['valor_percentual'].values
    model = LinearRegression()
    model.fit(X, y)
    y_pred = model.predict(X)

    fig_popularity = go.Figure()
    fig_popularity.add_trace(go.Scatter(
        x=df_popularity['data'],
        y=df_popularity['valor_percentual'],
        mode='lines+markers',
        name='Popularidade (Dados Originais)',
        line=dict(color='royalblue')
    ))
    fig_popularity.add_trace(go.Scatter(
        x=df_popularity['data'],
        y=y_pred,
        mode='lines',
        name='Tendência (Regressão Linear)',
        line=dict(color='red', dash='dash')
    ))
    fig_popularity.update_layout(
        title='Popularidade da Métrica ao Longo do Tempo',
        xaxis_title='Data',
        yaxis_title='Popularidade (%)',
        yaxis_range=[0, 105],
        legend_title_text='Legenda'
    )
    st.plotly_chart(fig_popularity, use_container_width=True)

    st.markdown("""
    ---
    **Análise do Gráfico:**
    - A **linha azul** representa o valor diário da popularidade, escalado para uma porcentagem.
    - A **linha vermelha tracejada** é a regressão linear, que suaviza as flutuações e mostra a direção geral (tendência) dos dados.
    """)

except FileNotFoundError:
    st.error(f"Erro: O arquivo '{file_path_popularity}' não foi encontrado.")
except KeyError:
    st.error("Erro: O arquivo de popularidade não contém as colunas esperadas ('data', 'valor').")
except Exception as e:
    st.error(f"Ocorreu um erro ao processar o arquivo de popularidade: {e}")