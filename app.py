"""
Assistente de Consulta a Contratos — VERSÃO DE DEMONSTRAÇÃO (trial pública).

Feita para rodar no Streamlit Community Cloud, a partir de um repositório
GitHub. Diferente da versão paga (instalada localmente no cliente):

- Aceita 1 PDF por vez, enviado via upload na barra lateral.
- Limite de tamanho/páginas do PDF, para controlar custo/abuso.
- Limite de perguntas por sessão, pelo mesmo motivo (a chave da Groq usada
  aqui é compartilhada entre TODOS os visitantes da demo).
- Mostra avisos de que é uma versão de teste, com as vantagens da versão
  completa, e um botão vermelho de compra no topo da página.

⚠️ Antes de publicar: troque LINK_CHECKOUT pelo link real do seu checkout.
"""

import os
import tempfile

import streamlit as st

from modules.llm import gerar_resposta
from modules.pdf_processor import contar_paginas
from modules.vector_store_demo import (
    arquivo_atual,
    buscar_trechos_relevantes,
    indexar_arquivo,
)

# ⚠️ TROQUE pelo link real do seu checkout (Stripe, Hotmart, Kiwify, etc.)
LINK_CHECKOUT = "https://pay.kiwify.com.br/7jRLEjs"

LIMITE_PERGUNTAS_SESSAO = 8
LIMITE_PAGINAS_PDF = 20
LIMITE_TAMANHO_MB = 8

st.set_page_config(
    page_title="Assistente de Contratos — Versão Teste", page_icon="📄", layout="centered"
)

# ----------------------------------------------------------------------
# Estilo — mesmo visual da versão principal, mais o botão de compra
# ----------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    [data-testid="stAppViewContainer"] h1 {
        font-size: 1.65rem !important;
        font-weight: 700 !important;
        color: #1F2937;
        margin-bottom: 0.2rem;
    }

    [data-testid="stChatMessage"] { border-radius: 14px; padding: 4px 6px; }

    [data-testid="stChatInput"] { border-radius: 14px; }
    [data-testid="stChatInput"] textarea { border-radius: 14px !important; }

    .botao-compra {
        display: block;
        text-align: center;
        background: #10B981;
        color: #ffffff !important;
        font-weight: 700;
        font-size: 15px;
        padding: 13px 20px;
        border-radius: 10px;
        text-decoration: none !important;
        box-shadow: 0 3px 10px rgba(220, 38, 38, 0.35);
        margin-bottom: 1.3rem;
        transition: transform 0.1s ease;
    }
    .botao-compra:hover { transform: scale(1.015); }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------
# Botão vermelho de compra — topo da página
# ----------------------------------------------------------------------
st.markdown(
    f'<a class="botao-compra" href="{LINK_CHECKOUT}" target="_blank">'
    f"🚀 Liberar Acesso Ilimitad</a>",
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------
# Título e aviso de versão teste + vantagens da versão paga
# ----------------------------------------------------------------------
st.title("📄 Assistente de Consulta a Contratos")
st.caption("Pergunte sobre um documento e receba respostas com a fonte citada.")

st.warning(
    "🧪 **Esta é uma versão teste.** Aqui você testa com **1 documento por vez** "
    f"e um limite de {LIMITE_PERGUNTAS_SESSAO} perguntas por sessão.\n\n"
    "**Na versão completa você tem:**\n"
    "- 📁 Pasta com **vários contratos** — indexação automática, sem limite de arquivos\n"
    "- 💻 **Instalação local** — seus documentos nunca saem da sua empresa\n"
    "- 🔄 **Atualização automática** — é só colocar um PDF novo na pasta, sem reenviar nada\n"
    "- ♾️ **Sem limite de perguntas**\n"
    "- 🛠️ Suporte e atualizações contínuas"
)

# ----------------------------------------------------------------------
# Barra lateral — upload do PDF de teste
# ----------------------------------------------------------------------
with st.sidebar:
    st.header("📁 Documento de teste")
    arquivo_pdf = st.file_uploader("Envie um PDF", type=["pdf"])
    st.caption(f"Limite da versão teste: {LIMITE_PAGINAS_PDF} páginas / {LIMITE_TAMANHO_MB}MB")

    st.divider()
    st.markdown(f"[🔓 Comprar versão completa]({LINK_CHECKOUT})")

    if st.session_state.get("historico"):
        st.divider()
        if st.button("🗑️ Recomeçar (novo documento)"):
            for chave in ["historico", "contador_perguntas", "arquivo_demo_atual",
                          "chroma_client_demo", "chroma_collection_demo"]:
                st.session_state.pop(chave, None)
            st.rerun()

if arquivo_pdf is None:
    st.info("⬅️ Envie um PDF na barra lateral para começar a testar.")
    st.stop()

# ----------------------------------------------------------------------
# Validações da versão teste (tamanho e páginas)
# ----------------------------------------------------------------------
tamanho_mb = arquivo_pdf.size / (1024 * 1024)
if tamanho_mb > LIMITE_TAMANHO_MB:
    st.error(
        f"Este arquivo tem {tamanho_mb:.1f}MB — acima do limite de {LIMITE_TAMANHO_MB}MB da "
        f"versão teste. A versão completa não tem esse limite."
    )
    st.stop()

# ----------------------------------------------------------------------
# Indexação (só reprocessa se for um arquivo diferente do já indexado)
# ----------------------------------------------------------------------
if arquivo_atual() != arquivo_pdf.name:
    caminho_temp = os.path.join(tempfile.gettempdir(), arquivo_pdf.name)
    with open(caminho_temp, "wb") as f:
        f.write(arquivo_pdf.getbuffer())

    total_paginas = contar_paginas(caminho_temp)
    if total_paginas > LIMITE_PAGINAS_PDF:
        st.error(
            f"Este documento tem {total_paginas} páginas — acima do limite de "
            f"{LIMITE_PAGINAS_PDF} páginas da versão teste. A versão completa não tem esse limite."
        )
        st.stop()

    with st.spinner("Lendo e indexando o documento..."):
        indexar_arquivo(caminho_temp, arquivo_pdf.name)

    st.session_state.contador_perguntas = 0
    st.success(f"'{arquivo_pdf.name}' indexado com sucesso.")

st.caption(f"📚 Documento atual: **{arquivo_atual()}**")

# ----------------------------------------------------------------------
# Chat
# ----------------------------------------------------------------------
if "historico" not in st.session_state:
    st.session_state.historico = []
if "contador_perguntas" not in st.session_state:
    st.session_state.contador_perguntas = 0

for mensagem in st.session_state.historico:
    with st.chat_message(mensagem["papel"]):
        st.markdown(mensagem["conteudo"])

if st.session_state.contador_perguntas >= LIMITE_PERGUNTAS_SESSAO:
    st.warning(
        f"Você atingiu o limite de {LIMITE_PERGUNTAS_SESSAO} perguntas da versão teste. "
        f"[Compre a versão completa]({LINK_CHECKOUT}) para uso sem limites, "
        "instalação local e pasta com vários documentos."
    )
else:
    pergunta = st.chat_input("Digite sua pergunta sobre o documento...")

    if pergunta:
        st.session_state.historico.append({"papel": "user", "conteudo": pergunta})
        with st.chat_message("user"):
            st.markdown(pergunta)

        with st.chat_message("assistant"):
            with st.spinner("Consultando o documento..."):
                trechos = buscar_trechos_relevantes(pergunta, k=5)
                resposta = gerar_resposta(pergunta, trechos)
            st.markdown(resposta)

        st.session_state.historico.append({"papel": "assistant", "conteudo": resposta})
        st.session_state.contador_perguntas += 1

        restantes = LIMITE_PERGUNTAS_SESSAO - st.session_state.contador_perguntas
        if 0 < restantes <= 3:
            st.caption(f"ℹ️ Você ainda tem {restantes} pergunta(s) nesta sessão de teste.")
