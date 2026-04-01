import pandas as pd
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import plotly.express as px
from dotenv import load_dotenv
import os
import json
import tempfile
from PIL import Image
import pytz

st.set_page_config(page_title='Vybbe Charts', layout="wide", initial_sidebar_state="expanded")

load_dotenv()

try:
    TZ = pytz.timezone('America/Sao_Paulo')
except ImportError:
    TZ = None

google_sheets_creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
planilha_completa = None

if not google_sheets_creds_json:
    st.error("A variável de ambiente GOOGLE_SHEETS_CREDENTIALS não foi encontrada.")
else:
    temp_file_name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as temp_creds_file:
            temp_creds_file.write(google_sheets_creds_json)
            temp_file_name = temp_creds_file.name

        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(filename=temp_file_name, scopes=scopes)
        client = gspread.authorize(creds)
        planilha_completa = client.open(title="2025_Charts")
        os.remove(temp_file_name)
        temp_file_name = None
    except Exception as e:
        st.error(f"Erro ao autenticar com o Google Sheets: {e}")
    finally:
        if temp_file_name and os.path.exists(temp_file_name):
            os.remove(temp_file_name)

@st.cache_data
def load_data(sheet_index):
    if not planilha_completa:
        return pd.DataFrame()

    try:
        worksheet = planilha_completa.get_worksheet(sheet_index)
        if sheet_index == 5:
            expected_headers = ['DATA', 'Rank', 'uri', 'Artista', 'Música', 'source', 'peak_rank', 'previous_rank', 'days_on_chart', 'Corte charts', 'Data de Pico', 'Streams']
            data = worksheet.get_all_records(expected_headers=expected_headers)
        else:
            data = worksheet.get_all_records()

        df = pd.DataFrame(data)
        return df
    except gspread.exceptions.APIError as e:
        st.error(f"Erro ao acessar a planilha (sheet {sheet_index}): {e}")
        return pd.DataFrame()

SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
try:
    # AQUI ESTAVA O ERRO DE DIGITAÇÃO: SpotifyClientClientCredentials -> SpotifyClientCredentials
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET))
except Exception as e:
    st.error(f"Erro ao autenticar com a API do Spotify: {e}")
    sp = None

@st.cache_data
def get_artist_image(artist_name):
    if sp is None:
        return None
    try:
        # Pega apenas o primeiro artista se houver vírgula
        primary_artist_name = artist_name.split(',')[0].strip() if isinstance(artist_name, str) else artist_name
        
        results = sp.search(q='artist:' + primary_artist_name, type='artist', limit=1)
        if results['artists']['items'] and results['artists']['items'][0]['images']:
            return results['artists']['items'][0]['images'][0]['url']
    except Exception as e:
        st.error(f"Erro ao buscar imagem do artista {artist_name}: {e}")
    return None

@st.cache_data
def get_album_image(album_name):
    if sp is None:
        return None
    try:
        results = sp.search(q='album:' + album_name, type='album', limit=1)
        if results and 'albums' in results and results['albums']['items']:
            album_item = results['albums']['items'][0]
            if 'images' in album_item and album_item['images']:
                return album_item['images'][0]['url']
    except Exception as e:
        st.error(f"Erro ao buscar imagem do álbum {album_name}: {e}")
    return None
    
@st.cache_data
def get_track_album_image(track_name, artist_name):
    if sp is None:
        return None
        
    image_url = None
    
    # 1. Tenta buscar a imagem do álbum da faixa
    try:
        primary_artist_name = artist_name.split(',')[0].strip() if isinstance(artist_name, str) else artist_name
        
        results = sp.search(q=f'track:{track_name} artist:{primary_artist_name}', type='track', limit=1)
        if results and 'tracks' in results and results['tracks']['items']:
            track_item = results['tracks']['items'][0]
            if 'album' in track_item and 'images' in track_item['album'] and track_item['album']['images']:
                image_url = track_item['album']['images'][0]['url']
                
    except Exception as e:
        # Erro de busca no Spotify (ex: música não existe ou problema de API)
        pass # Continua para o fallback
        
    # 2. Se a imagem do álbum falhou ou não foi encontrada, usa a imagem do artista (FALLBACK)
    if not image_url:
        image_url = get_artist_image(artist_name)
        
    return image_url

# CORREÇÃO: Formatação robusta para Padrão BR (Ponto Milhar)
def format_br_number(number):
    """Preserva os dígitos, limpa e formata o número para o padrão BR (ponto milhar)."""
    try:
        # 1. Limpeza
        number_str = str(number).strip()
        
        number_pure = number_str.replace('.', '').replace(',', '')
        
        # Se for um float (e.g. 2319970.0), converte para int para evitar casa decimal
        if '.' in number_str: # Se a string original ou limpa ainda tiver ponto (sinal de decimal no BR ou separador no US)
             num_int = int(float(number_pure))
        else:
             num_int = int(number_pure)
        
        # 3. Formatação
        # Formata o número com separadores de milhar do sistema (vírgula no US)
        s = f"{num_int:,}"
        
        # 4. Ajuste BR: troca separadores (vírgula por ponto, ponto por vírgula)
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        
        return s
        
    except (ValueError, TypeError):
        # Retorna o valor original como string se a conversão falhar
        return str(number)
        
def format_br_date(date_str):
    try:
        date_obj = datetime.strptime(date_str, "%d/%m/%Y").date()
        return date_obj.strftime('%d/%m/%Y')
    except (ValueError, TypeError):
        return str(date_str)

def update_date_range(key_suffix, df_original, item_col, date_col_name):
    """Callback para recalcular e armazenar as datas min/max do item selecionado no session_state."""
    
    selected_item = st.session_state[f"selectbox_{key_suffix}"]
    df_filtered = df_original[df_original[item_col] == selected_item].copy()
    
    if not df_filtered.empty:
        min_date = df_filtered[date_col_name].min().date()
        max_date = df_filtered[date_col_name].max().date()
    else:
        current_date = datetime.now(TZ).date() if TZ else datetime.today().date()
        min_date = current_date
        max_date = current_date

    st.session_state[f'start_date_state_{key_suffix}'] = min_date
    st.session_state[f'end_date_state_{key_suffix}'] = max_date


def display_chart(sheet_index, section_title, item_type, key_suffix, chart_type, platform):
    st.header(section_title)
    df = load_data(sheet_index)

    if df.empty:
        st.info(f"😪 Nenhum dado disponível para o chart de {section_title.replace('Global', 'Brasil').replace('Songs', 'Músicas').replace('Artists', 'Artistas').replace('Albums', 'Álbums')}.")
        st.write("---")
        return

    item_col = 'Música' if 'Música' in df.columns else ('Álbum' if 'Álbum' in df.columns else ('Faixa' if 'Faixa' in df.columns else 'Artista'))
    date_col_name = 'DATA' if 'DATA' in df.columns else 'Data'
    
    if date_col_name not in df.columns:
        st.warning("Coluna de data não encontrada. Verifique se o nome da coluna é 'DATA' ou 'Data'.")
        st.write("---")
        return
        
    df[date_col_name] = pd.to_datetime(df[date_col_name], format="%d/%m/%Y")
    
    df_display = pd.DataFrame()
    selected_date_display = None
    
    today_br = datetime.now(TZ).date() if TZ else datetime.today().date()
    yesterday = today_br - timedelta(days=1)
    
    if chart_type == 'daily':
        latest_date_available = df[date_col_name].max().date()
        
        show_date_selector = st.checkbox("Pesquisar por datas anteriores?", key=f"checkbox_{key_suffix}")
        
        if show_date_selector:
            selected_date = st.date_input("Selecione a Data para Visualização", latest_date_available, key=f"date_input_{key_suffix}")
            df_display = df[df[date_col_name].dt.date == selected_date].copy()
            selected_date_display = selected_date
        else:
            df_display = df[df[date_col_name].dt.date == yesterday].copy()
            selected_date_display = yesterday

        if df_display.empty and not show_date_selector:
            st.info(f"😪 Nenhum dado encontrado para os artistas Vybbe no chart de {yesterday.strftime('%d/%m/%y')}.")
            
    elif chart_type == 'weekly':
        latest_date_available = df[date_col_name].max().date()
        
        show_date_selector = st.checkbox("Pesquisar por datas anteriores?", key=f"checkbox_{key_suffix}")

        if show_date_selector:
            selected_date = st.date_input("Selecione a Data para Visualização", latest_date_available, key=f"date_input_{key_suffix}")
            df_display = df[df[date_col_name].dt.date == selected_date].copy()
            selected_date_display = selected_date
        else:
            df_display = df[df[date_col_name].dt.date == latest_date_available].copy()
            selected_date_display = latest_date_available
            
        if not df_display.empty:
            st.markdown(f"**Semana Última Atualização:** {selected_date_display.strftime('%d/%m/%Y')}")
        else:
            if not show_date_selector:
                st.info(f"😪 Nenhum dado disponível para o chart de {section_title} na data {latest_date_available.strftime('%d/%m/%Y')}.")
            elif selected_date_display:
                st.info(f"Nenhum dado encontrado para a data selecionada: {selected_date_display.strftime('%d/%m/%Y')}.")
            
    if not df_display.empty:
        
        total_artistas = df_display['Artista'].nunique()
        if item_type == 'o artista':
            col_artists = st.columns(1)
            with col_artists[0]:
                st.metric(label="Total de Artistas", value=total_artistas)
        else:
            total_items = df_display[item_col].nunique() if item_col in df_display.columns else 0
            col_artists, col_tracks = st.columns(2)
            with col_artists:
                st.metric(label="Total de Artistas", value=total_artistas)
            with col_tracks:
                st.metric(label=f"Total de {item_col}s", value=total_items)
        
        st.write("---")

        if 'Daily Top Songs' in section_title:
            if selected_date_display:
                st.markdown(f"**Dados do dia:** {selected_date_display.strftime('%d/%m/%Y')}") 
            corte_charts_value = df_display['Corte charts'].iloc[0] if 'Corte charts' in df_display.columns and not df_display.empty else "N/A"
            if 'Daily Top Songs Brasil' in section_title and corte_charts_value != 'N/A':
                st.markdown(f"**Corte do Chart:** {corte_charts_value}")
        else:
            if selected_date_display:
                st.markdown(f"**Dados do dia:** {selected_date_display.strftime('%d/%m/%Y')}")

        # --- Visualização da Tabela ---
        has_streams = platform == 'Spotify' and 'Streams' in df_display.columns and not df_display['Streams'].isna().all() and "Artists" not in section_title and "Albums" not in section_title
        has_peak_date = 'Data de Pico' in df_display.columns or 'Data do Pico' in df_display.columns
        has_views_youtube = platform == 'Youtube' and 'Visualizações Semanais' in df_display.columns and not df_display['Visualizações Semanais'].isna().all()

        column_ratios = [0.5, 3.5, 0.7, 0.7, 0.9]
        if has_streams: column_ratios.append(1.5)
        if has_views_youtube: column_ratios.append(1.5)
        if has_peak_date: column_ratios.append(1.2)
        
        header_cols = st.columns(column_ratios)
        
        # Determina o cabeçalho correto para a coluna de tempo (Dias ou Semanas)
        time_header = "Dias no Charts"
        if "Weekly" in section_title or "Semanal" in section_title:
            time_header = "Semanas no Charts"
            
        # CORREÇÃO APLICADA: Renomeação dos cabeçalhos das colunas
        with header_cols[0]: st.markdown("<b>#</b>", unsafe_allow_html=True)
        with header_cols[1]: 
            header_text = "ARTISTA" if "Top Artists" in section_title or "Top Artistas" in section_title else ("ÁLBUM" if "Top Albums" in section_title else "MÚSICA/FAIXA")
            st.markdown(f"<b>{header_text}</b>", unsafe_allow_html=True)
        with header_cols[2]: st.markdown("<b>Pico</b>", unsafe_allow_html=True)
        with header_cols[3]: st.markdown("<b>Anterior</b>", unsafe_allow_html=True)
        with header_cols[4]: st.markdown(f"<b>{time_header}</b>", unsafe_allow_html=True) # Cabeçalho dinâmico

        col_index = 5
        if has_streams:
            with header_cols[col_index]: st.markdown("<b>Streams</b>", unsafe_allow_html=True)
            col_index += 1
        if has_views_youtube:
            with header_cols[col_index]: st.markdown("<b>Visualizações</b>", unsafe_allow_html=True)
            col_index += 1
        if has_peak_date:
            with header_cols[col_index]: st.markdown("<b>Data de Pico</b>", unsafe_allow_html=True)

        st.markdown("---")

        # Define a largura padrão para a imagem (PADRONIZADO PARA 200 PIXELS)
        image_width = 200 

        for index, row in df_display.iterrows():
            rank = row.get('Rank', 'N/A')
            item_name = row.get(item_col, '').strip()
            artist_name_col = 'Artista' if 'Artista' in df_display.columns else 'Criador'
            artist_name = row.get(artist_name_col, 'N/A').strip()
            peak_rank = row.get('peak_rank', 'N/A')
            previous_rank = row.get('previous_rank', 'N/A')
            
            # CORREÇÃO APLICADA: Busca por 'Weeks_on_chart' para charts semanais (Semanal ou Weekly)
            streak = row.get('days_on_chart', 'N/A')
            if "Weekly" in section_title or "Semanal" in section_title: 
                # Tenta 'Weeks_on_chart' (YouTube) ou 'weeks_on_chart' (Spotify)
                streak = row.get('Weeks_on_chart', row.get('weeks_on_chart', 'N/A'))


            streams = "N/A"
            if platform == 'Spotify' and 'Streams' in row:
                streams = row.get('Streams', 'N/A')
            elif platform == 'Youtube' and 'Visualizações Semanais' in row:
                streams = row.get('Visualizações Semanais', 'N/A')

            peak_date = row.get('Data de Pico') or row.get('Data do Pico', 'N/A')
            if peak_date != 'N/A': peak_date = format_br_date(peak_date)

            image_url = None
            
            # Lógica de fallback para imagens
            if item_type == 'o artista': image_url = get_artist_image(artist_name)
            elif item_type == 'o álbum': image_url = get_album_image(item_name)
            elif item_type in ['a música', 'a faixa']: 
                image_url = get_track_album_image(item_name, artist_name)
                
            cols = st.columns(column_ratios)
            with cols[0]: st.markdown(f"<p style='font-size:20px; font-weight:bold;'>{rank}</p>", unsafe_allow_html=True)
            with cols[1]:
                track_cols = st.columns([0.7, 3])
                with track_cols[0]:
                    if image_url: st.image(image_url, width=image_width, caption="")
                    else: st.write("🖼️")
                with track_cols[1]:
                    st.markdown(f"**{item_name}**")
                    if item_type != 'o artista': st.markdown(f"<span style='color: gray; font-size: 16px;'>{artist_name}</span>", unsafe_allow_html=True)
            
            with cols[2]: st.markdown(f"<span style='font-size: 16px;'>{peak_rank}</span>", unsafe_allow_html=True)
            with cols[3]: st.markdown(f"<span style='font-size: 16px;'>{previous_rank}</span>", unsafe_allow_html=True)
            with cols[4]: st.markdown(f"<span style='font-size: 16px;'>{streak}</span>", unsafe_allow_html=True)
            
            col_index = 5
            if has_streams or has_views_youtube:
                with cols[col_index]:
                    display_value = streams if streams == 'N/A' else format_br_number(streams)
                    st.markdown(f"<span style='font-size: 16px;'>{display_value}</span>", unsafe_allow_html=True)
                col_index += 1
            if has_peak_date:
                with cols[col_index]: st.markdown(f"<span style='font-size: 16px;'>{peak_date}</span>", unsafe_allow_html=True)
            
            st.markdown("---")
            
    else:
        if selected_date_display: st.info(f"Nenhum dado encontrado para a data selecionada: {selected_date_display.strftime('%d/%m/%Y')}.")
        st.write("---")

    # --- Início do Gráfico de Análise ---
    
    df['Mês'] = df[date_col_name].dt.strftime('%B')
    df['Ano'] = df[date_col_name].dt.year
    df_unique_items = sorted(df[item_col].unique())

    selectbox_key = f"selectbox_{key_suffix}"
    
    if selectbox_key not in st.session_state and df_unique_items:
        st.session_state[selectbox_key] = df_unique_items[0]
        update_date_range(key_suffix, df, item_col, date_col_name)

    initial_index = df_unique_items.index(st.session_state.get(selectbox_key, df_unique_items[0])) if df_unique_items else 0
    
    selected_item = st.selectbox(
        f"Selecione {item_type} para análise do ranking", 
        df_unique_items,
        index=initial_index, 
        key=selectbox_key,
        on_change=update_date_range, 
        args=(key_suffix, df, item_col, date_col_name)
    )

    start_date_state_key = f'start_date_state_{key_suffix}'
    end_date_state_key = f'end_date_state_{key_suffix}'
    
    if start_date_state_key not in st.session_state: update_date_range(key_suffix, df, item_col, date_col_name)
        
    df_filtered = df[df[item_col] == selected_item].copy()

    st.write("---")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Data de Início", 
            value=st.session_state[start_date_state_key],
            min_value=st.session_state[start_date_state_key],
            max_value=st.session_state[end_date_state_key],
            key=f"start_date_{key_suffix}"
        )
    with col2:
        end_date = st.date_input(
            "Data de Fim", 
            value=st.session_state[end_date_state_key],
            min_value=st.session_state[start_date_state_key],
            max_value=st.session_state[end_date_state_key],
            key=f"end_date_{key_suffix}"
        )
        
    df_chart = df_filtered[(df_filtered[date_col_name].dt.date >= start_date) & (df_filtered[date_col_name].dt.date <= end_date)].copy()

    y_axis_col = "Rank"
    y_axis_title = "Posição no Ranking"
    y_tickformat = None

    if item_type in ["a música", "a faixa"]:
        chart_options = ["Ranking"]
        if "Streams" in df_chart.columns and not df_chart['Streams'].isna().all(): chart_options.append("Streams")
        if "Visualizações Semanais" in df_chart.columns and not df_chart['Visualizações Semanais'].isna().all(): chart_options.append("Visualizações")
            
        if len(chart_options) > 1:
            chart_type_radio = st.radio("Tipo de visualização:", chart_options, key=f"radio_chart_type_{key_suffix}")
            
            if chart_type_radio == "Ranking": y_axis_col = "Rank"; y_axis_title = "Posição no Ranking"
            elif chart_type_radio == "Streams": y_axis_col = "Streams"; y_axis_title = "Número de Streams"
            elif chart_type_radio == "Visualizações": y_axis_col = "Visualizações Semanais"; y_axis_title = "Número de Visualizações"

    if y_axis_col in ["Streams", "Visualizações Semanais"] and y_axis_col in df_chart.columns:
        
        # --- CORREÇÃO DE BUG: Conversão e Formatação para o Gráfico ---
        # 1. Converte a coluna para string e limpa os separadores de milhar (ponto e vírgula) do GSheets/BR
        df_chart['temp_numeric'] = df_chart[y_axis_col].astype(str).str.replace('.', '', regex=False).str.replace(',', '', regex=False)
        
        # 2. Converte para float para ser o eixo Y do Plotly
        df_chart[y_axis_col] = pd.to_numeric(df_chart['temp_numeric'], errors='coerce')
        
        # 3. Usa a função corrigida `format_br_number` para criar a coluna de texto formatado (para o hover/text)
        df_chart['y_axis_formatted'] = df_chart[y_axis_col].apply(lambda x: format_br_number(x))

        # Remove a coluna temporária
        df_chart = df_chart.drop(columns=['temp_numeric'])
        # --- FIM DA CORREÇÃO DE BUG ---

        y_tickformat = None
    
    text_col = 'y_axis_formatted' if 'y_axis_formatted' in df_chart.columns else y_axis_col

    image_url = None
    artist_name = ''
    if item_type == 'o artista': artist_name = selected_item
    elif item_type in ['a música', 'a faixa']:
        artist_name_series = df[df[item_col] == selected_item]['Artista']
        if not artist_name_series.empty: artist_name = artist_name_series.iloc[0].split(',')[0].strip()
    
    if platform == 'Youtube':
        artist_for_image = artist_name.split(',')[0].strip() if isinstance(artist_name, str) else artist_name
        image_url = get_artist_image(artist_for_image)
    elif item_type == 'o artista': image_url = get_artist_image(selected_item)
    elif item_type in ['a música', 'a faixa']:
        if artist_name:
            image_url = get_track_album_image(selected_item, artist_name)
            if not image_url: image_url = get_artist_image(artist_name)
    elif item_type == 'o álbum': image_url = get_album_image(selected_item)
    
    if image_url:
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="{image_url}" width=60 style="border-radius: 50%;">
            <h3>{y_axis_title} de '{selected_item}' ao Longo do Tempo</h3>
        </div>
        """, unsafe_allow_html=True)
    else: st.header(f"{y_axis_title} de '{selected_item}' ao Longo do Tempo")
        
    fig = px.line(df_chart, x=date_col_name, y=y_axis_col, text=text_col, line_shape='spline')
    
    # Se for Streams ou Visualizações, remove os pontos para que o número não seja exibido com casas decimais no hover.
    if y_axis_col in ["Streams", "Visualizações Semanais"]:
         fig.update_traces(texttemplate='%{text}', textposition='top center')
    else:
         fig.update_traces(textposition='top center')
         
    
    yaxis_config = {'title': y_axis_title}
    if y_axis_col == 'Rank': yaxis_config['autorange'] = 'reversed'
    if y_tickformat: yaxis_config['tickformat'] = y_tickformat
    
    fig.update_layout(xaxis_title="Dia", yaxis=yaxis_config)
    st.plotly_chart(fig)
    st.write("---")

def display_weekly_global_chart(global_sheet_index, global_section_title, global_item_type, global_key_suffix):
    st.header(global_section_title)
    df = load_data(global_sheet_index)

    if df.empty:
        st.info(f"😪 Nenhum dado disponível para o chart de {global_section_title}.")
        st.write("---")
        return

    item_col = 'Música' if 'Música' in df.columns else ('Álbum' if 'Álbum' in df.columns else 'Artista')
    date_col_name = 'Data' if 'Data' in df.columns else 'DATA'
    df[date_col_name] = pd.to_datetime(df[date_col_name], format="%d/%m/%Y")
    
    today_br = datetime.now(TZ).date() if TZ else datetime.today().date()
    yesterday = today_br - timedelta(days=1)
    
    latest_date_available = df[date_col_name].max().date()
    
    show_date_selector = st.checkbox("Pesquisar por datas anteriores?", key=f"checkbox_{global_key_suffix}")
    
    df_display = pd.DataFrame()
    selected_date_display = None
    
    if show_date_selector:
        selected_date = st.date_input("Selecione a Data para Visualização", latest_date_available, key=f"date_input_{global_key_suffix}")
        df_display = df[df[date_col_name].dt.date == selected_date].copy()
        selected_date_display = selected_date
    else:
        df_display = df[df[date_col_name].dt.date == latest_date_available].copy()
        selected_date_display = latest_date_available

    if not df_display.empty:
        st.markdown(f"**Dados do dia:** {selected_date_display.strftime('%d/%m/%Y')}")
    else:
        if not show_date_selector:
            st.info(f"😪 Nenhum dado encontrado para os artistas Vybbe no chart de {yesterday.strftime('%d/%m/%Y')}.")
        elif selected_date_display:
            st.info(f"Nenhum dado encontrado para a data selecionada: {selected_date_display.strftime('%d/%m/%Y')}.")
        st.write("---")
        return

    # --- Visualização da Tabela ---
    
    # --- Início do Gráfico de Análise ---
    
    df_unique_items = sorted(df[item_col].unique())
    
    selectbox_key = f"selectbox_{global_key_suffix}"
    
    if selectbox_key not in st.session_state and df_unique_items:
        st.session_state[selectbox_key] = df_unique_items[0]
        update_date_range(global_key_suffix, df, item_col, date_col_name)

    initial_index = df_unique_items.index(st.session_state.get(selectbox_key, df_unique_items[0])) if df_unique_items else 0
    
    selected_item = st.selectbox(
        f"Selecione {global_item_type} para análise do ranking", 
        df_unique_items,
        index=initial_index, 
        key=selectbox_key,
        on_change=update_date_range, 
        args=(global_key_suffix, df, item_col, date_col_name)
    )

    start_date_state_key = f'start_date_state_{global_key_suffix}'
    end_date_state_key = f'end_date_state_{global_key_suffix}'
    
    if start_date_state_key not in st.session_state: update_date_range(global_key_suffix, df, item_col, date_col_name)
        
    df_filtered = df[df[item_col] == selected_item].copy()
    
    st.write("---")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Data de Início", 
            value=st.session_state[start_date_state_key],
            min_value=st.session_state[start_date_state_key],
            max_value=st.session_state[end_date_state_key],
            key=f"start_date_{global_key_suffix}"
        )
    with col2:
        end_date = st.date_input(
            "Data de Fim", 
            value=st.session_state[end_date_state_key],
            min_value=st.session_state[start_date_state_key],
            max_value=st.session_state[end_date_state_key],
            key=f"end_date_{global_key_suffix}"
        )
        
    df_chart = df_filtered[(df_filtered[date_col_name].dt.date >= start_date) & (df_filtered[date_col_name].dt.date <= end_date)].copy()

    y_axis_col = "Rank"
    y_axis_title = "Posição no Ranking"
    
    image_url = None
    if global_item_type == 'o artista': image_url = get_artist_image(selected_item)
    elif global_item_type in ['a música', 'a faixa']:
        artist_name_series = df[df[item_col] == selected_item]['Artista']
        if not artist_name_series.empty:
            artist_name = artist_name_series.iloc[0].split(',')[0].strip()
            image_url = get_track_album_image(selected_item, artist_name)
            if not image_url: image_url = get_artist_image(artist_name)
    elif global_item_type == 'o álbum': image_url = get_album_image(selected_item)
    
    if image_url:
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="{image_url}" width=60 style="border-radius: 50%;">
            <h3>{y_axis_title} de '{selected_item}' ao Longo do Tempo</h3>
        </div>
        """, unsafe_allow_html=True)
    else: st.header(f"{y_axis_title} de '{selected_item}' ao Longo do Tempo")
        
    fig = px.line(df_chart, x=date_col_name, y=y_axis_col, text=y_axis_col, line_shape='spline')
    fig.update_traces(textposition='top center')
    
    yaxis_config = {'title': y_axis_title}
    if y_axis_col == 'Rank': yaxis_config['autorange'] = 'reversed'
    
    fig.update_layout(xaxis_title="Dia", yaxis=yaxis_config)
    st.plotly_chart(fig)
    st.write("---")
@st.cache_data
def generate_whatsapp_message():
    """Busca dados dos Daily Charts de múltiplas plataformas e formata uma mensagem detalhada para WhatsApp."""
    
    # Mapeamento: (sheet_index, chart_name_prefix, item_col, platform_name, is_youtube)
    daily_charts_config = [
        (5, "Spotify - Diário Top Músicas Brasil", 'Música', 'Spotify', False),
        (9, "Spotify - Diário Viral Músicas Brasil", 'Música', 'Spotify', False), 
        (4, "Spotify - Diário Top Músicas Global", 'Música', 'Spotify', False),
        (8, "Spotify - Diário Viral Músicas Global", 'Música', 'Spotify', False),
        (18, "YouTube - Top Vídeos Diários Brasil", 'Música', 'YouTube', True),
        (12, "Deezer - Diário Top Músicas", 'Música', 'DEEZER', False),
        (13, "Amazon - Diário Top Músicas Amazon", 'Música', 'Amazon', False),
        (14, "Apple Music - Diário Top Músicas Apple Music", 'Música', 'Apple Music', False),
    ]

    message_parts = []
    
    today_br = datetime.now(TZ).date() if TZ else datetime.today().date()
    # yesterday é usada apenas para fins de exibição da data, o filtro usa a data real do dado
    yesterday = today_br - timedelta(days=1) 
    
    for sheet_index, chart_name_prefix, item_col, platform_name, is_youtube in daily_charts_config:
        df = load_data(sheet_index)

        if df.empty:
            continue
            
        date_col_name = 'DATA' if 'DATA' in df.columns else 'Data'
        df[date_col_name] = pd.to_datetime(df[date_col_name], format="%d/%m/%Y", errors='coerce')
        df = df.dropna(subset=[date_col_name])
        
        if df.empty:
            continue
        
        latest_date_available = df[date_col_name].max().date()
        date_to_filter = latest_date_available 
        
        df_display = df[df[date_col_name].dt.date == date_to_filter].copy()

        if df_display.empty:
            continue
            
        # Garante ordenação numérica e usa o total de itens presentes
        df_display['Rank_num'] = pd.to_numeric(df_display['Rank'], errors='coerce')
        df_display = df_display.sort_values(by='Rank_num', ascending=True).dropna(subset=['Rank_num'])
        
        total_items = len(df_display)
        
        # --- CABEÇALHO ---
        # Tópicos principais em negrito (usando *)
        chart_title = chart_name_prefix.split(' - ')[-1]
        message_parts.append(f"🎶 *{platform_name}* - *{chart_title}*")
        message_parts.append(f"📅 *Dados de:* {date_to_filter.strftime('%d/%m/%Y')}")

        corte_charts_value = df_display['Corte charts'].iloc[0] if 'Corte charts' in df_display.columns and not df_display.empty else None
        if corte_charts_value:
            message_parts.append(f"✂ *Corte:* {format_br_number(corte_charts_value)}")
            
        message_parts.append(f"---------------------------------------")
        message_parts.append(f"*Chart Completo* ({total_items} item{'s' if total_items != 1 else ''}) -")
        
        # --- DETALHES DAS MÚSICAS ---
        for _, row in df_display.iterrows():
            rank = row.get('Rank', 'N/A')
            item_name = row.get(item_col, '').strip()
            artist_col = 'Artista' if 'Artista' in row else 'Criador'
            artist_name = row.get(artist_col, 'N/A').strip()
            
            # Métricas
            streams = row.get('Streams', None)
            views = row.get('Visualizações Semanais', None)
            previous_rank = row.get('previous_rank', 'N/A')
            peak_rank = row.get('peak_rank', 'N/A')
            
            # Verifica se é chart Weekly (para dias ou semanas)
            days_on_chart = row.get('days_on_chart', row.get('weeks_on_chart', row.get('Weeks_on_chart', 'N/A')))
            days_label = "Dias" if sheet_index in [4, 5, 8, 9, 12, 13, 14, 18, 19] else "Semanas"
            
            # Linha Principal (Negrito no Rank e Título da Música)
            stream_info = ""
            if streams:
                formatted_streams = format_br_number(streams)
                stream_info = f" ({formatted_streams} Streams)"
            elif views:
                formatted_views = format_br_number(views)
                stream_info = f" ({formatted_views} Visualizações)"
                
            # Formato: 7. Pela Última Vez - Ao Vivo - Grupo Menos É Mais, NATTAN (1.135.516 Streams)
            message_parts.append(f"*{rank}. {item_name}* - {artist_name}{stream_info}")
            
            # Linha Secundária (Detalhamento)
            # Formato: Ant.: 7 | Pico: 2 | Dias: 58
            message_parts.append(f"   Ant.: {previous_rank} | Pico: {peak_rank} | {days_label}: {days_on_chart}")
            
        message_parts.append(f"---------------------------------------")

    message_parts.append(f"\n*Acesse o dashboard completo para mais detalhes:*")
    message_parts.append(f"https://vybbestreams.streamlit.app/")

    return "\n".join(message_parts)

# --- FUNÇÃO PARA GERAR MENSAGEM SEMANAL (COMPLETA) ---
@st.cache_data
def generate_weekly_whatsapp_message():
    """Busca dados dos Weekly Charts do Spotify e Youtube e formata uma mensagem detalhada para WhatsApp."""
    
    # Mapeamento: (sheet_index, chart_name_prefix, item_col, platform_name, is_youtube)
    weekly_charts_config = [
        # Spotify Weekly
        (6, "Spotify - Semanal Top Músicas Global", 'Música', 'Spotify', False),
        (7, "Spotify - Semanal Top Músicas Brasil", 'Música', 'Spotify', False),
        (2, "Spotify - Semanal Top Artistas Global", 'Artista', 'Spotify', False),
        (3, "Spotify - Semanal Top Artistas Brasil", 'Artista', 'Spotify', False),
        (10, "Spotify - Semanal Top Álbuns Global", 'Álbum', 'Spotify', False),
        (11, "Spotify - Semanal Top Álbuns Brasil", 'Álbum', 'Spotify', False),
        # Youtube Weekly
        # CORRIGIDO: Usando 'Música' conforme solicitado, em vez de 'Faixa'
        (16, "YouTube - Top Faixas Semanal Brasil", 'Música', 'YouTube', True), 
        (15, "YouTube - Top Artistas Semanal Brasil", 'Artista', 'YouTube', True),
    ]

    message_parts = []
    
    today_br = datetime.now(TZ).date() if TZ else datetime.today().date()
    
    for sheet_index, chart_name_prefix, item_col, platform_name, is_youtube in weekly_charts_config:
        df = load_data(sheet_index)

        if df.empty:
            continue
            
        date_col_name = 'DATA' if 'DATA' in df.columns else 'Data'
        df[date_col_name] = pd.to_datetime(df[date_col_name], format="%d/%m/%Y", errors='coerce')
        df = df.dropna(subset=[date_col_name])
        
        if df.empty:
            continue
        
        latest_date_available = df[date_col_name].max().date()
        date_to_filter = latest_date_available 
        
        df_display = df[df[date_col_name].dt.date == date_to_filter].copy()

        if df_display.empty:
            continue
            
        # Garante ordenação numérica e usa o total de itens presentes
        df_display['Rank_num'] = pd.to_numeric(df_display['Rank'], errors='coerce')
        df_display = df_display.sort_values(by='Rank_num', ascending=True).dropna(subset=['Rank_num'])
        
        total_items = len(df_display)
        
        # --- CABEÇALHO ---
        chart_title = chart_name_prefix.split(' - ')[-1]
        message_parts.append(f"\n🎶 *{platform_name}* - *{chart_title}*")
        message_parts.append(f"📅 *Dados de:* {date_to_filter.strftime('%d/%m/%Y')}")

        message_parts.append(f"---------------------------------------")
        message_parts.append(f"*Chart Completo* ({total_items} item{'s' if total_items != 1 else ''}) -")
        
        # --- DETALHES DOS ITENS ---
        for _, row in df_display.iterrows():
            rank = row.get('Rank', 'N/A')
            
            # Extração robusta do item_name: Tenta o item_col configurado, se não funcionar, tenta 'Música' ou 'Faixa'
            item_name = str(row.get(item_col, '')).strip()
            if not item_name and item_col != 'Música' and 'Música' in row:
                 item_name = str(row.get('Música', '')).strip()
            if not item_name and item_col != 'Faixa' and 'Faixa' in row:
                 item_name = str(row.get('Faixa', '')).strip()

            
            # Artista só é incluído se o item_col não for Artista/Criador
            artist_name = ""
            artist_col = 'Artista' if 'Artista' in row else 'Criador'
            if item_col not in ['Artista', 'Criador', 'Álbum']:
                 artist_name = row.get(artist_col, 'N/A').strip()
            
            # Métricas
            streams = row.get('Streams', None)
            views = row.get('Visualizações Semanais', None)
            previous_rank = row.get('previous_rank', row.get('Previous_Rank', 'N/A'))
            peak_rank = row.get('peak_rank', row.get('Peak_Rank', 'N/A'))
            
            # Para charts Semanais, forçamos a busca por semanas (usando Weeks_on_chart ou weeks_on_chart)
            weeks_on_chart = row.get('Weeks_on_chart', row.get('weeks_on_chart', 'N/A'))
            
            # Linha Principal (Negrito no Rank e Título do Item)
            stream_info = ""
            if streams and item_col not in ['Artista', 'Álbum']: # Só exibe streams para Músicas/Faixas
                formatted_streams = format_br_number(streams)
                stream_info = f" ({formatted_streams} Streams)"
            elif views and item_col not in ['Artista', 'Álbum']:
                formatted_views = format_br_number(views)
                stream_info = f" ({formatted_views} Visualizações)"
                
            
            # Linha: *RANK. NOME_DO_ITEM* - ARTISTA (Streams/Views)
            # A linha principal agora garante que o item_name (nome da música) seja o primeiro elemento negrito
            display_item_name = item_name if item_name else "N/A"
            
            artist_display = f" - {artist_name}" if artist_name else ""
            
            message_parts.append(f"*{rank}. {display_item_name}*{artist_display}{stream_info}")
            
            # Linha Secundária (Detalhamento)
            message_parts.append(f"   Ant.: {previous_rank} | Pico: {peak_rank} | Semanas: {weeks_on_chart}")
            
        message_parts.append(f"---------------------------------------")

    # --- RODAPÉ DA MENSAGEM ---
    message_parts.append(f"\nAcesse o dashboard completo para mais detalhes:")
    message_parts.append(f"https://vybbestreams.streamlit.app/")

    return "\n".join(message_parts)

# --- Estrutura principal do aplicativo (Não alterada) ---
try:
    imagem_logo = Image.open('logo_Charts.jpg')
    st.image(imagem_logo)
except FileNotFoundError:
    st.header("Logo 'habbla.jpg' não encontrada.")
st.write("")

import streamlit as st
st.markdown(
    '<a href="https://ana-comparativa.streamlit.app/" target="_blank">Clique aqui para ir para a Análise Comparativa Faixas Top 200 Spotify</a>',
    unsafe_allow_html=True
)

#st.title('🎶 Vybbe Dashboard Streaming')
st.markdown("Bem-vindo(a) ao seu portal de inteligência de mercado musical. Explore as tendências e rankings das principais plataformas de streaming, com dados atualizados e análises detalhadas para auxiliar na sua estratégia artística.")
st.write("---")

st.sidebar.title("Menu Plataformas")
plataforma_selecionada = st.sidebar.radio(
    "Selecione a Plataforma:", 
    ["Spotify", "Youtube", "Deezer", "Amazon", "Apple Music"]
)

if plataforma_selecionada == "Spotify":
    menu_spotify = ["Daily Charts", "Weekly Charts"]
    spotify_charts_selection = st.sidebar.radio("Selecione o tipo de chart:", menu_spotify)
    
    if spotify_charts_selection == "Daily Charts":
        with st.sidebar.expander("Spotify Daily", expanded=True):
            opcao_selecionada = st.radio("Selecione uma opção:", ["Daily Top Songs", "Daily Top Artists", "Daily Viral Songs"], key="daily_menu_radio")
        
        if opcao_selecionada == "Daily Top Songs":
            sub_opcao_songs = st.radio("Selecione uma região:", ("Global", "Brasil"), key="sub_menu_songs")
            if sub_opcao_songs == "Global":
                display_chart(4, "Daily Top Songs Global", "a música", "songs_global", 'daily', 'Spotify')
            elif sub_opcao_songs == "Brasil":
                display_chart(5, "Daily Top Songs Brasil", "a música", "songs_brasil", 'daily', 'Spotify')
        elif opcao_selecionada == "Daily Top Artists":
            sub_opcao_artists = st.radio("Selecione uma região:", ("Global", "Brasil"), key="sub_menu_artists")
            if sub_opcao_artists == "Global":
                display_chart(0, "Daily Top Artists Global", "o artista", "artists_global", 'daily', 'Spotify')
            elif sub_opcao_artists == "Brasil":
                display_chart(1, "Daily Top Artists Brasil", "o artista", "artists_brasil", 'daily', 'Spotify')
        elif opcao_selecionada == "Daily Viral Songs":
            sub_opcao_viral = st.radio("Selecione uma região:", ("Global", "Brasil"), key="sub_menu_viral")
            if sub_opcao_viral == "Global":
                display_chart(8, "Daily Viral Songs Global", "a música", "viral_songs_global", 'daily', 'Spotify')
            elif sub_opcao_viral == "Brasil":
                display_chart(9, "Daily Viral Songs Brasil", "a música", "viral_songs_brasil", 'daily', 'Spotify')

    elif spotify_charts_selection == "Weekly Charts":
        with st.sidebar.expander("Spotify Weekly", expanded=True):
            opcao_selecionada = st.radio("Selecione uma opção:", ["Weekly Top Songs", "Weekly Top Artists", "Weekly Top Albums"], key="weekly_menu_radio")

        if opcao_selecionada == "Weekly Top Songs":
            sub_opcao_songs_weekly = st.radio("Selecione uma região:", ("Global", "Brasil"), key="sub_menu_songs_weekly")
            if sub_opcao_songs_weekly == "Global":
                display_weekly_global_chart(6, "Weekly Top Songs Global", "a música", "weekly_songs_global")
            elif sub_opcao_songs_weekly == "Brasil":
                display_chart(7, "Weekly Top Songs Brasil", "a música", "weekly_songs_brasil", 'weekly', 'Spotify')
        elif opcao_selecionada == "Weekly Top Artists":
            sub_opcao_artists_weekly = st.radio("Selecione uma região:", ("Global", "Brasil"), key="sub_menu_artists_weekly")
            if sub_opcao_artists_weekly == "Global":
                display_weekly_global_chart(2, "Weekly Top Artists Global", "o artista", "weekly_artists_global")
            elif sub_opcao_artists_weekly == "Brasil":
                display_chart(3, "Weekly Top Artists Brasil", "o artista", "weekly_artists_brasil", 'weekly', 'Spotify')
        elif opcao_selecionada == "Weekly Top Albums":
            sub_opcao_albums_weekly = st.radio("Selecione uma região:", ("Global", "Brasil"), key="sub_menu_albums_weekly")
            if sub_opcao_albums_weekly == "Global":
                display_weekly_global_chart(10, "Weekly Top Albums Global", "o álbum", "weekly_albums_global")
            elif sub_opcao_albums_weekly == "Brasil":
                display_chart(11, "Weekly Top Albums Brasil", "o álbum", "weekly_albums_brasil", 'weekly', 'Spotify')

elif plataforma_selecionada == "Youtube":
    with st.sidebar.expander("YouTube Charts", expanded=True):
        opcao_selecionada_youtube = st.radio("Selecione uma opção:", ["Top Videos Diários", "Top Shorts Diários", "Top Clipes Semanal", "Top Faixas Semanal", "Top Artistas Semanal"], key="youtube_menu_radio")
    
    if opcao_selecionada_youtube == "Top Videos Diários":
        sheet_index = 18
        display_chart(sheet_index, "Top Videos Diários Brasil", "a música", "videos_diarios_br", 'daily', 'Youtube')

    elif opcao_selecionada_youtube == "Top Shorts Diários":
        sheet_index = 19
        display_chart(sheet_index, "Músicas mais tocadas nos Shorts neste dia", "a música", "shorts_diarios_br", 'daily', 'Youtube')

    elif opcao_selecionada_youtube == "Top Clipes Semanal":
        sheet_index = 17
        display_chart(sheet_index, "Top Clipes Semanal Brasil", "a música", "clipes_semanal_br", 'weekly', 'Youtube')

    elif opcao_selecionada_youtube == "Top Faixas Semanal":
        sheet_index = 16
        display_chart(sheet_index, "Top Faixas Semanal Brasil", "a faixa", "faixas_semanal_br", 'weekly', 'Youtube')

    elif opcao_selecionada_youtube == "Top Artistas Semanal":
        sheet_index = 15
        display_chart(sheet_index, "Top Artistas Semanal Brasil", "o artista", "artistas_semanal_br", 'weekly', 'Youtube')

elif plataforma_selecionada == "Deezer":
    display_chart(sheet_index=12, section_title="Daily Top Songs Deezer", item_type="a música", key_suffix="songs_deezer", chart_type='daily', platform='Deezer')

elif plataforma_selecionada == "Amazon":
    display_chart(sheet_index=13, section_title="Daily Top Songs Amazon", item_type="a música", key_suffix="songs_amazon", chart_type='daily', platform='Amazon')

elif plataforma_selecionada == "Apple Music":
    display_chart(sheet_index=14, section_title="Daily Top Songs Apple Music", item_type="a música", key_suffix="songs_apple", chart_type='daily', platform='Apple Music')

st.write("---")
st.markdown("Desenvolvido com Python e Streamlit, este painel é uma ferramenta essencial para a análise de mercado musical. Explore as tendências e rankings das principais plataformas de streaming, com dados atualizados e análises detalhadas para auxiliar na sua estratégia artística.")

# --- NOVO BLOCO: Botão de Download da Mensagem (Próximo ao rodapé) ---
# st.radio para seleção de tipo de chart
chart_type_download = st.radio(
    "Selecione o tipo de dado para download:", 
    ("Diário", "Semanal"),
    key="download_chart_type"
)

today_br = datetime.now(TZ).date() if TZ else datetime.today().date()
today_formatted = today_br.strftime('%Y%m%d')

if chart_type_download == "Diário":
    download_content = generate_whatsapp_message()
    file_name = f"Daily_Charts_Vybbe_{today_formatted}.txt"
    label = "📲 Baixar Charts Diários (WhatsApp .txt)"
else:
    download_content = generate_weekly_whatsapp_message()
    file_name = f"Weekly_Charts_Vybbe_{today_formatted}.txt"
    label = "📲 Baixar Charts Semanais (WhatsApp .txt)"

st.download_button(
    label=label,
    data=download_content,
    file_name=file_name,
    mime="text/plain",
    help="Clique para baixar os rankings consolidados em um arquivo de texto para facilitar o compartilhamento no WhatsApp."
)
st.write("---")
# Rodapé existente
col1, col2 = st.columns([1, 4])

with col1:
    try:
        rodape_image = Image.open('habbla_rodape.jpg')
        st.image(rodape_image, width=110)
    except FileNotFoundError:
        st.write("Logo rodapé não encontrada.")

with col2:
    st.markdown(
        """
        <div style='font-size: 12px; color: gray;'>
            Desenvolvido pela equipe de dados da <b>Habbla</b> | © 2025 Habbla Marketing<br>
            Versão 1.0.0 | Atualizado em: Setembro/2025<br>
            <a href="mailto:nil@habbla.ai">nil@habbla.ai</a> |
            <a href="https://vybbe.com.br" target="_blank">Site Institucional</a>
        </div>
        """,
        unsafe_allow_html=True
    )