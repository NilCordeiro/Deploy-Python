import streamlit as st

# Configuração da página
st.set_page_config(page_title="Plano de Ação – Analista de Dados", layout="wide")

st.title("🎯 Plano de Atuação – Analista de Dados Marketing Vybbe")

# Barra lateral com navegação
section = st.sidebar.radio("Navegar para:", [
    "🔍 Imersão no Negócio",
    "📊 Ecossistema de Dados",
    "📈 Definição de KPIs",
    "⚙️ Automação & Relatórios",
    "🔁 Rotina & Ciclo Contínuo",
    "💡 Entrega de Insights",
    "📚 Cultura de Dados",
    "📦 Entregáveis"
])

if section == "🔍 Imersão no Negócio":
    st.header("🔍 1. Imersão no Negócio (Primeiros 15 dias)")
    st.markdown("""
- Reuniões com as equipes:
    - Marketing
    - Gestão de Artistas
    - Distribuição Digital
- Mapeamento dos canais:
    - Instagram, TikTok, YouTube Music, Spotify,Deezer etc.
- Estudo dos públicos-alvo
- **Acesso às ferramentas:** Meta Business Suite, Spotify for Artists, Google Analytics...
    """)

elif section == "📊 Ecossistema de Dados":
    st.header("📊 2. Montagem do Ecossistema de Dados")
    st.markdown("""
- Criação de dashboards integrados com:
    - Redes sociais
    - Tráfego de sites
    - Anúncios pagos (Google Ads / Meta Ads)
    - Plataformas de streaming (Spotify, YouTube, Deezer)
- Ferramentas:
    - Ecxel,Power BI, APIs + Python
    """)

elif section == "📈 Definição de KPIs":
    st.header("📈 3. Definição de KPIs por Área")
    
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🎵 Lançamentos")
        st.markdown("""
- Streams por dia / semana / mês
- Ouvintes mensais
- Inclusões em playlists
        """)

        st.subheader("📢 Publicidade")
        st.markdown("""
- ROI das campanhas
- CPA (Custo por Aquisição)
- CTR (Click Through Rate)
- CAC (Custo de Aquisição por Cliente)
        """)

    with col2:
        st.subheader("📱 Redes Sociais")
        st.markdown("""
- Crescimento de seguidores
- Engajamento por post
- Alcance orgânico vs pago
- Melhores horários
        """)


elif section == "⚙️ Automação & Relatórios":
    st.header("⚙️ 4. Automação de Relatórios e Alertas")
    st.markdown("""
- Criação de alertas automáticos:
    - Baixo engajamento
    - ROI insatisfatório
- Relatórios:
    - Semanais e mensais por artista
    - Comparativos entre artistas
    """)

elif section == "🔁 Rotina & Ciclo Contínuo":
    st.header("🔁 5. Rotina de Melhoria Contínua")
    st.markdown("""
- Reuniões periódicas:
    - Semanais com marketing
    - Mensais com gestão artística
- Análises pontuais para:
    - Turnês
    - Lançamentos
    - Parcerias
    """)

elif section == "💡 Entrega de Insights":
    st.header("💡 6. Entrega de Insights Acionáveis")
    st.markdown("""
Exemplos:
- Melhor horário para postar Reels: 18h–22h
- YouTube Ads com ROI 70% maior que Instagram para o artista Y
- Bastidores geram 30% mais engajamento em Reels
    """)

elif section == "📚 Cultura de Dados":
    st.header("📚 7. Cultura de Dados Interna")
    st.markdown("""
- Mini-manual de uso dos dashboards
- Capacitação dos times de artistas e marketing
- Reuniões mensais com foco em leitura de dados
    """)

elif section == "📦 Entregáveis":
    st.header("📦 Entregáveis Esperados – Primeiros 90 Dias")

    st.table({
        "Prazo": ["30 dias", "60 dias", "90 dias"],
        "Entregas": [
            "Diagnóstico inicial + dashboards básicos",
            "Estrutura de KPI por artista + relatórios periódicos",
            "Automação + cultura de dados em andamento"
        ]
    })

    


### 💡 Como rodar o app:
