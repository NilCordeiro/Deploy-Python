"""
Script de linha de comando para gerenciar clientes diretamente no banco local
(licenses.db) — útil se você preferir não ficar montando requisições HTTP
manualmente para ativar/suspender um cliente.

IMPORTANTE: rode este script na MESMA máquina/servidor onde está o
licenses.db usado pelo server.py (ou aponte LICENSE_DB_PATH para o mesmo
arquivo). Se o servidor estiver hospedado num serviço como Render, você
provavelmente vai preferir usar os endpoints /admin/clientes com curl ou
Postman em vez deste script, a não ser que tenha acesso de shell ao servidor.

Exemplos:
    python manage.py adicionar --chave ABC123 --nome "Empresa X" --expira 2026-12-31
    python manage.py suspender --chave ABC123
    python manage.py reativar --chave ABC123 --expira 2027-01-31
    python manage.py listar
"""

import argparse
import sqlite3

CAMINHO_BANCO = "licenses.db"


def conectar():
    conexao = sqlite3.connect(CAMINHO_BANCO)
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
    return conexao


def adicionar(args):
    with conectar() as c:
        c.execute(
            """
            INSERT INTO clientes (license_key, nome_cliente, status, expira_em)
            VALUES (?, ?, 'ativo', ?)
            ON CONFLICT(license_key) DO UPDATE SET
                nome_cliente = excluded.nome_cliente,
                expira_em = excluded.expira_em,
                status = 'ativo'
            """,
            (args.chave, args.nome, args.expira),
        )
    print(f"Cliente '{args.nome}' adicionado/atualizado com chave {args.chave} (ativo até {args.expira}).")


def suspender(args):
    with conectar() as c:
        c.execute("UPDATE clientes SET status='suspenso' WHERE license_key=?", (args.chave,))
    print(f"Licença {args.chave} suspensa. O app do cliente vai bloquear na próxima validação.")


def reativar(args):
    with conectar() as c:
        c.execute(
            "UPDATE clientes SET status='ativo', expira_em=? WHERE license_key=?",
            (args.expira, args.chave),
        )
    print(f"Licença {args.chave} reativada até {args.expira}.")


def listar(args):
    with conectar() as c:
        linhas = c.execute(
            "SELECT license_key, nome_cliente, status, expira_em FROM clientes"
        ).fetchall()
    if not linhas:
        print("Nenhum cliente cadastrado ainda.")
    for linha in linhas:
        print(linha)


parser = argparse.ArgumentParser(description="Gerenciar licenças de clientes")
sub = parser.add_subparsers(required=True)

p_add = sub.add_parser("adicionar", help="Cria ou atualiza um cliente como ativo")
p_add.add_argument("--chave", required=True)
p_add.add_argument("--nome", required=True)
p_add.add_argument("--expira", required=True, help="Formato AAAA-MM-DD")
p_add.set_defaults(func=adicionar)

p_susp = sub.add_parser("suspender", help="Suspende a licença de um cliente (ex: inadimplência)")
p_susp.add_argument("--chave", required=True)
p_susp.set_defaults(func=suspender)

p_reat = sub.add_parser("reativar", help="Reativa a licença de um cliente")
p_reat.add_argument("--chave", required=True)
p_reat.add_argument("--expira", required=True)
p_reat.set_defaults(func=reativar)

p_list = sub.add_parser("listar", help="Lista todos os clientes cadastrados")
p_list.set_defaults(func=listar)

if __name__ == "__main__":
    args = parser.parse_args()
    args.func(args)
