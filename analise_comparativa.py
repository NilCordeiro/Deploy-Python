import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import tempfile
from PIL import Image
from datetime import datetime

# --- CONFIGURAÇÃO E AUTENTICAÇÃO ---
def get_gspread_client():
    google_sheets_creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    if not google_sheets_creds_json:
        st.error("A variável de ambiente GOOGLE_SHEETS_CREDENTIALS não foi encontrada.")
        return None
    
    try:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as temp_creds_file:
            temp_creds_file.write(google_sheets_creds_json)
            temp_path = temp_creds_file.name
        
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(temp_path, scopes)
        client = gspread.authorize(creds)
        os.remove(temp_path)
        return client
    except Exception as e:
        st.error(f"Erro ao autenticar: {e}")
        return None

@st.cache_data
def load_data_comparativo(sheet_index):
    client = get_gspread_client()
    if not client: return pd.DataFrame()
    
    try:
        planilha = client.open(title="2025_Charts")
        worksheet = planilha.get_worksheet(sheet_index)
        
        # Ajuste de colunas específico para a planilha de índice 5
        if sheet_index == 5:
            expected_headers = ['DATA', 'Rank', 'uri', 'Artista', 'Música', 'source', 'peak_rank', 'previous_rank', 'days_on_chart', 'Corte charts', 'Data de Pico', 'Streams']
            data = worksheet.get_all_records(expected_headers=expected_headers)
        else:
            data = worksheet.get_all_records()
            
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Erro ao carregar aba {sheet_index}: {e}")
        return pd.DataFrame()

# --- FUNÇÕES DE FORMATAÇÃO ---
def format_br_number(number):
    try:
        num_int = int(float(str(number).replace('.', '').replace(',', '')))
        return f"{num_int:,}".replace(",", "X").replace(".", ",").replace("X", ".")
    except: return str(number)


st.set_page_config(page_title='Comparativo Vybbe', layout="wide")

st.header("📊 Comparativo de Performance Faixas Top 200 Spotify Brasil")
st.markdown("""
Bem-vindo à ferramenta de **Inteligência Competitiva**. Este módulo permite:
* **Comparar Performance Temporal:** Analise até 3 músicas simultaneamente no Ranking ou Streams.
* **Análise de Lançamento:** O gráfico de barras foca no impacto inicial (primeiro registro) de cada faixa.
* **Filtros Personalizados:** Ajuste o período para identificar tendências e picos de audiência.
""")
st.write("---")

df = load_data_comparativo(5)

if not df.empty:
    # Tratamento de Dados
    df['DATA'] = pd.to_datetime(df['DATA'], format="%d/%m/%Y",errors = 'coerce')
    df['Streams_Num'] = pd.to_numeric(df['Streams'].astype(str).str.replace('.', '').replace(',', ''), errors='coerce')
    df['Streams_Formatado'] = df['Streams_Num'].apply(format_br_number)

    # Seleção de Músicas
    qtd = st.radio("Quantidade de músicas para comparar:", [2, 3], horizontal=True)
    musicas = sorted(df['Música'].unique())
    
    col1, col2, col3 = st.columns(3)
    m1 = col1.selectbox("Música 1", musicas, index=0)
    m2 = col2.selectbox("Música 2", musicas, index=1)
    m3 = col3.selectbox("Música 3", musicas, index=2) if qtd == 3 else None
    
    selecionadas = [m for m in [m1, m2, m3] if m]
    df_comp = df[df['Música'].isin(selecionadas)]

    # Filtro de Datas
    c_date1, c_date2 = st.columns(2)
    start = c_date1.date_input("Data Início", df_comp['DATA'].min())
    end = c_date2.date_input("Data Fim", df_comp['DATA'].max())

    df_filtered = df_comp[(df_comp['DATA'].dt.date >= start) & (df_comp['DATA'].dt.date <= end)]

    # 1. GRÁFICO DE LINHA
    st.subheader("Evolução Temporal")
    tipo = st.radio("Visualizar por:", ["Ranking", "Streams"], horizontal=True)
    
    y_col = "Rank" if tipo == "Ranking" else "Streams_Num"
    text_col = "Rank" if tipo == "Ranking" else "Streams_Formatado" 

    fig_line = px.line(df_filtered, x='DATA', y=y_col, color='Música', text=text_col, line_shape='spline', markers=True)
    fig_line.update_traces(textposition='top center')
    if tipo == "Ranking": fig_line.update_layout(yaxis=dict(autorange="reversed"))
    
    st.plotly_chart(fig_line, use_container_width=True)

    # 2. GRÁFICO DE BARRAS (Primeira data de entrada)
    st.write("---")
    st.subheader("🚀 Impacto Data de Lançamento Faixa")
    
    # Filtra apenas a primeira data de cada música no período selecionado
    df_primeira = df_filtered.sort_values('DATA').groupby('Música').head(1)
    
    fig_bar = px.bar(df_primeira, x='Música', y='Streams_Num', color='Música', text='Streams_Formatado',
                     title="Volume de Streams Data de Lançamento",)
    fig_bar.update_traces(textposition='outside')
    fig_bar.update_layout(showlegend=False)
    st.plotly_chart(fig_bar, use_container_width=True)

else:
    st.error("Não foi possível carregar os dados da planilha. Verifique os Secrets no Streamlit Cloud.")


st.write("---")

