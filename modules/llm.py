"""
Módulo responsável por conversar com a API da Groq e gerar a resposta final,
sempre citando a origem (documento e página) das informações usadas.

Nesta versão de demonstração, a chave da API vem do Streamlit Secrets
(Settings > Secrets, no painel do Streamlit Cloud) — NUNCA do código ou de
um arquivo .env commitado no repositório, já que este projeto vai para um
repositório GitHub que pode ser lido por qualquer pessoa.
"""

import os

import streamlit as st
from groq import Groq

MODELO_GROQ = "openai/gpt-oss-120b"

AVISO_PADRAO = (
    "Esta resposta é apenas um apoio de consulta rápida e não substitui a "
    "leitura completa do documento original."
)

PROMPT_SISTEMA = f"""Você é um assistente de consulta a contratos e documentos — versão de demonstração.

A empresa pode atuar em qualquer segmento e os documentos podem ser contratos de qualquer tipo.
Não assuma nenhum segmento específico nem trate o usuário como se fosse necessariamente de uma área jurídica.

Regras obrigatórias:
1. Responda SOMENTE com base nos trechos de documento fornecidos abaixo. Nunca invente informação que não esteja neles.
2. Se a resposta não estiver claramente nos trechos fornecidos, diga explicitamente que não encontrou essa informação no documento enviado. Não tente adivinhar ou complementar com conhecimento geral.
3. Sempre que usar uma informação, cite o nome do arquivo de origem e, se disponível, a página, no formato: (Fonte: NOME_DO_ARQUIVO, página N).
4. Seja claro, objetivo e escreva em português.
5. Ao final de toda resposta, inclua o aviso: "{AVISO_PADRAO}"
"""


def _obter_chave_api():
    """Busca a chave primeiro no Streamlit Secrets (produção), depois em
    variável de ambiente (útil para rodar localmente sem configurar secrets.toml)."""
    try:
        if "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass
    return os.environ.get("GROQ_API_KEY")


def _montar_contexto(trechos):
    partes = []
    for i, trecho in enumerate(trechos, start=1):
        pagina = f", página {trecho['pagina']}" if trecho.get("pagina") else ""
        partes.append(f"[Trecho {i} - Fonte: {trecho['fonte']}{pagina}]\n{trecho['texto']}")
    return "\n\n".join(partes)


def gerar_resposta(pergunta, trechos_relevantes):
    chave_api = _obter_chave_api()
    if not chave_api:
        return (
            "⚠️ A chave da API não foi configurada. Se você é o administrador deste app, "
            "configure GROQ_API_KEY em Settings > Secrets no painel do Streamlit Cloud."
        )

    cliente = Groq(api_key=chave_api)

    if not trechos_relevantes:
        contexto = "(Nenhum trecho relevante foi encontrado no documento enviado.)"
    else:
        contexto = _montar_contexto(trechos_relevantes)

    mensagem_usuario = f"""Pergunta do usuário: {pergunta}

Trechos do documento recuperados:
{contexto}
"""

    resposta = cliente.chat.completions.create(
        model=MODELO_GROQ,
        messages=[
            {"role": "system", "content": PROMPT_SISTEMA},
            {"role": "user", "content": mensagem_usuario},
        ],
        temperature=0.2,
        max_tokens=1000,
    )

    return resposta.choices[0].message.content
