
import  streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from PIL import Image
import base64
from io import BytesIO


st.set_page_config(
    page_title="Regressão Linear",
    layout= "centered",
    page_icon="📈"
)

st.subheader("📈 Regressão Linear")

st.markdown("A regressão linear, que é uma técnica clássica de aprendizado supervisionado, pode ser aplicada em diversas áreas onde há uma relação linear entre variáveis. Aqui estão alguns exemplos de onde você pode aplicar **regressão linear:**")

st.markdown("#### 1. Previsão de vendas")
st.markdown(" - **Exemplo:** Uma empresa pode usar regressão linear para prever as vendas de um produto com base em variáveis como o preço, o número de promoções, o tempo de publicidade, entre outras.")

st.markdown("#### 2. Análise de risco em finanças")
st.markdown(" - **Exemplo:** Instituições financeiras podem usar a regressão linear para prever o valor de ativos (como ações ou imóveis) com base em variáveis como a taxa de juros, inflação, ou o desempenho econômico.")

st.markdown("#### 3. Previsão de preços de imóveis")
st.markdown(" - **Exemplo:** Prever o preço de venda de um imóvel com base em características como a localização, área do imóvel, número de quartos, e outras variáveis associadas.")

st.markdown("#### 4. Análise de marketing")
st.markdown(" - Exemplo: Uma empresa pode analisar como diferentes canais de marketing (como anúncios online, TV, rádio) impactam as vendas ou o tráfego do site, e usar a regressão linear para prever os resultados com base em variáveis de marketing.")

st.markdown("#### 5. Ajuste de processos industriais")
st.markdown(" - **Exemplo:** Em uma fábrica, a regressão linear pode ser usada para prever o rendimento ou a eficiência da produção com base em variáveis como a temperatura, a pressão, ou a quantidade de insumos.")

st.markdown("#### 6. Previsão de custos operacionais")
st.markdown(" - **Exemplo:** Empresas podem usar regressão linear para prever os custos operacionais (como custos de transporte, logística, energia) com base em variáveis como volume de produção, distâncias percorridas, entre outros fatores.")

st.markdown("#### 7. Análise de desempenho acadêmico")
st.markdown(" - **Exemplo:** Prever a nota final de um aluno com base em variáveis como o número de horas de estudo, participação em atividades extracurriculares, e histórico acadêmico.")

st.markdown("#### 8. Previsão de demanda")
st.markdown(" - **Exemplo:** Empresas de varejo podem prever a demanda de determinados produtos em diferentes períodos do ano com base em variáveis como clima, datas festivas, e padrões de consumo passados.")

st.markdown("#### 9. Saúde e medicina")
st.markdown(" - **Exemplo:** Prever a pressão arterial, níveis de colesterol ou glicose com base em variáveis como idade, peso, altura, histórico familiar, hábitos alimentares, entre outros fatores.")

st.markdown("#### 10. Análise de clima")
st.markdown(" - **Exemplo:** Modelar a temperatura média de uma região com base em variáveis como a umidade, velocidade do vento, e hora do dia.")

st.markdown("**Considerações importantes:**")
st.markdown(""" - A regressão linear é mais eficaz quando as relações entre as variáveis são aproximadamente lineares. 
                  Para dados que apresentam relações não lineares, técnicas mais avançadas como a regressão polinomial ou redes neurais podem ser mais apropriadas.
""")

st.markdown("""Esses são apenas alguns exemplos de como a regressão linear pode ser aplicada, e ela pode ser útil em muitos outros contextos dependendo dos dados disponíveis e das variáveis envolvidas!
""")

st.markdown("##### Criando um modelo **regressão linear simples**")
st.markdown("""Nessa base de dados temos alguns dados de um plano de saúde ficticio onde vamos colocar o modelo para prever o custo pela idade do paciente""")

data = pd.read_csv("plano_saude.csv")
st.dataframe(data)

x_plano_saude = data.iloc[:,0].values
y_plano_saude = data.iloc[:,1].values

x_plano_saude = x_plano_saude.reshape(-1,1)

from sklearn.linear_model import LinearRegression
regressor_plano_saude = LinearRegression()
regressor_plano_saude.fit(x_plano_saude,y_plano_saude)

previsoes = regressor_plano_saude.predict(x_plano_saude)

grafico = px.scatter(x = x_plano_saude.ravel(),y = y_plano_saude,title="Grafico")
grafico.add_scatter(x = x_plano_saude.ravel(),y = previsoes,name = "Regressão")

st.plotly_chart(grafico)

st.markdown("""
    - X Idade do Cliente
    - Y Custo Plano
    - Linha Previsão do Modelo
""")

st.markdown("""Obs: Os pontos no gráfico representa os dados da tabela plano de saude, a reta são as previsões do modelo de regressão linear simples.""")

# Previsão de valores inseridos pelo usuário
st.markdown("#### Previsão")
st.write("Em seguida insira um valor para que o modelo realize uma previsão")
valor_usuario = st.number_input("Digite a idade para prever os custos",min_value = 0.0)

if valor_usuario:
    previsao_usuario = regressor_plano_saude.predict(np.array([[valor_usuario]]))
    st.write(f"A previsão para a idade de {valor_usuario} anos é de R$ {round(previsao_usuario[0],2)}")

# Caminho da imagem local
caminho_imagem = "imagem.JPG"

# Abrir imagem com PIL
imagem = Image.open(caminho_imagem)

# Converter imagem para base64
def get_image_base64(img):
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_bytes = buffered.getvalue()
    return base64.b64encode(img_bytes).decode()

img_base64 = get_image_base64(imagem)

# CSS para imagem arredondada
st.markdown("""
    <style>
    .img-redonda {
        border-radius: 50%;
        width: 200px;
        height: 200px;
        object-fit: cover;
    }
    </style>
""", unsafe_allow_html=True)

# Exibir imagem com HTML
st.sidebar.markdown(f'<img src="data:image/png;base64,{img_base64}" class="img-redonda">', unsafe_allow_html=True)
#st.sidebar.image('imagem.jpg',caption= 'Nil Cordeiro - Machine Learning and Data Science student',width= 160,channels="RGB")
st.sidebar.markdown("**Nil Cordeiro Analista de Dados**")
st.sidebar.markdown("""
                
                    Principais tecnologias:
                    - Python
                    - Machine Learning
                    - Power Bi
                    - SQL
                    - Excel/VBA                  
""")



