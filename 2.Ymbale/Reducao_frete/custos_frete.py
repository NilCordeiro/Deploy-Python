
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(

    page_title= 'Logística Ymbale',
    layout= 'wide'
)

st.title('🚚 Projeto Redução Custos Frete')
st.markdown("Reduzir os custos totais com fretes por meio da otimização de processos logísticos,"
"<br>renegociação de contratos, uso de tecnologia e melhoria na consolidação de cargas.", unsafe_allow_html=True)

st.write('Objetivos:')

st.markdown("""


    -  Aumentar a taxa de ocupação dos veículos de transporte.
    -  Diminuir o número de entregas parciais.
    -  Estabelecer KPIs logísticos para monitoramento contínuo.

""")

st.write('Pontos observado em análise durante acompanhemento frete transportadora.')
st.write('**Pontos observados.**')

st.markdown("""
      - Definir metas, exemplo redução de x%
      - Limite do valor frete por região.
      - Frete todos os dias para as regiões com maior percentual
      - Reentregas

""")
st.write('**Benefívios esperados**')
st.markdown(
    """
    - Economia financeira
    - Maior controle e visibilidade das operações logística
    - Melhoria no atendimento ao cliente
    - Redução dos desperdicios e retrabalho

""")

data = pd.read_excel('custo_frete.xlsx')

frete = data[data['DEV_FRETE'] == 'FRETE']
df_reg = frete.groupby('REGIÃO')[['VALOR A RECEBER','VALOR TOTAL DA MERCADORIA']].sum().reset_index()
df_reg['Porc'] = (df_reg['VALOR A RECEBER']/df_reg['VALOR TOTAL DA MERCADORIA']) * 100
grafico_reg = df_reg.sort_values('Porc',ascending = True)

st.sidebar.image('ymbale.png',width= 200,clamp=200)

regia = frete['REGIÃO'].unique()
regiao = st.sidebar.selectbox('Região',regia)
df_filter = frete[frete['REGIÃO'] == regiao]

qtd_pedidos = df_filter['NOTA FISCAL'].count()
fig_reg = px.bar(

    grafico_reg,
    x = 'Porc',
    y = 'REGIÃO',
    title = 'Gráfico Custo Frete por Região',
    width = 1150,
    height = 500,
    hover_data=['REGIÃO', 'Porc'], 
    color='Porc',
    text_auto = True     
)

total_por = frete.groupby(['ESTADO DESTINO','REGIÃO'])[['VALOR A RECEBER','VALOR TOTAL DA MERCADORIA']].sum().reset_index().sort_values('VALOR A RECEBER',ascending = False)
total_por['Pocent'] = (total_por['VALOR A RECEBER']/total_por['VALOR TOTAL DA MERCADORIA']) * 100


grafico = total_por.groupby(['ESTADO DESTINO','REGIÃO'])['Pocent'].sum().reset_index().sort_values('Pocent',ascending = True)

df_estados = grafico[grafico['REGIÃO'] == regiao ]


# Grafico por estado
fig = px.bar(
    df_estados,
    x = 'Pocent',
    y = 'ESTADO DESTINO',
    title = 'Gráfico Custo frete por Estado',
    width = 1150,
    height = 500,
    hover_data=['ESTADO DESTINO', 'Pocent'], 
    color='Pocent',
    text_auto = True 
)


#Grafico por região
st.plotly_chart(fig_reg)


st.header('Demontração frete por estado')
st.write('Estados Região ',regiao) 
st.plotly_chart(fig)

fig_scatter = px.scatter(
    df_filter,x = 'VALOR TOTAL DA MERCADORIA',y = 'VALOR A RECEBER',
    size = 'VALOR TOTAL DA MERCADORIA',hover_data = 'VALOR A RECEBER',
    marginal_x="histogram", marginal_y="rug",trendline="ols"
    )

st.write('Região: ',regiao)
st.write('Total pedido ',qtd_pedidos)
st.plotly_chart(fig_scatter)