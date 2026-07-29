"""
Servidor mínimo de validação de licenças.

Hospede este serviço (ex: Render, Railway, PythonAnywhere — todos aceitam
Python puro, sem precisar de Docker) e configure o app do cliente para
apontar para a URL pública dele (variável LICENSE_SERVER_URL no .env do
cliente).

Você controla o status de cada cliente por aqui. Se ele não pagar a
mensalidade, basta marcar a licença como "suspenso" (via manage.py ou pelos
endpoints /admin/*) e o aplicativo dele para de funcionar na próxima
validação — no máximo após o período de tolerância offline configurado em
modules/license_manager.py (GRACE_PERIOD_DIAS).
"""

import os
import sqlite3
from datetime import datetime, timezone

from flask import Flask, jsonify, request

app = Flask(__name__)

CAMINHO_BANCO = os.environ.get("LICENSE_DB_PATH", "licenses.db")
CHAVE_ADMIN = os.environ.get("ADMIN_KEY", "troque-esta-chave")


def obter_conexao():
    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row
    return conexao


def inicializar_banco():
    with obter_conexao() as conexao:
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS clientes (
                license_key TEXT PRIMARY KEY,
                nome_cliente TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ativo',
                expira_em TEXT,
                observacao TEXT
            )
            """
        )


inicializar_banco()


def _eh_admin():
    return request.headers.get("X-Admin-Key") == CHAVE_ADMIN


@app.route("/validate", methods=["POST"])
def validar_licenca():
    """Endpoint chamado pelo app do cliente para checar se pode continuar rodando."""
    corpo = request.get_json(silent=True) or {}
    chave = corpo.get("license_key", "")

    with obter_conexao() as conexao:
        linha = conexao.execute(
            "SELECT * FROM clientes WHERE license_key = ?", (chave,)
        ).fetchone()

    if not linha:
        return jsonify({"status": "invalido", "mensagem": "Chave de licença não reconhecida."})

    status = linha["status"]
    expira_em = linha["expira_em"]

    # Se passou da data de expiração, trata como expirado mesmo que o campo
    # "status" ainda diga "ativo" (evita esquecer de atualizar manualmente).
    if expira_em:
        try:
            data_expiracao = datetime.fromisoformat(expira_em).replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > data_expiracao:
                status = "expirado"
        except ValueError:
            pass

    mensagens = {
        "ativo": "",
        "suspenso": "Assinatura suspensa. Entre em contato com o suporte para regularizar o pagamento.",
        "expirado": "Assinatura expirada. Entre em contato com o suporte para renovar.",
        "cancelado": "Assinatura cancelada.",
    }

    return jsonify(
        {
            "status": status,
            "expira_em": expira_em,
            "mensagem": mensagens.get(status, "Licença inativa."),
        }
    )


@app.route("/admin/clientes", methods=["GET"])
def listar_clientes():
    if not _eh_admin():
        return jsonify({"erro": "não autorizado"}), 401
    with obter_conexao() as conexao:
        linhas = conexao.execute("SELECT * FROM clientes").fetchall()
    return jsonify([dict(l) for l in linhas])


@app.route("/admin/clientes", methods=["POST"])
def criar_ou_atualizar_cliente():
    """
    Cria ou atualiza um cliente. Corpo esperado (JSON):
        {"license_key": "...", "nome_cliente": "...", "status": "ativo",
         "expira_em": "2026-12-31", "observacao": "opcional"}
    Requer o header X-Admin-Key com o valor de ADMIN_KEY.
    """
    if not _eh_admin():
        return jsonify({"erro": "não autorizado"}), 401

    corpo = request.get_json(silent=True) or {}
    chave = corpo.get("license_key")
    nome = corpo.get("nome_cliente")
    status = corpo.get("status", "ativo")
    expira_em = corpo.get("expira_em")
    observacao = corpo.get("observacao", "")

    if not chave or not nome:
        return jsonify({"erro": "license_key e nome_cliente são obrigatórios"}), 400

    with obter_conexao() as conexao:
        conexao.execute(
            """
            INSERT INTO clientes (license_key, nome_cliente, status, expira_em, observacao)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(license_key) DO UPDATE SET
                nome_cliente = excluded.nome_cliente,
                status = excluded.status,
                expira_em = excluded.expira_em,
                observacao = excluded.observacao
            """,
            (chave, nome, status, expira_em, observacao),
        )

    return jsonify({"ok": True})


@app.route("/", methods=["GET"])
def raiz():
    return jsonify({"servico": "servidor de licenças", "status": "online"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
