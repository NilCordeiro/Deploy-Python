"""
Indexação vetorial da versão de demonstração (Streamlit Cloud).

Diferenças importantes em relação à versão paga/local
(modules/vector_store.py do projeto principal):

1. ISOLAMENTO POR SESSÃO — usa um ChromaDB em memória (EphemeralClient)
   guardado em st.session_state, não em disco. Isso é essencial numa demo
   pública: o Streamlit Cloud roda um único processo atendendo vários
   visitantes ao mesmo tempo, então se o índice fosse global (não por
   sessão), o documento de um visitante poderia aparecer para outro.

2. UM ARQUIVO POR VEZ — a demo trabalha com o PDF atualmente enviado via
   upload, substituindo o anterior. A versão paga/local é que sincroniza
   uma pasta inteira com múltiplos arquivos.

3. NADA FICA GRAVADO EM DISCO — quando a sessão do navegador termina, o
   índice em memória desaparece junto. Isso é intencional (não queremos
   reter documentos de visitantes da demo).
"""

import chromadb
import streamlit as st

from .pdf_processor import processar_pdf


def _obter_colecao():
    if "chroma_client_demo" not in st.session_state:
        st.session_state.chroma_client_demo = chromadb.EphemeralClient()
    if "chroma_collection_demo" not in st.session_state:
        st.session_state.chroma_collection_demo = (
            st.session_state.chroma_client_demo.get_or_create_collection("demo")
        )
    return st.session_state.chroma_collection_demo


def indexar_arquivo(caminho_pdf, nome_arquivo):
    """
    Indexa o PDF enviado, substituindo o que estava indexado antes nesta
    mesma sessão (a demo trabalha com um documento por vez).
    Retorna a quantidade de trechos indexados.
    """
    colecao = _obter_colecao()

    ids_existentes = colecao.get()["ids"]
    if ids_existentes:
        colecao.delete(ids=ids_existentes)

    chunks = processar_pdf(caminho_pdf, nome_arquivo)
    if chunks:
        colecao.add(
            ids=[f"{nome_arquivo}::{i}" for i in range(len(chunks))],
            documents=[c["texto"] for c in chunks],
            metadatas=[{"fonte": c["fonte"], "pagina": c["pagina"]} for c in chunks],
        )

    st.session_state.arquivo_demo_atual = nome_arquivo
    return len(chunks)


def buscar_trechos_relevantes(pergunta, k=5):
    colecao = _obter_colecao()
    if colecao.count() == 0:
        return []

    resultado = colecao.query(query_texts=[pergunta], n_results=min(k, colecao.count()))

    trechos = []
    documentos = resultado.get("documents", [[]])[0]
    metadados = resultado.get("metadatas", [[]])[0]
    for texto, meta in zip(documentos, metadados):
        trechos.append({"texto": texto, "fonte": meta.get("fonte"), "pagina": meta.get("pagina")})
    return trechos


def arquivo_atual():
    return st.session_state.get("arquivo_demo_atual")
