"""
Módulo de extração e chunking de PDFs de contratos.

Responsável por:
- Ler o texto de cada página de um PDF (usando pdfplumber, que lida bem
  com tabelas simples e texto corrido).
- Dividir o texto em "chunks" (pedaços) menores, tentando não cortar uma
  cláusula no meio, para que a IA sempre receba um trecho com sentido completo.

Funciona para qualquer tipo de contrato (aluguel, prestação de serviço,
fornecimento, trabalhista, societário, etc.) — não é específico de nenhum
segmento ou área de atuação.
"""

import re
import pdfplumber

# Tamanho máximo de um chunk (em caracteres). Contratos usam frases longas,
# então usamos um limite generoso, mas ainda seguro para o contexto da IA.
TAMANHO_MAXIMO_CHUNK = 1800
SOBREPOSICAO_CHUNK = 200  # caracteres repetidos entre chunks vizinhos, para não perder contexto na borda

# Padrão que tenta reconhecer o início de uma cláusula/artigo numerado,
# ex: "Cláusula 3ª", "CLÁUSULA TERCEIRA", "Art. 5º", "5.1", "Parágrafo único"
PADRAO_CLAUSULA = re.compile(
    r"(?im)^\s*(cl[aá]usula\s+\w+|art(?:igo)?\.?\s*\d+|par[aá]grafo\s+\w+|\d+(?:\.\d+)*\s*[-–.)])"
)


def extrair_paginas(caminho_pdf):
    """
    Abre um PDF e retorna uma lista de tuplas (numero_da_pagina, texto_da_pagina).
    A numeração de página começa em 1, como um humano leria o documento.
    """
    paginas = []
    with pdfplumber.open(caminho_pdf) as pdf:
        for indice, pagina in enumerate(pdf.pages, start=1):
            texto = pagina.extract_text() or ""

            # Tenta também capturar texto de tabelas simples, juntando célula a célula.
            # Contratos frequentemente têm tabelas de valores/prazos que o extract_text
            # sozinho não organiza bem.
            texto_tabelas = ""
            try:
                tabelas = pagina.extract_tables()
            except Exception:
                tabelas = []
            for tabela in tabelas:
                for linha in tabela:
                    celulas = [c.strip() for c in linha if c]
                    if celulas:
                        texto_tabelas += " | ".join(celulas) + "\n"

            texto_completo = (texto + "\n" + texto_tabelas).strip()
            paginas.append((indice, texto_completo))
    return paginas


def _dividir_em_blocos_por_clausula(texto):
    """
    Quebra o texto em blocos, tentando iniciar um novo bloco sempre que
    encontra o início aparente de uma cláusula/artigo. Isso evita que uma
    cláusula fique cortada ao meio entre dois chunks diferentes.
    """
    posicoes = [m.start() for m in PADRAO_CLAUSULA.finditer(texto)]
    if not posicoes:
        return [texto]

    blocos = []
    for i, inicio in enumerate(posicoes):
        fim = posicoes[i + 1] if i + 1 < len(posicoes) else len(texto)
        bloco = texto[inicio:fim].strip()
        if bloco:
            blocos.append(bloco)

    # Texto antes da primeira cláusula reconhecida (ex: preâmbulo do contrato)
    if posicoes[0] > 0:
        preambulo = texto[: posicoes[0]].strip()
        if preambulo:
            blocos.insert(0, preambulo)

    return blocos


def gerar_chunks(nome_arquivo, paginas):
    """
    Recebe o nome do arquivo e a lista de (pagina, texto) e devolve uma lista
    de dicionários no formato:
        {"texto": "...", "fonte": "Contrato_X.pdf", "pagina": 3}
    Cada chunk tenta respeitar os limites de cláusula e o tamanho máximo definido.
    """
    chunks = []

    for numero_pagina, texto_pagina in paginas:
        if not texto_pagina.strip():
            continue

        blocos = _dividir_em_blocos_por_clausula(texto_pagina)

        for bloco in blocos:
            if len(bloco) <= TAMANHO_MAXIMO_CHUNK:
                chunks.append({"texto": bloco, "fonte": nome_arquivo, "pagina": numero_pagina})
                continue

            # Bloco muito grande (cláusula longa demais): quebra em pedaços
            # menores, com sobreposição, para não perder o fio da meada.
            inicio = 0
            while inicio < len(bloco):
                fim = min(inicio + TAMANHO_MAXIMO_CHUNK, len(bloco))
                pedaco = bloco[inicio:fim].strip()
                if pedaco:
                    chunks.append({"texto": pedaco, "fonte": nome_arquivo, "pagina": numero_pagina})
                if fim == len(bloco):
                    break
                inicio = fim - SOBREPOSICAO_CHUNK

    return chunks


def processar_pdf(caminho_pdf, nome_arquivo):
    """Função de conveniência: extrai páginas e já devolve os chunks prontos."""
    paginas = extrair_paginas(caminho_pdf)
    return gerar_chunks(nome_arquivo, paginas)


def contar_paginas(caminho_pdf):
    """Conta rapidamente o número de páginas de um PDF (usado para limites da versão teste)."""
    with pdfplumber.open(caminho_pdf) as pdf:
        return len(pdf.pages)
