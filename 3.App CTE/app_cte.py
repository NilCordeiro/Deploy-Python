
import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import os
import io

st.title("Leitor de CT-e XML")
st.write("Selecione os arquivos XML de CT-e para extrair os dados.")

# Upload de múltiplos arquivos XML
arquivos = st.file_uploader("Selecione os arquivos XML", type="xml", accept_multiple_files=True)

# Namespace do XML CTe
ns = {'cte': 'http://www.portalfiscal.inf.br/cte'}

# Função auxiliar para extrair texto de um elemento XML com namespace
def get_text(element, tag):
    child = element.find(tag, ns)
    return child.text if child is not None else None

# Processamento dos arquivos
dados_cte = []

if arquivos:
    for arquivo in arquivos:
        try:
            tree = ET.parse(arquivo)
            root = tree.getroot()

            infCte = root.find('.//cte:infCte', ns)
            if infCte is None:
                st.warning(f"`infCte` não encontrado no arquivo: {arquivo.name}")
                continue

            ide = infCte.find('cte:ide', ns)
            emit = infCte.find('cte:emit', ns)
            rem = infCte.find('cte:rem', ns)
            dest = infCte.find('cte:dest', ns)
            vPrest = infCte.find('cte:vPrest', ns)

            infCTeNorm = infCte.find('cte:infCTeNorm', ns)
            infCarga = infCTeNorm.find('cte:infCarga', ns) if infCTeNorm is not None else None
            vCarga = get_text(infCarga, 'cte:vCarga') if infCarga is not None else None

            dados_cte.append({
                'chave': infCte.attrib.get('Id', '')[-44:],
                'cte': get_text(ide, 'cte:nCT') if ide is not None else None,
                'data_emissao': get_text(ide, 'cte:dhEmi') if ide is not None else None,
                'remetente_nome': get_text(rem, 'cte:xNome') if rem is not None else None,
                'destinatario_nome': get_text(dest, 'cte:xNome') if dest is not None else None,
                'valor_carga': vCarga,
                'valor_cte': get_text(vPrest, 'cte:vTPrest') if vPrest is not None else None,
                'cnpj_emitente': get_text(emit, 'cte:CNPJ') if emit is not None else None,
                'emitente_nome': get_text(emit, 'cte:xNome') if emit is not None else None,
            })

        except Exception as e:
            st.error(f"Erro ao processar {arquivo.name}: {e}")

    # Exibir dados em tabela
    if dados_cte:
        df_cte = pd.DataFrame(dados_cte)
        st.success(f"{len(df_cte)} arquivos processados com sucesso.")
        st.dataframe(df_cte)

        # Criar um buffer de memória para o Excel
        output = io.BytesIO()
        df_cte.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)

        # Botão de download
        st.download_button(
            
            label="📥 Baixar como Excel",
            data=output,
            file_name="dados_cte.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )       
        
    else:
        st.info("Nenhum dado extraído.")
else:
    st.info("Aguardando upload de arquivos XML.")

