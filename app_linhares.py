import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# Configuração da Página
st.set_page_config(page_title="Relatório Comercial - Supermercado Linhares", layout="wide")

# --- 1. CARREGAMENTO DE DADOS (Baseado no Case) ---
def load_data():
    # Vendas por Loja
    df_lojas = pd.DataFrame({
        'Loja': ['Aldeota', 'Parangaba', 'Messejana'],
        'Q1_2025': [12000000, 8500000, 6800000],
        'Q2_2025': [9800000, 7200000, 6600000],
        'Meta_Q2': [11500000, 8000000, 6700000]
    })
    
    # Vendas por Categoria
    df_cat = pd.DataFrame({
        'Categoria': ['Alimentos Básicos', 'Bebidas', 'Higiene & Limpeza', 'Perecíveis'],
        'Q1': [10500000, 6000000, 5500000, 5300000],
        'Q2': [9000000, 4800000, 5300000, 4500000]
    })
    
    # Canais de Venda
    df_canais = pd.DataFrame({
        'Indicador': ['Clientes Físico', 'Clientes App', 'Ticket Médio Físico', 'Ticket Médio App', 'Entregas Atrasadas (%)'],
        'Q1': [420000, 60000, 65, 110, 7],
        'Q2': [390000, 55000, 60, 95, 14]
    })
    
    return df_lojas, df_cat, df_canais

df_lojas, df_cat, df_canais = load_data()

# --- 2. HEADER E KPI'S PRINCIPAIS ---
st.title("📊 Inteligência Comercial: Análise de Desempenho Q2/2025")
st.markdown("---")

total_q1 = df_lojas['Q1_2025'].sum()
total_q2 = df_lojas['Q2_2025'].sum()
meta_global = df_lojas['Meta_Q2'].sum()
var_global = (total_q2 - total_q1) / total_q1 * 100

col1, col2, col3, col4 = st.columns(4)
col1.metric("Faturamento Q2", f"R$ {total_q2/1e6:.1f}M", f"{var_global:.1f}% vs Q1")
col2.metric("Atingimento de Meta", f"{(total_q2/meta_global)*100:.1f}%", f"Gap R$ {(total_q2-meta_global)/1e6:.1f}M", delta_color="inverse")
col3.metric("Entregas Atrasadas", f"{df_canais.iloc[4]['Q2']}%", f"+{df_canais.iloc[4]['Q2'] - df_canais.iloc[4]['Q1']}% pts", delta_color="inverse")
col4.metric("Ticket Médio Digital", f"R$ {df_canais.iloc[3]['Q2']}", f"-13.6%", delta_color="inverse")

# --- 3. ANÁLISE DESCRITIVA (PERGUNTA 1) ---
st.header("1. Análise Descritiva: Onde ocorreram as quedas?")
tab1, tab2 = st.tabs(["Performance por Unidade", "Performance por Categoria"])

with tab1:
    # Gráfico de Barras Agrupadas: Real vs Meta
    fig_lojas = go.Figure()
    fig_lojas.add_trace(go.Bar(x=df_lojas['Loja'], y=df_lojas['Q2_2025'], name='Realizado Q2', marker_color='#1f77b4'))
    fig_lojas.add_trace(go.Bar(x=df_lojas['Loja'], y=df_lojas['Meta_Q2'], name='Meta Q2', marker_color='#ff7f0e'))
    fig_lojas.update_layout(title="Volume Realizado vs Meta por Loja", barmode='group')
    st.plotly_chart(fig_lojas, use_container_width=True)
    
    st.write("**Destaque:** A unidade **Aldeota** representa o maior gap nominal (R$ 1,7M abaixo da meta)[cite: 8].")

with tab2:
    # Variação por Categoria
    df_cat['Variacao'] = (df_cat['Q2'] - df_cat['Q1']) / df_cat['Q1'] * 100
    fig_cat = px.bar(df_cat, x='Categoria', y='Variacao', color='Variacao', 
                     title="Variação Percentual de Vendas por Categoria (Q1 vs Q2)",
                     labels={'Variacao': 'Queda %'}, color_continuous_scale='RdYlGn')
    st.plotly_chart(fig_cat, use_container_width=True)
    st.write("**Destaque:** Categorias de **Bebidas (-20%)** e **Perecíveis (-15,1%)** foram as mais afetadas[cite: 10].")

# --- 4. ANÁLISE DIAGNÓSTICA (PERGUNTA 2) ---
st.header("2. Análise Diagnóstica: Causas e Correlações")
col_diag1, col_diag2 = st.columns(2)

with col_diag1:
    st.subheader("Fatores Externos")
    st.info("""
    - **Concorrência:** Campanha agressiva do 'Super Bom Preço' em Bebidas e Carnes[cite: 14].
    - **Sazonalidade/Clima:** Aumento de 12% nos preços de Hortifrúti impactando Perecíveis[cite: 14].
    """)

with col_diag2:
    st.subheader("Fatores Internos")
    st.warning("""
    - **Logística:** Dobro de entregas atrasadas (de 7% para 14%)[cite: 12].
    - **App:** Queda de R$ 15 no Ticket Médio Digital e alta de 25% nas reclamações[cite: 12, 14].
    """)

# --- 5. PROPOSTAS DE SOLUÇÃO (PERGUNTA 3) ---
st.header("3. Propostas de Solução e Plano de Ação")

# Matriz de Ação
st.markdown("""
| Ação | Prioridade | Objetivo |
| :--- | :--- | :--- |
| **Combos de Churrasco/Bebidas** | Alta | Recuperar faturamento de Perecíveis e Bebidas contra concorrência. |
| **Força-Tarefa Logística** | Crítica | Reduzir atrasos para < 7% para recuperar confiança no App. |
| **Dia do Hortifrúti (Ofertas)** | Média | Gerar fluxo de loja física apesar da alta de preços do setor. |
""")

st.subheader("KPIs para Monitoramento (Dashboard Recomendado)")
st.write("""
1. **OTIF (On-Time In-Full):** Percentual de entregas perfeitas no canal digital.
2. **Price Index (PI):** Comparação diária de preços em Bebidas e Carnes vs Concorrente.
3. **NPS (Net Promoter Score):** Monitoramento do sentimento do cliente após a entrega.
""")