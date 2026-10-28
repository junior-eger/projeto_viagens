import csv
from itertools import islice

from psycopg2 import sql
from psycopg2.extras import execute_values

from banco import conectar
from config import (
    ARQUIVOS,
    CSV_ENCODING,
    CSV_SEPARADOR,
    TAMANHO_BLOCO,
)

import zipfile

import gdown

from config import DRIVE_FILE_ID, PASTA_DADOS


def baixar_zip():
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    caminho_zip = PASTA_DADOS / "viagens_2025_6meses.zip"

    print("Baixando o ZIP do Google Drive...")

    resultado = gdown.download(
        id=DRIVE_FILE_ID,
        output=str(caminho_zip),
        quiet=False,
    )

    if resultado is None or not zipfile.is_zipfile(caminho_zip):
        raise RuntimeError("O download não gerou um ZIP válido.")

    print("Download concluído. ZIP válido!")

    with zipfile.ZipFile(caminho_zip) as arquivo_zip:
        print("\nArquivos dentro do ZIP:")
        for nome in arquivo_zip.namelist():
            print(nome)

def extrair_csvs():
    caminho_zip = PASTA_DADOS / "viagens_2025_6meses.zip"

    nomes_csv = [
        "2025_Viagem.csv",
        "2025_Pagamento.csv",
        "2025_Passagem.csv",
        "2025_Trecho.csv",
    ]

    with zipfile.ZipFile(caminho_zip) as arquivo_zip:
        for nome in nomes_csv:
            arquivo_zip.extract(nome, path=PASTA_DADOS)
            print(f"CSV extraído: {nome}")

def carregar_raw():
    conexao = conectar()

    try:
        # Todas as cargas fazem parte da mesma transação.
        with conexao:
            with conexao.cursor() as cursor:
                tabelas = sql.SQL(", ").join(
                    sql.Identifier(item["tabela_raw"])
                    for item in ARQUIVOS.values()
                )

                cursor.execute(
                    sql.SQL("TRUNCATE TABLE {}").format(tabelas)
                )

                for item in ARQUIVOS.values():
                    caminho = PASTA_DADOS / item["csv"]
                    tabela = item["tabela_raw"]
                    total = 0

                    comando = sql.SQL(
                        "INSERT INTO {} VALUES %s"
                    ).format(sql.Identifier(tabela)).as_string(conexao)

                    with caminho.open(
                        encoding=CSV_ENCODING,
                        newline="",
                    ) as arquivo:
                        leitor = csv.reader(
                            arquivo,
                            delimiter=CSV_SEPARADOR,
                        )
                        cabecalho = next(leitor)

                        while True:
                            bloco = list(islice(leitor, TAMANHO_BLOCO))

                            if not bloco:
                                break

                            for linha in bloco:
                                if len(linha) != len(cabecalho):
                                    raise ValueError(
                                        f"{caminho.name}: registro com "
                                        f"{len(linha)} campos; esperado "
                                        f"{len(cabecalho)}."
                                    )

                            execute_values(
                                cursor,
                                comando,
                                bloco,
                                page_size=1000,
                            )

                            total += len(bloco)
                            print(f"{tabela}: {total:,} linhas processadas")

                    cursor.execute(
                        sql.SQL("SELECT COUNT(*) FROM {}").format(
                            sql.Identifier(tabela)
                        )
                    )
                    quantidade_banco = cursor.fetchone()[0]

                    if quantidade_banco != total:
                        raise RuntimeError(
                            f"Contagem diferente em {tabela}: "
                            f"CSV={total}, banco={quantidade_banco}"
                        )

        print("Carga Raw concluída e confirmada no banco!")

    finally:
        conexao.close()

if __name__ == "__main__":
    try:
        baixar_zip()
        extrair_csvs()
        carregar_raw()
    except Exception as erro:
        print(f"Falha na extração: {erro}")
        raise SystemExit(1)