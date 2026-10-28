import csv

from config import (
    ARQUIVOS,
    CSV_ENCODING,
    CSV_SEPARADOR,
    PASTA_DADOS,
)

for item in ARQUIVOS.values():
    caminho = PASTA_DADOS / item["csv"]

    with caminho.open(
        encoding=CSV_ENCODING,
        newline="",
    ) as arquivo:
        leitor = csv.reader(arquivo, delimiter=CSV_SEPARADOR)
        colunas = next(leitor)

    print(f"\nARQUIVO: {caminho.name}")
    for numero, coluna in enumerate(colunas, start=1):
        print(f"{numero}. {coluna}")