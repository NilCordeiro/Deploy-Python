import numpy as np
import pandas as pd
import plotly.express as px
import fdb
import streamlit as st
from datetime import date
import locale

locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

dia = date.today()
hoje = dia.strftime('%d/%m/%y')

st.set_page_config(
    page_title="Faturamento",
    page_icon="📈",
    layout="wide"
)

con = fdb.connect(dsn='192.168.15.22:C:\Database\Producao WMS\WMSYMBALE.FDB',user='NIL', password='logistica123')
cur = con.cursor()

cur.execute(""" 
    
    select
        wms_pedido.ped_data,
        wms_pedido.ped_codigo Pedido,
        sum(wms_pedido.ped_total) as R$_Total,
        wms_configuracao.conf_empresa Empresa
    from
        wms_pedido

    inner join
        wms_configuracao on wms_pedido.conf_codigo = wms_configuracao.conf_codigo
    where
        wms_pedido.ped_data between '01.01.2025 00:00:00' and '31.12.2025 23:59:59'
        and
            wms_pedido.cfop_codigo in (6101,5101,1201,6109,6102,5102,1202)
        and
            wms_pedido.cfop_codigo not in (8888,5949,1010,2201,5910,6911,6915)
        and
            wms_pedido.ped_status = 'IMPORTACAO COMPLETA'
        and
            wms_pedido.ped_excluido is null 

    group by
        wms_pedido.ped_data,
        wms_pedido.ped_codigo,
        wms_pedido.ped_total,
        wms_configuracao.conf_empresa
  
""")

st.title("📊 Faturamento Diário")


data = cur.fetchall()

df = pd.DataFrame(data)
df.columns = ['DATA','PEDIDO','FATURAMENTO','EMPRESA']

df['MES'] = df['DATA'].dt.month_name(locale='pt_BR')
df['NUMERO MES'] = df['DATA'].dt.month

df['DATA'] = df['DATA'].dt.strftime('%d/%m/%y')

df['MES'] = df['MES'].apply(lambda x: x.encode('utf-8', errors='ignore').decode('utf-8'))


# Filtro dataset
df_filter = df[df['DATA'] == hoje]

# Médidas
faturamento = df_filter['FATURAMENTO'].sum()

faturamento_dia  = locale.currency(faturamento, grouping=True)

# filtro por empresa
df_alfpack = df_filter[df_filter['EMPRESA'] == "ALFPACK"]
df_mc = df_filter[df_filter['EMPRESA'] =='MC']
df_grafica = df_filter[df_filter['EMPRESA'] == 'ALFGRAF']

# medias faturamento por empresa
fat_alfpack = df_alfpack['FATURAMENTO'].sum()
faturamento_alfpack  = locale.currency(fat_alfpack, grouping=True)
qtd_alfpack = len(df_alfpack['PEDIDO'].unique())

fat_mc = df_mc['FATURAMENTO'].sum()
faturamento_mc = locale.currency(fat_mc,grouping = True)

fat_graf = df_grafica['FATURAMENTO'].sum()
faturamento_grafica = locale.currency(fat_graf,grouping=True)

qtd_pedidos = len(df_filter['PEDIDO'].unique())

fat_dia,pedidos_dia = st.columns(2)

with fat_dia:
    st.subheader(f'Faturamento em {hoje}')
    st.subheader(f'{faturamento_dia}')

with pedidos_dia:
    st.subheader("Pedidos")
    st.subheader(qtd_pedidos)


st.write("---")

alfpack,mc,grafica = st.columns(3)

with alfpack:
    st.subheader('ALFPACK')
    st.subheader(f'{faturamento_alfpack}')
    
with mc:
    st.subheader("MC")
    st.subheader(f'{faturamento_mc}')
with grafica:
    st.subheader("GRÁFICA")
    st.subheader(f'{faturamento_grafica}')

st.write("---")

# filtro dataframe por empresa








