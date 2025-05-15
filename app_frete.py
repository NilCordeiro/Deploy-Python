
import pandas as pd
import streamlit as st
from datetime import datetime,timedelta
from datetime import date
import plotly.express as px

st.set_page_config(page_title= "Logística Ymbale",layout="wide")
                                  
st.title("🚚 Coleta Ymbale",)
hoje = date.today()
nova_data = hoje - timedelta(days=1)
#data_pes = nova_data.strftime('%d/%m/%y')
data_formatada = nova_data.strftime('%d/%m/%y')

data_ajuste = date.today()

st.write("Data coleta",data_formatada)


# importando as tabelas transportadoras

df_carga_rapida = pd.read_excel("TABELA PRAZO CARGA RAPIDA.xlsx")
df_vb = pd.read_excel("TABELA PRAZOS VB.xlsx")
df_rio_grande = pd.read_excel("TABEL PRAZO RIO GRANDE.xlsx")
df_filmes = pd.read_excel("T_FILMES.xlsx")
df_filmes_copia = df_filmes.copy()
df_filmes["R$ VALOR ESTOQUE"] = df_filmes["R$ VALOR ESTOQUE"].apply(lambda x: f'R$ {x:,.2f}'.replace(",", "X").replace(".", ",").replace("X", "."))

# Calculo dataframe

total_fat = df_filmes_copia['R$ VALOR ESTOQUE'].sum()

st.write("**Tabela de prazos por transportadoras**")

# escolha tabela transportadora
col1,col2,col3 = st.columns(3)

with col1:
    if st.checkbox("Tabela prazo Carga Rapida:"):
        st.write("Contato: Laerte (85) 9773-1852")
        st.dataframe(df_carga_rapida)

with col2:
    if st.checkbox("Tabela prazo VB Express:"):
        st.write("Contato: Glória (85) 9136-1516")
        st.dataframe(df_vb)

with col3:
    if st.checkbox("Tabela prazo Rio Grande:"):
        st.write("Contato: Luísa Mara (85) 9108-4249")
        st.dataframe(df_rio_grande)


if st.checkbox("Filmes Personalizados:"):
    st.markdown("**Lista filmes personalizados:**")
    st.markdown(f"segue estoque filmes personalizados pela empresa MC total R$ {total_fat:,.2f}")
    st.dataframe(df_filmes)

st.markdown("""---""")

# importando tabela CTE´s
data = pd.read_excel("custo_frete.xlsx")
data =  data.drop(['NATUREZA DA OPERAÇÃO','CIDADE TRANSPORTADORA','ESTADO TRANSPORTADORA','EMPRESA','CNPJ DESTINO','DATA DO ARQUIVO','IND','% PORCENTAGEM'],axis =1)
data = data.drop(['VALOR A RECEBER','TRANSPORTADORA','PERIODO','DATA REAL','MÊS'],axis = 1)
data['DATA'] = data['DATA'].dt.strftime('%d/%m/%y')
#data['DATA'] = pd.to_datetime(data['DATA'])
data['NOTA FISCAL'] = data['NOTA FISCAL'].astype(str)
data['N_CTE'] = data['N_CTE'].astype(str)

#---------------------------------------------------------------------------------------------------------------------------------------------------------------------
# sidebar 

st.sidebar.image('ymbale.png',width= 200,clamp=200,caption="Ymbale Embalagens")
st.sidebar.markdown("Empresa de embalagens em Maracanaú, Ceará")
st.sidebar.markdown("**Obs:** Toda e qualquer dúvida gerada devem ser tratadas com o setor logístico.")
st.sidebar.markdown("""
                    
    - Assitente Frete: Jander
    - Analista Logística: Nil
    - Coodernador: Marcelo

""")

st.sidebar.write("**FILTRE AQUI!**")
df_regiao = data['REGIÃO'].unique()
pesquisa = st.sidebar.selectbox("ESCOLHA A REGIÃO: ",df_regiao,placeholder="Região")

# filtro_1

df_filter = data[(data['REGIÃO'] == pesquisa) & (data['DATA'] == data_formatada)]
count_pedidos = df_filter["RAZÃO SOCIAL DESTINO"].count()

df_d = data[(data['DEV_FRETE'] == "FRETE") & (data['DATA'] == data_formatada)]
df_d = df_d.rename(columns={'RAZÃO SOCIAL DESTINO': 'PEDIDOS'})
grafico = df_d.groupby(['REGIÃO'])[['PEDIDOS']].count().reset_index().sort_values('PEDIDOS',ascending = True)

fig =px.bar(
    grafico,
    x = 'PEDIDOS',
    y = 'REGIÃO',
    title = (f'Gráfico coleta {data_formatada}'),
    width = 1150,
    height = 500,
    hover_data=['REGIÃO', 'PEDIDOS'], 
    color='PEDIDOS',
    text_auto = True )

# copia e friltro 

#tratamento de erro
if df_filter.empty:
    st.warning("Nenhum dado disponível com base nas configurações de filtro atuais!")
    st.stop() 


#plotando grafico

st.plotly_chart(fig)
st.markdown("O gráfico mostra a contagem por clientes região.")
st.markdown("""---""")
# plotando filtro

st.caption("Tabela coleta")
st.write(f"{count_pedidos} Pedidos coleta em {data_formatada}")
st.dataframe(df_filter)


if st.checkbox("Filtro Data"):
    
    data_filtro = st.text_input("**Filtre aqui**")
   
    df_filter2 = data[(data['REGIÃO'] == pesquisa) & (data['DATA'] == data_filtro)]
    qtd_pedidos = df_filter2['RAZÃO SOCIAL DESTINO'].count()
    st.write(f"{qtd_pedidos} Pedidos")
    st.dataframe(df_filter2)


