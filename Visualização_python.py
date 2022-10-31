
from re import L
from turtle import width
import streamlit as st
import pandas as pd
import plotly.express as px
from PIL import Image

st.set_page_config(page_title="Excel Plotter")

logo = Image.open('logo.JPG')
st.image(logo)

st.title("PLOTEASY DEMONSTRAÇÕES 📊")
st.subheader('Faça upload do arquivo 🚀')

st.write('Análise do dataset de gorjetas')

upload_file = st.file_uploader('Carregar arquivo',type = 'csv')

if upload_file:
    st.markdown('---')
    data = pd.read_csv(upload_file)
    st.subheader('Dataset Tips')
    st.write('**Descrição do dataset:**')
    
    st.markdown('Em um restaurante, um servidor de comida registrou os seguintes dados em todos os clientes tomers que serviram durante um intervalo de dois meses e meio no início de 1990. O restaurante, localizado em um shopping de subúrbio, fazia parte de uma rede e serviu um cardápio variado. Em observância à lei local, o restaurante ofereceu para sentar em uma seção de não-fumantes para os clientes que o solicitaram. Cada registro inclui um dia e hora, e juntos, eles mostram o servidor horário de trabalho.')

    st.dataframe(data)
    #agrupando_coluna = st.selectbox('O que você gostaria de análisar?',('sex','day'))

    #--GROUPBY DATAFRAME
    fig = px.bar(data,x = 'sexo',y = 'total conta',color = 'janta/almoço',height=400)
    fig2 = px.bar(data,x = 'sexo',y='total conta',color ='fumante',barmode = 'group',height = 400)
    fig3 = px.scatter(data,x = 'total conta',y = 'gorjeta',color = 'sexo',size = 'gorjeta',height = 400)
    histplot = px.histogram(data,x = 'total conta',y ='gorjeta',color = 'sexo',marginal = 'rug',hover_data = data.columns)

    st.subheader('Graficos de Barras')

    st.write('Barra') 
    st.plotly_chart(fig)

    st.write('Barra') 
    st.plotly_chart (fig2)

    st.subheader('Plot Distribuição')

    st.write('Scatter Plot')
    st.plotly_chart(fig3)
    st.write('DistPlot')
    st.plotly_chart(histplot)  


st.markdown('**Precisando de uma aplicação como essa em sua empresa? não perca tempo e entre em contato pelo nosso WhatSapp (85)9 8576-6920.**')