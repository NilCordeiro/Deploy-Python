import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import plotly_express as px

st.set_page_config( page_title="Grafico de dispersão em python")
st.header("Gráfico de Dispersão em Python")

st.write('Como fazer gráfico de Dispersão em python com plotly.')

st.write('Importamos um dataset muito utilizado para essa demonstração, dataset tips')

tips = sns.load_dataset('tips')

tips.columns = ['total conta','gorjeta','sexo','fumante','dia','tempo','tamanho']
tips['sexo'] = tips['sexo'].replace(['female','male'],['masculino','feminio'])

st.dataframe(tips)

st.subheader('Scatter Plot com Plotly Express.')

st.write('**Scatter Plot** - Grafico de Dispersão, cada ponto de dados é representado com um ponto marcador, a localização é dada pelas colunas x e y')

scatter = px.scatter( data_frame=tips, x = 'total conta',y = 'gorjeta')

st.plotly_chart(scatter)

st.write('Atribuição de uma variável para matriz mapeará seus níveis para a cor dos pontos:')

scatter_hue = px.scatter(tips,x = 'total conta',y = 'gorjeta',color = 'sexo')

st.plotly_chart(scatter_hue)

st.subheader('Configurando cor com nomes de colunas')

st.write('Os gráficos de dispersão com marcadores circulares de tamanho variável são frequentemente conhecidos como gráficos de bolhas. Observe que os dados de cor e tamanho são adicionados às informações de foco.')

st.plotly_chart(px.scatter(tips,x = 'total conta',y = 'gorjeta',color = 'sexo',size = 'tamanho'))

st.write('**A cor pode ser contínua como segue, ou discreta/categórica como acima.**')

scatter_color = px.scatter(tips,x = 'total conta',y = 'gorjeta',color= 'tamanho')

st.plotly_chart(scatter_color)

st.subheader('Facetamento')
st.write('Os gráficos de Dispersão suportam facetamento')

scatter_facet = px.scatter(tips,x = 'total conta',y = 'gorjeta',color = 'fumante',facet_col='sexo',facet_row='tempo')

st.plotly_chart(scatter_facet)

st.subheader('Regressão linear e outras linhas de tendência')
st.write('Os gráficos de dispersão suportam linhas de tendência lineares e não lineares.')

scatter_tendencia = px.scatter(tips,x = 'total conta',y='gorjeta',color = 'sexo',size = 'gorjeta',trendline="ols")

st.plotly_chart(scatter_tendencia)



