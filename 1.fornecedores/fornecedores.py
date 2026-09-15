# ============================================================
# ANÁLISE DE DADOS — BASE DE FORNECEDORES (T_Rela_Forn)
# Python + Streamlit + Pandas + Plotly
# ============================================================
#
# RESUMO DA ANÁLISE EXPLORATÓRIA (EDA) QUE ORIENTOU ESTE APP
# ------------------------------------------------------------
# Antes de desenhar qualquer gráfico, explorei a planilha inteira
# (681.846 linhas, 1 linha por item de nota fiscal) para entender o
# que os dados realmente permitem responder. Principais achados e
# decisões de engenharia que vieram deles:
#
# 1) Volume e granularidade: 304 fornecedores, 424 grupos (cada
#    grupo é "Fornecedor - subcategoria de produto"), 109
#    vendedores, ~53 mil combinações de produto (código +
#    descrição) e 85.118 notas fiscais distintas. Não há nenhum
#    valor nulo em nenhuma coluna.
#
# 2) Período disponível: só existem os meses JAN, FEV, MAR, ABR e
#    JUL — maio e junho não aparecem na base. O app mostra isso
#    explicitamente (aviso na Visão Geral) para ninguém interpretar
#    a evolução Abr → Jul como "mês a mês" sem esse intervalo.
#
# 3) "Devolução" vem ZERADA em 100% das 681 mil linhas desta
#    extração. Por isso não criei nenhum indicador de devolução —
#    ele mostraria sempre 0% e passaria uma informação falsa de
#    "sem devoluções". Isso fica documentado na aba de Qualidade
#    dos Dados.
#
# 4) "Filial" tem um único valor (MATRIZ - L1) na base inteira —
#    não é uma dimensão útil para filtro/gráfico aqui.
#
# 5) As colunas prontas "% QTD Vendas" e "% Vendas" somam ~1,275 no
#    total (não 1,0), ou seja, foram calculadas contra uma base de
#    referência diferente desta extração. Por isso o app NUNCA usa
#    essas colunas — todo percentual exibido é recalculado a partir
#    dos dados realmente carregados, com o filtro que está ativo.
#
# 6) Não existe coluna de cliente/comprador na base — dá para
#    analisar por fornecedor, grupo, vendedor e produto, mas não por
#    cliente final.
#
# 7) Controle de acesso: a aba "T_login" segue o mesmo modelo do
#    dashboard comercial já existente — cada representante só
#    enxerga o(s) fornecedor(es)/marca(s) liberados para ela.
# ============================================================

import os
import re
import time
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# CONFIGURAÇÃO PRINCIPAL
# ============================================================
CAMINHO_PLANILHA = "1.fornecedores\BD_Fornecedores.xlsx"
PASTA_CACHE = ".cache_analise_fornecedores"

TITULO_APP = "Análise de Fornecedores"
SUBTITULO_APP = "Painel analítico — vendas, produtos e vendedores"
LOGO_PATH = None

# Paleta (fundo 100% preto, no mesmo padrão já adotado no dashboard comercial)
COR_FUNDO = "#000000"
COR_CARD = "#121212"
COR_CARD_BORDA = "#2A2A2A"
COR_TEXTO = "#FFFFFF"
COR_TEXTO_SECUNDARIO = "#A3A3A3"
COR_DESTAQUE = "#38BDF8"
COR_POSITIVO = "#34D399"
COR_NEGATIVO = "#F87171"
COR_AMARELO = "#FBBF24"

MESES_ORDEM = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}
MESES_NOME = {
    "jan": "Janeiro", "fev": "Fevereiro", "mar": "Março", "abr": "Abril",
    "mai": "Maio", "jun": "Junho", "jul": "Julho", "ago": "Agosto",
    "set": "Setembro", "out": "Outubro", "nov": "Novembro", "dez": "Dezembro",
}
MESES_ABREV = {
    "jan": "Jan", "fev": "Fev", "mar": "Mar", "abr": "Abr",
    "mai": "Mai", "jun": "Jun", "jul": "Jul", "ago": "Ago",
    "set": "Set", "out": "Out", "nov": "Nov", "dez": "Dez",
}


class ErroPlanilha(Exception):
    pass


# ============================================================
# FORMATAÇÃO (padrão numérico brasileiro)
# ============================================================
def formatar_moeda_br(valor) -> str:
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        valor = 0.0
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def formatar_numero_br(valor) -> str:
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        valor = 0.0
    texto = f"{valor:,.0f}"
    texto = texto.replace(",", ".")
    return texto


def formatar_percentual_br(valor, com_sinal: bool = False) -> str:
    if valor is None or pd.isna(valor):
        return "N/A"
    texto = f"{valor:,.1f}"
    texto = texto.replace(".", ",")
    sinal = "+" if (com_sinal and valor > 0) else ""
    return f"{sinal}{texto}%"


# ============================================================
# NORMALIZAÇÃO DE TEXTO / COLUNAS
# ============================================================
def _normalizar_espacos(texto) -> str:
    return re.sub(r"\s+", " ", str(texto).strip())


def _chave_comparacao(texto) -> str:
    texto = _normalizar_espacos(texto).upper()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return texto


def _normalizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [_normalizar_espacos(c) for c in df.columns]
    return df


def _validar_colunas(df: pd.DataFrame, colunas_esperadas: list, nome_aba: str):
    faltantes = [c for c in colunas_esperadas if c not in df.columns]
    if faltantes:
        raise ErroPlanilha(
            f"A aba **{nome_aba}** está sem a(s) coluna(s): {', '.join(faltantes)}. "
            f"Colunas encontradas: {', '.join(df.columns)}."
        )


def _assinatura_arquivo(caminho: str) -> str:
    stat = os.stat(caminho)
    return f"{stat.st_size}_{int(stat.st_mtime)}"


# ============================================================
# CARREGAMENTO — T_login
# ============================================================
@st.cache_data(show_spinner=False)
def carregar_login(caminho_planilha: str, assinatura: str) -> pd.DataFrame:
    df = pd.read_excel(caminho_planilha, sheet_name="T_login", engine="openpyxl")
    df = _normalizar_colunas(df)
    _validar_colunas(df, ["Nome", "Marca", "Senha"], "T_login")

    df = df.dropna(subset=["Nome", "Marca", "Senha"]).copy()
    df["Nome"] = df["Nome"].astype(str).map(_normalizar_espacos)
    df["Marca"] = df["Marca"].astype(str).map(_normalizar_espacos)
    df["Senha"] = df["Senha"].apply(
        lambda v: str(int(v)) if isinstance(v, float) and v.is_integer() else str(v).strip()
    )
    return df.reset_index(drop=True)


# ============================================================
# CARREGAMENTO — T_Rela_Forn (tabela granular: 1 linha por item de NF)
# ============================================================
def _ler_base_do_excel(caminho_planilha: str) -> pd.DataFrame:
    df = pd.read_excel(caminho_planilha, sheet_name="T_Rela_Forn", engine="openpyxl")
    df = _normalizar_colunas(df)
    _validar_colunas(
        df,
        ["Fornecedor", "Grupo", "Mês", "Cod. Vendedor", "Vendedor", "CODIGO",
         "DESCRICAO_PRODUTO", "Qtde 2026", "Vendas 2026", "Devolução"],
        "T_Rela_Forn",
    )
    tem_nf = "N° NF" in df.columns

    renomeio = {
        "Fornecedor": "fornecedor",
        "Grupo": "grupo",
        "Mês": "mes",
        "Cod. Vendedor": "cod_vendedor",
        "Vendedor": "vendedor",
        "CODIGO": "codigo_produto",
        "DESCRICAO_PRODUTO": "descricao_produto",
        "Qtde 2026": "qtd",
        "Vendas 2026": "vendas",
        "Devolução": "devolucao",
    }
    if tem_nf:
        renomeio["N° NF"] = "nota_fiscal"
    df = df.rename(columns=renomeio)

    colunas_uteis = [
        "fornecedor", "grupo", "mes", "cod_vendedor", "vendedor",
        "codigo_produto", "descricao_produto", "qtd", "vendas", "devolucao",
    ]
    if tem_nf:
        colunas_uteis.append("nota_fiscal")
    df = df[colunas_uteis].copy()

    df["fornecedor"] = df["fornecedor"].astype(str).map(_normalizar_espacos).astype("category")
    df["grupo"] = df["grupo"].astype(str).map(_normalizar_espacos).astype("category")
    df["mes"] = df["mes"].astype(str).str.strip().str.lower().astype("category")
    df["vendedor"] = df["vendedor"].fillna("").astype(str).map(_normalizar_espacos).astype("category")
    df["cod_vendedor"] = df["cod_vendedor"].apply(
        lambda v: str(int(v)) if isinstance(v, float) and v.is_integer() else str(v).strip()
    )
    df["codigo_produto"] = df["codigo_produto"].apply(
        lambda v: str(int(v)) if isinstance(v, float) and v.is_integer() else str(v).strip()
    )
    df["descricao_produto"] = df["descricao_produto"].fillna("").astype(str).map(_normalizar_espacos)
    if tem_nf:
        df["nota_fiscal"] = df["nota_fiscal"].apply(
            lambda v: str(int(v)) if isinstance(v, float) and v.is_integer() else str(v).strip()
        )

    for col in ["qtd", "vendas", "devolucao"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df["_chave_fornecedor"] = df["fornecedor"].astype(str).map(_chave_comparacao)
    return df.reset_index(drop=True)


@st.cache_data(show_spinner=False)
def carregar_base(caminho_planilha: str, assinatura: str) -> pd.DataFrame:
    """
    A aba T_Rela_Forn tem ~680 mil linhas. Ler isso via Excel a cada
    execução deixaria o app lento (o teste levou ~65s) — então, na
    primeira execução, convertemos para Parquet local (bem mais rápido
    de reler) e nas próximas vezes lemos direto do Parquet. Se a
    planilha original mudar, a assinatura muda e o cache é refeito.
    """
    Path(PASTA_CACHE).mkdir(parents=True, exist_ok=True)
    caminho_parquet = os.path.join(PASTA_CACHE, f"base_{assinatura}.parquet")

    if os.path.exists(caminho_parquet):
        try:
            return pd.read_parquet(caminho_parquet)
        except Exception:
            pass

    df = _ler_base_do_excel(caminho_planilha)

    try:
        df.to_parquet(caminho_parquet, index=False)
        for arquivo in os.listdir(PASTA_CACHE):
            caminho_antigo = os.path.join(PASTA_CACHE, arquivo)
            if arquivo.startswith("base_") and caminho_antigo != caminho_parquet:
                try:
                    os.remove(caminho_antigo)
                except OSError:
                    pass
    except Exception:
        pass

    return df


def carregar_dados(caminho_planilha: str):
    if not os.path.exists(caminho_planilha):
        raise ErroPlanilha(
            f"Não encontrei a planilha em **{caminho_planilha}**. "
            f"Confira a variável CAMINHO_PLANILHA no topo do arquivo."
        )
    assinatura = _assinatura_arquivo(caminho_planilha)
    login = carregar_login(caminho_planilha, assinatura)
    base = carregar_base(caminho_planilha, assinatura)
    return login, base


# ============================================================
# REGRAS DE ACESSO
# ============================================================
def obter_fornecedores_autorizados(marca_bruta: str) -> list:
    partes = re.split(r"[;,/]", marca_bruta)
    return [p.strip() for p in partes if p.strip()]


def validar_login(login_df: pd.DataFrame, nome: str, senha: str):
    nome_chave = _chave_comparacao(nome)
    senha = senha.strip()

    candidatos = login_df[login_df["Nome"].map(_chave_comparacao) == nome_chave]
    if candidatos.empty:
        return None

    linha = candidatos.iloc[0]
    if linha["Senha"] != senha:
        return None

    # Uma mesma pessoa pode aparecer em mais de uma linha do login (uma
    # marca por linha) — juntamos todas as marcas dela em uma lista só.
    marcas = []
    for m in candidatos["Marca"]:
        for marca in obter_fornecedores_autorizados(m):
            if marca not in marcas:
                marcas.append(marca)

    return {
        "nome": linha["Nome"],
        "marcas": marcas,
        "chaves_marcas": {_chave_comparacao(m) for m in marcas},
    }


def filtrar_por_acesso(df: pd.DataFrame, chaves_marcas: set) -> pd.DataFrame:
    return df[df["_chave_fornecedor"].isin(chaves_marcas)].copy()


# ============================================================
# CSS
# ============================================================
def aplicar_css():
    st.markdown(f"""
    <style>
        html, body {{ background-color: {COR_FUNDO}; }}
        .stApp {{ background-color: {COR_FUNDO}; }}
        [data-testid="stSidebar"] {{
            background-color: {COR_FUNDO};
            border-right: 1px solid {COR_CARD_BORDA};
        }}
        [data-testid="stSidebar"] * {{ color: {COR_TEXTO} !important; }}
        h1, h2, h3, h4, p, span, label, .stMarkdown {{ color: {COR_TEXTO}; }}

        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header, [data-testid="stHeader"], .stAppHeader {{
            visibility: visible;
            background-color: {COR_FUNDO} !important;
        }}
        [data-testid="stToolbar"] {{visibility: hidden;}}
        [data-testid="stDecoration"] {{
            visibility: hidden;
            background-color: {COR_FUNDO} !important;
        }}
        [data-testid="stStatusWidget"] {{visibility: hidden;}}
        [data-testid="collapsedControl"],
        [data-testid="collapsedControl"] *,
        [data-testid*="Sidebar"],
        [data-testid*="Sidebar"] * {{
            visibility: visible !important;
            opacity: 1 !important;
        }}

        .cabecalho-app h1 {{ margin-bottom: 0.1rem; }}
        .cabecalho-app p {{ color: {COR_TEXTO_SECUNDARIO}; margin-top: 0; }}

        .card-indicador {{
            background-color: {COR_CARD};
            border: 1px solid {COR_CARD_BORDA};
            border-radius: 12px;
            padding: 1rem 1.2rem;
        }}
        .card-indicador .rotulo {{
            color: {COR_TEXTO_SECUNDARIO};
            font-size: 0.85rem;
            margin-bottom: 0.3rem;
        }}
        .card-indicador .valor {{ font-size: 1.5rem; font-weight: 700; color: {COR_TEXTO}; }}
        .card-indicador .valor-destaque {{ color: {COR_DESTAQUE}; }}

        .badge-marca {{
            display: inline-block;
            background-color: {COR_CARD};
            border: 1px solid {COR_CARD_BORDA};
            color: {COR_TEXTO_SECUNDARIO};
            border-radius: 999px;
            padding: 0.2rem 0.7rem;
            margin-right: 0.4rem;
            font-size: 0.8rem;
        }}

        .stTextInput input, .stTextInput input:focus {{
            background-color: {COR_CARD};
            color: {COR_TEXTO};
            border: 1px solid {COR_CARD_BORDA};
        }}
        .stButton > button {{
            background-color: {COR_CARD};
            color: {COR_TEXTO};
            border: 1px solid {COR_CARD_BORDA};
        }}
        .stButton > button:hover {{ border-color: {COR_DESTAQUE}; color: {COR_DESTAQUE}; }}
        .stButton > button[kind="primary"] {{
            background-color: {COR_DESTAQUE};
            color: #0A1520;
            border: none;
        }}

        [data-testid="stTabs"] button {{ color: {COR_TEXTO_SECUNDARIO}; }}
        [data-testid="stTabs"] button[aria-selected="true"] {{ color: {COR_DESTAQUE}; }}
    </style>
    """, unsafe_allow_html=True)


# ============================================================
# TELA DE LOGIN
# ============================================================
def tela_login(login_df: pd.DataFrame):
    col_esq, col_meio, col_dir = st.columns([1, 1.1, 1])
    with col_meio:
        st.markdown("<div style='height: 8vh'></div>", unsafe_allow_html=True)
        if LOGO_PATH and os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=140)

        st.markdown(f"""
        <div class="cabecalho-app" style="text-align:center;">
            <h1>{TITULO_APP}</h1>
            <p>Acesse com seu usuário para ver a análise da sua marca</p>
        </div>
        """, unsafe_allow_html=True)

        with st.container():
            st.markdown('<div class="card-indicador">', unsafe_allow_html=True)
            with st.form("form_login"):
                nome = st.text_input("Nome da representante")
                senha = st.text_input("Senha", type="password")
                entrar = st.form_submit_button("Entrar", use_container_width=True, type="primary")
            st.markdown('</div>', unsafe_allow_html=True)

        if entrar:
            if not nome.strip() or not senha.strip():
                st.error("Preencha nome e senha.")
            else:
                usuario = validar_login(login_df, nome, senha)
                if usuario is None:
                    st.error("Usuário ou senha inválidos.")
                else:
                    st.session_state["autenticado"] = True
                    st.session_state["usuario"] = usuario
                    for chave in ["grupos_selecionados", "marca_selecionada", "mes_selecionado_grupo"]:
                        st.session_state.pop(chave, None)
                    st.rerun()


# ============================================================
# COMPONENTES
# ============================================================
def card_indicador(rotulo: str, valor_formatado: str, destaque: bool = False):
    classe_valor = "valor valor-destaque" if destaque else "valor"
    st.markdown(f"""
    <div class="card-indicador">
        <div class="rotulo">{rotulo}</div>
        <div class="{classe_valor}">{valor_formatado}</div>
    </div>
    """, unsafe_allow_html=True)


def _ordenar_meses(meses) -> list:
    return sorted(set(meses), key=lambda m: MESES_ORDEM.get(str(m), 99))


def grafico_vendas_mensais(df_filtrado: pd.DataFrame):
    agrupado = df_filtrado.groupby("mes", as_index=False, observed=True)["vendas"].sum()
    agrupado["mes"] = agrupado["mes"].astype(str)
    agrupado["ordem"] = agrupado["mes"].map(MESES_ORDEM)
    agrupado = agrupado.dropna(subset=["ordem"]).sort_values("ordem")
    agrupado["nome_mes"] = agrupado["mes"].map(MESES_ABREV)
    agrupado["nome_mes_completo"] = agrupado["mes"].map(MESES_NOME)
    agrupado["variacao"] = agrupado["vendas"].pct_change() * 100

    if agrupado.empty:
        st.info("Sem dados de vendas para o filtro selecionado.")
        return

    textos, cores = [], []
    for v, var in zip(agrupado["vendas"], agrupado["variacao"]):
        valor_fmt = formatar_moeda_br(v)
        if pd.isna(var):
            textos.append(valor_fmt)
            cores.append(COR_TEXTO_SECUNDARIO)
        else:
            seta = "▲" if var > 0 else ("▼" if var < 0 else "■")
            textos.append(f"{seta} {formatar_percentual_br(var, com_sinal=True)}<br>{valor_fmt}")
            cores.append(COR_POSITIVO if var > 0 else (COR_NEGATIVO if var < 0 else COR_TEXTO_SECUNDARIO))

    hover = [
        f"{m}<br>Vendas: {formatar_moeda_br(v)}<br>Variação: {formatar_percentual_br(var, com_sinal=True)}"
        for m, v, var in zip(agrupado["nome_mes_completo"], agrupado["vendas"], agrupado["variacao"])
    ]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=agrupado["nome_mes"], y=agrupado["vendas"],
        mode="lines+markers+text",
        line=dict(color=COR_DESTAQUE, width=3),
        marker=dict(size=9, color=COR_DESTAQUE),
        text=textos, textposition="top center",
        textfont=dict(size=12, color=cores),
        hovertext=hover, hoverinfo="text", name="Vendas",
    ))
    fig.update_layout(
        plot_bgcolor=COR_CARD, paper_bgcolor=COR_CARD, font=dict(color=COR_TEXTO),
        margin=dict(l=10, r=10, t=60, b=10), height=420,
        xaxis=dict(showgrid=False, color=COR_TEXTO_SECUNDARIO, categoryorder="array",
                   categoryarray=agrupado["nome_mes"].tolist()),
        yaxis=dict(showgrid=True, gridcolor=COR_CARD_BORDA, color=COR_TEXTO_SECUNDARIO, tickprefix="R$ "),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    meses_existentes = set(agrupado["mes"])
    meses_faltando = [m for m in MESES_ORDEM if m not in meses_existentes
                      and MESES_ORDEM[m] > min(agrupado["ordem"]) and MESES_ORDEM[m] < max(agrupado["ordem"])]
    if meses_faltando:
        nomes_faltando = ", ".join(MESES_NOME[m] for m in sorted(meses_faltando, key=lambda m: MESES_ORDEM[m]))
        st.caption(
            f"⚠️ A base não tem dados de **{nomes_faltando}** — os meses acima estão "
            f"lado a lado no gráfico, mas não são necessariamente consecutivos."
        )


def grafico_projecao_vendas(df_filtrado: pd.DataFrame):
    """
    Projeção do próximo mês por regressão linear simples (mínimos
    quadrados) sobre a série mensal filtrada. Com poucos pontos
    históricos, uma reta de tendência é mais estável e explicável do
    que um modelo com mais parâmetros — que tenderia a overfitar uma
    série curta.
    """
    agrupado = df_filtrado.groupby("mes", as_index=False, observed=True)["vendas"].sum()
    agrupado["mes"] = agrupado["mes"].astype(str)
    agrupado["ordem"] = agrupado["mes"].map(MESES_ORDEM)
    agrupado = agrupado.dropna(subset=["ordem"]).sort_values("ordem").reset_index(drop=True)
    agrupado["nome_mes"] = agrupado["mes"].map(MESES_ABREV)

    if len(agrupado) < 2:
        st.info("É preciso pelo menos 2 meses de histórico (com o filtro atual) para projetar.")
        return

    x = agrupado["ordem"].to_numpy(dtype=float)
    y = agrupado["vendas"].to_numpy(dtype=float)
    a, b = np.polyfit(x, y, 1)

    proxima_ordem = x[-1] + 1
    projecao = max(a * proxima_ordem + b, 0.0)

    ordem_para_mes = {v: k for k, v in MESES_ORDEM.items()}
    ciclica = int(proxima_ordem) - 12 if proxima_ordem > 12 else int(proxima_ordem)
    proximo_mes = MESES_ABREV.get(ordem_para_mes.get(ciclica), "Próx.")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=agrupado["nome_mes"], y=agrupado["vendas"], mode="lines+markers",
        line=dict(color=COR_DESTAQUE, width=3), marker=dict(size=8, color=COR_DESTAQUE), name="Histórico",
    ))
    fig.add_trace(go.Scatter(
        x=[agrupado["nome_mes"].iloc[-1], proximo_mes],
        y=[agrupado["vendas"].iloc[-1], projecao],
        mode="lines", line=dict(color=COR_POSITIVO, width=2, dash="dash"),
        showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=[proximo_mes], y=[projecao], mode="markers+text",
        marker=dict(size=13, color=COR_POSITIVO, symbol="diamond"),
        text=[formatar_moeda_br(projecao)], textposition="top center",
        textfont=dict(size=12, color=COR_POSITIVO), name="Projeção",
        hovertext=f"Projeção para {proximo_mes}: {formatar_moeda_br(projecao)}", hoverinfo="text",
    ))
    fig.update_layout(
        plot_bgcolor=COR_CARD, paper_bgcolor=COR_CARD, font=dict(color=COR_TEXTO),
        margin=dict(l=10, r=10, t=40, b=10), height=380,
        xaxis=dict(showgrid=False, color=COR_TEXTO_SECUNDARIO),
        yaxis=dict(showgrid=True, gridcolor=COR_CARD_BORDA, color=COR_TEXTO_SECUNDARIO, tickprefix="R$ "),
        legend=dict(orientation="h", y=1.15, font=dict(color=COR_TEXTO_SECUNDARIO)),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Projeção por regressão linear sobre o histórico mensal filtrado — é uma "
        "tendência estatística simples, não uma garantia de resultado."
    )


def grafico_vendas_por_grupo(df_filtrado: pd.DataFrame):
    meses_disponiveis = _ordenar_meses(df_filtrado["mes"].dropna().astype(str).unique().tolist())
    opcoes_mes = ["Todos os meses"] + meses_disponiveis

    if st.session_state.get("mes_selecionado_grupo") not in opcoes_mes:
        st.session_state["mes_selecionado_grupo"] = "Todos os meses"

    mes_selecionado = st.selectbox(
        "Mês", options=opcoes_mes,
        format_func=lambda m: m if m == "Todos os meses" else MESES_NOME.get(m, m),
        key="mes_selecionado_grupo",
    )
    if mes_selecionado != "Todos os meses":
        df_filtrado = df_filtrado[df_filtrado["mes"].astype(str) == mes_selecionado]

    agrupado = (
        df_filtrado.groupby("grupo", as_index=False, observed=True)["vendas"].sum()
        .sort_values("vendas", ascending=False).head(20)
    )
    if agrupado.empty:
        st.info("Sem dados para o filtro selecionado.")
        return

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=agrupado["grupo"].astype(str), y=agrupado["vendas"],
        marker=dict(color=COR_DESTAQUE),
        text=[formatar_moeda_br(v) for v in agrupado["vendas"]],
        textposition="outside", textfont=dict(color=COR_TEXTO_SECUNDARIO),
        hovertext=[f"{g}<br>Vendas: {formatar_moeda_br(v)}" for g, v in zip(agrupado["grupo"], agrupado["vendas"])],
        hoverinfo="text",
    ))
    fig.update_layout(
        plot_bgcolor=COR_CARD, paper_bgcolor=COR_CARD, font=dict(color=COR_TEXTO),
        margin=dict(l=10, r=10, t=20, b=10), height=440,
        xaxis=dict(showgrid=False, color=COR_TEXTO_SECUNDARIO, tickangle=-35,
                   categoryorder="array", categoryarray=agrupado["grupo"].astype(str).tolist()),
        yaxis=dict(showgrid=True, gridcolor=COR_CARD_BORDA, color=COR_TEXTO_SECUNDARIO, tickprefix="R$ "),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)
    if len(agrupado) == 20:
        st.caption("Mostrando os 20 grupos com maior venda no período selecionado.")


def curva_abc_produtos(df_filtrado: pd.DataFrame):
    """
    Curva ABC (Pareto) de produtos: ordena os produtos do mais vendido
    para o menos vendido. Classe A = produtos que juntos somam até 80%
    das vendas, B = até 95%, C = o resto. É a forma clássica de mostrar
    concentração/cauda longa.

    Observação de qualidade de dados: o mesmo "codigo_produto" às vezes
    aparece na base com descrições ligeiramente diferentes (ex.: uma
    variação de texto entre notas fiscais). Se agrupássemos por
    (código + descrição), o mesmo produto virava duas barras separadas
    e a ordenação parecia "quebrada". Por isso agrupamos só por
    codigo_produto e usamos a descrição mais frequente daquele código
    como rótulo — cada produto físico vira uma única barra.
    """
    contagem_descricoes = (
        df_filtrado.groupby(["codigo_produto", "descricao_produto"], as_index=False, observed=True)
        .size()
        .sort_values("size", ascending=False)
    )
    descricao_por_codigo = (
        contagem_descricoes.drop_duplicates(subset="codigo_produto")
        .set_index("codigo_produto")["descricao_produto"]
    )

    por_produto = (
        df_filtrado.groupby("codigo_produto", as_index=False, observed=True)
        .agg(vendas=("vendas", "sum"), qtd=("qtd", "sum"))
        .sort_values("vendas", ascending=False).reset_index(drop=True)
    )
    por_produto["descricao_produto"] = por_produto["codigo_produto"].map(descricao_por_codigo)

    total = por_produto["vendas"].sum()
    if total <= 0 or por_produto.empty:
        st.info("Sem dados de produtos para o filtro selecionado.")
        return

    por_produto["pct_acumulado"] = por_produto["vendas"].cumsum() / total * 100
    por_produto["classe"] = por_produto["pct_acumulado"].map(lambda p: "A" if p <= 80 else ("B" if p <= 95 else "C"))

    resumo = por_produto.groupby("classe").agg(n_produtos=("codigo_produto", "count"), vendas=("vendas", "sum"))
    resumo = resumo.reindex(["A", "B", "C"]).fillna(0)
    resumo["pct_produtos"] = resumo["n_produtos"] / len(por_produto) * 100
    resumo["pct_vendas"] = resumo["vendas"] / total * 100

    c1, c2, c3 = st.columns(3)
    cores_classe = {"A": COR_POSITIVO, "B": COR_AMARELO, "C": COR_NEGATIVO}
    for col, classe in zip([c1, c2, c3], ["A", "B", "C"]):
        with col:
            st.markdown(f"""
            <div class="card-indicador">
                <div class="rotulo">Classe {classe}</div>
                <div class="valor" style="color:{cores_classe[classe]}">
                    {formatar_numero_br(resumo.loc[classe, 'n_produtos'])} produtos
                </div>
                <div style="color:{COR_TEXTO_SECUNDARIO}; font-size:0.85rem; margin-top:0.3rem;">
                    {formatar_percentual_br(resumo.loc[classe, 'pct_produtos'])} dos produtos ·
                    {formatar_percentual_br(resumo.loc[classe, 'pct_vendas'])} das vendas
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)

    top_n = st.slider("Quantos produtos mostrar no gráfico (ordenados por venda)", 10, 100, 30, step=10)
    amostra = por_produto.head(top_n).copy()
    amostra["rotulo"] = amostra["descricao_produto"].str.slice(0, 28)
    # rótulos duplicados (dois produtos com descrição parecida) confundiriam o eixo
    # X categórico do Plotly — deixamos cada barra com um rótulo único.
    amostra["rotulo"] = [
        f"{r} ({i + 1})" if amostra["rotulo"].tolist().count(r) > 1 else r
        for i, r in enumerate(amostra["rotulo"])
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=amostra["rotulo"], y=amostra["vendas"],
        marker=dict(color=[cores_classe[c] for c in amostra["classe"]]),
        name="Vendas",
        hovertext=[f"{d}<br>Vendas: {formatar_moeda_br(v)}<br>Classe {c} · Acumulado: {formatar_percentual_br(p)}"
                   for d, v, c, p in zip(amostra["descricao_produto"], amostra["vendas"],
                                         amostra["classe"], amostra["pct_acumulado"])],
        hoverinfo="text",
    ))
    fig.update_layout(
        plot_bgcolor=COR_CARD, paper_bgcolor=COR_CARD, font=dict(color=COR_TEXTO),
        margin=dict(l=10, r=10, t=30, b=100), height=460,
        xaxis=dict(showgrid=False, color=COR_TEXTO_SECUNDARIO, tickangle=-45,
                   categoryorder="array", categoryarray=amostra["rotulo"].tolist()),
        yaxis=dict(title="Vendas (R$)", showgrid=True, gridcolor=COR_CARD_BORDA,
                   color=COR_TEXTO_SECUNDARIO, tickprefix="R$ "),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("🔎 Buscar produto (tabela completa)"):
        busca = st.text_input("Filtrar por descrição ou código", "")
        tabela = por_produto.copy()
        if busca.strip():
            chave = _chave_comparacao(busca)
            tabela = tabela[
                tabela["descricao_produto"].map(_chave_comparacao).str.contains(chave, na=False)
                | tabela["codigo_produto"].astype(str).str.contains(busca.strip(), na=False)
            ]
        tabela_exibicao = tabela.head(300)[["codigo_produto", "descricao_produto", "qtd", "vendas", "classe"]].copy()
        tabela_exibicao["vendas"] = tabela_exibicao["vendas"].map(formatar_moeda_br)
        tabela_exibicao["qtd"] = tabela_exibicao["qtd"].map(formatar_numero_br)
        tabela_exibicao.columns = ["Código", "Produto", "Qtd.", "Vendas", "Classe ABC"]
        st.dataframe(tabela_exibicao, hide_index=True, use_container_width=True)
        if len(tabela) > 300:
            st.caption(f"Mostrando 300 de {len(tabela)} produtos encontrados — refine a busca para ver menos linhas.")


def grafico_ranking_vendedores(df_filtrado: pd.DataFrame):
    agrupado = (
        df_filtrado.groupby("vendedor", as_index=False, observed=True)["vendas"].sum()
    )
    agrupado = agrupado[agrupado["vendedor"].astype(str).str.strip() != ""]
    total = agrupado["vendas"].sum()
    if agrupado.empty or total <= 0:
        st.info("Sem dados de vendedores para o filtro selecionado.")
        return

    agrupado = agrupado.sort_values("vendas", ascending=False).reset_index(drop=True)
    top10_pct = agrupado.head(10)["vendas"].sum() / total * 100

    st.caption(
        f"Os **10 maiores vendedores** respondem por **{formatar_percentual_br(top10_pct)}** "
        f"das vendas do filtro atual, de um total de {formatar_numero_br(len(agrupado))} vendedores."
    )

    top_n = st.slider("Quantos vendedores mostrar", 5, min(40, len(agrupado)), min(15, len(agrupado)), step=5)
    amostra = agrupado.head(top_n).sort_values("vendas", ascending=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=amostra["vendas"], y=amostra["vendedor"].astype(str), orientation="h",
        marker=dict(color=COR_DESTAQUE),
        text=[formatar_moeda_br(v) for v in amostra["vendas"]],
        textposition="outside", textfont=dict(color=COR_TEXTO_SECUNDARIO),
    ))
    fig.update_layout(
        plot_bgcolor=COR_CARD, paper_bgcolor=COR_CARD, font=dict(color=COR_TEXTO),
        margin=dict(l=10, r=60, t=20, b=10), height=max(380, 30 * len(amostra)),
        xaxis=dict(showgrid=True, gridcolor=COR_CARD_BORDA, color=COR_TEXTO_SECUNDARIO, tickprefix="R$ "),
        yaxis=dict(showgrid=False, color=COR_TEXTO_SECUNDARIO),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def painel_qualidade_dados(df_escopo: pd.DataFrame, usuario: dict):
    """Painel transparente com o que a EDA encontrou, escopado ao acesso do usuário logado."""
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        card_indicador("Notas fiscais", formatar_numero_br(df_escopo["nota_fiscal"].nunique())
                        if "nota_fiscal" in df_escopo.columns else "N/D")
    with c2:
        card_indicador("Produtos distintos", formatar_numero_br(df_escopo["codigo_produto"].nunique()))
    with c3:
        card_indicador("Vendedores", formatar_numero_br(df_escopo["vendedor"].nunique()))
    with c4:
        card_indicador("Grupos", formatar_numero_br(df_escopo["grupo"].nunique()))

    st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div class="card-indicador">
    <b>O que a análise exploratória encontrou nesta base</b>
    <ul>
        <li>A base não tem <b>nenhum valor nulo</b> nas colunas usadas neste painel.</li>
        <li>Só existem os meses <b>Jan, Fev, Mar, Abr e Jul</b> — Maio e Junho não aparecem
            nos dados carregados.</li>
        <li>A coluna <b>Devolução</b> vem zerada em 100% das linhas desta extração — por isso
            não há indicador de devolução no painel (mostraria sempre 0%, o que seria
            enganoso).</li>
        <li>A coluna <b>Filial</b> tem um único valor em toda a base (não é útil como filtro).</li>
        <li>As colunas prontas <b>% QTD Vendas</b> e <b>% Vendas</b> da planilha original não
            somam 100% no total (foram calculadas contra outra base de referência) — por isso
            todo percentual mostrado neste app é recalculado a partir dos dados carregados.</li>
        <li>Não existe coluna de <b>cliente/comprador</b> — as análises são por fornecedor,
            grupo, vendedor e produto.</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# DASHBOARD PRINCIPAL
# ============================================================
def tela_dashboard(login_df: pd.DataFrame, base_df: pd.DataFrame):
    usuario = st.session_state["usuario"]

    with st.sidebar:
        if LOGO_PATH and os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=120)
        st.markdown(f"### {usuario['nome']}")
        st.caption("Marca(s): " + ", ".join(usuario["marcas"]))
        st.divider()

        base_autorizada_previa = filtrar_por_acesso(base_df, usuario["chaves_marcas"])
        opcoes_grupo = sorted(base_autorizada_previa["grupo"].dropna().astype(str).unique().tolist())

        if "grupos_selecionados" not in st.session_state:
            st.session_state["grupos_selecionados"] = opcoes_grupo
        st.session_state["grupos_selecionados"] = [
            g for g in st.session_state["grupos_selecionados"] if g in opcoes_grupo
        ]

        st.markdown("**Grupo**")
        with st.container(border=True):
            grupos_selecionados = st.multiselect(
                "Grupos disponíveis", options=opcoes_grupo,
                key="grupos_selecionados", label_visibility="collapsed",
            )

        opcoes_vendedor = sorted(
            v for v in base_autorizada_previa["vendedor"].dropna().unique().tolist() if v
        )
        if opcoes_vendedor:
            st.markdown("**Vendedor**")
            vendedores_selecionados = st.multiselect(
                "Vendedores", options=opcoes_vendedor, default=[],
                label_visibility="collapsed", help="Deixe vazio para ver todos.",
            )
        else:
            vendedores_selecionados = []

        st.divider()
        if st.button("🔄 Recarregar dados", use_container_width=True,
                      help="Limpa o cache e relê a planilha do zero."):
            st.cache_data.clear()
            if os.path.isdir(PASTA_CACHE):
                for arquivo in os.listdir(PASTA_CACHE):
                    try:
                        os.remove(os.path.join(PASTA_CACHE, arquivo))
                    except OSError:
                        pass
            st.rerun()

        if st.button("Sair / Logout", use_container_width=True):
            for chave in ["autenticado", "usuario", "grupos_selecionados", "marca_selecionada",
                          "mes_selecionado_grupo"]:
                st.session_state.pop(chave, None)
            st.rerun()

    st.markdown(f"""
    <div class="cabecalho-app">
        <h1>{TITULO_APP}</h1>
        <p>{SUBTITULO_APP} — {usuario['nome']}</p>
        <div>{''.join(f'<span class="badge-marca">{m}</span>' for m in usuario['marcas'])}</div>
    </div>
    """, unsafe_allow_html=True)

    if not grupos_selecionados:
        st.warning("Selecione ao menos um grupo no menu lateral para ver os resultados.")
        return

    base_autorizada = filtrar_por_acesso(base_df, usuario["chaves_marcas"])
    base_filtrada = base_autorizada[base_autorizada["grupo"].astype(str).isin(grupos_selecionados)]
    if vendedores_selecionados:
        base_filtrada = base_filtrada[base_filtrada["vendedor"].isin(vendedores_selecionados)]

    if len(usuario["marcas"]) > 1:
        if st.session_state.get("marca_selecionada") not in usuario["marcas"]:
            st.session_state["marca_selecionada"] = usuario["marcas"][0]
        marca_selecionada = st.selectbox(
            "Marca", options=usuario["marcas"], key="marca_selecionada",
            help="Você representa mais de uma marca — escolha qual ver abaixo.",
        )
        chave = _chave_comparacao(marca_selecionada)
        base_filtrada = base_filtrada[base_filtrada["_chave_fornecedor"] == chave]
        st.markdown("<div style='height: 0.5rem'></div>", unsafe_allow_html=True)

    if base_filtrada.empty:
        st.info("Sem dados para os filtros selecionados.")
        return

    total_vendas = base_filtrada["vendas"].sum()
    total_qtd = base_filtrada["qtd"].sum()
    total_notas = base_filtrada["nota_fiscal"].nunique() if "nota_fiscal" in base_filtrada.columns else None
    ticket_medio = (total_vendas / total_notas) if total_notas else None

    cols = st.columns(4 if total_notas else 2)
    with cols[0]:
        card_indicador("Soma de Vendas", formatar_moeda_br(total_vendas), destaque=True)
    with cols[1]:
        card_indicador("Soma Qtd", formatar_numero_br(total_qtd))
    if total_notas:
        with cols[2]:
            card_indicador("Notas Fiscais", formatar_numero_br(total_notas))
        with cols[3]:
            card_indicador("Ticket Médio / NF", formatar_moeda_br(ticket_medio))

    st.markdown("<div style='height: 1.2rem'></div>", unsafe_allow_html=True)

    aba_geral, aba_produtos, aba_vendedores, aba_qualidade = st.tabs(
        ["📊 Visão Geral", "📦 Produtos (Curva ABC)", "🧑‍💼 Vendedores", "🔍 Qualidade dos Dados"]
    )

    with aba_geral:
        st.markdown("#### Vendas por mês")
        grafico_vendas_mensais(base_filtrada)

        with st.expander("📈 Ver projeção de vendas do próximo mês"):
            grafico_projecao_vendas(base_filtrada)

        st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)
        st.markdown("#### Vendas por grupo")
        grafico_vendas_por_grupo(base_filtrada)

    with aba_produtos:
        st.markdown("#### Curva ABC de produtos")
        st.caption(
            "Classe A = produtos que, somados, respondem por 80% das vendas; "
            "Classe B = até 95%; Classe C = os 5% finais."
        )
        curva_abc_produtos(base_filtrada)

    with aba_vendedores:
        st.markdown("#### Ranking de vendedores")
        grafico_ranking_vendedores(base_filtrada)

    with aba_qualidade:
        st.markdown("#### Qualidade dos dados (escopo do seu acesso)")
        painel_qualidade_dados(base_filtrada, usuario)


# ============================================================
# PONTO DE ENTRADA
# ============================================================
def main():
    st.set_page_config(
        page_title=TITULO_APP, page_icon="📊", layout="wide",
        initial_sidebar_state="expanded",
    )
    aplicar_css()

    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    try:
        with st.spinner("Carregando dados da planilha (a primeira execução pode levar alguns minutos)..."):
            login_df, base_df = carregar_dados(CAMINHO_PLANILHA)
    except ErroPlanilha as erro:
        st.error(str(erro))
        st.stop()
    except Exception as erro:
        st.error(f"Ocorreu um erro inesperado ao carregar a planilha: {erro}")
        st.stop()

    if not st.session_state["autenticado"]:
        tela_login(login_df)
    else:
        tela_dashboard(login_df, base_df)


if __name__ == "__main__":
    main()
