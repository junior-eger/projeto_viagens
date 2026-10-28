from psycopg2.extras import execute_values

from config import TAMANHO_BLOCO

from banco import conectar

from datetime import datetime
from decimal import Decimal, InvalidOperation


def converter_decimal(valor):
    """Converte texto brasileiro, como 1.272,97, para Decimal."""
    if valor is None or str(valor).strip() == "":
        return None

    texto = str(valor).strip()
    texto = texto.replace(".", "").replace(",", ".")

    try:
        numero = Decimal(texto)
    except InvalidOperation as erro:
        raise ValueError(f"Valor monetário inválido: {valor!r}") from erro

    if not numero.is_finite():
        raise ValueError(f"Valor monetário inválido: {valor!r}")

    return numero


def converter_data(valor):
    """Converte texto DD/MM/AAAA para uma data."""
    if valor is None or str(valor).strip() == "":
        return None

    try:
        return datetime.strptime(str(valor).strip(), "%d/%m/%Y").date()
    except ValueError as erro:
        raise ValueError(f"Data inválida: {valor!r}") from erro


def carregar_viagens(conexao):
    colunas = [
        "id_viagem",
        "num_proposta",
        "situacao",
        "viagem_urgente",
        "cod_orgao_superior",
        "nome_orgao_superior",
        "nome_viajante",
        "cargo",
        "data_inicio",
        "data_fim",
        "destinos",
        "motivo",
        "valor_diarias",
        "valor_passagens",
        "valor_devolucao",
        "valor_outros_gastos",
    ]

    comando_insert = """
        INSERT INTO silver_viagem (
            id_viagem, num_proposta, situacao, viagem_urgente,
            cod_orgao_superior, nome_orgao_superior,
            nome_viajante, cargo, data_inicio, data_fim,
            destinos, motivo, valor_diarias, valor_passagens,
            valor_devolucao, valor_outros_gastos,
            valor_total, duracao_dias
        ) VALUES %s
    """

    total = 0

    with conexao.cursor(name="leitura_viagens") as leitura:
        leitura.execute(
            f"SELECT {', '.join(colunas)} FROM raw_viagem"
        )

        with conexao.cursor() as escrita:
            while True:
                bloco = leitura.fetchmany(TAMANHO_BLOCO)

                if not bloco:
                    break

                linhas_tratadas = []

                for linha in bloco:
                    valores = [
                        valor.strip() if valor is not None else None
                        for valor in linha
                    ]

                    id_viagem = valores[0]

                    if not id_viagem or not valores[5]:
                        raise ValueError(
                            f"Viagem {id_viagem!r}: campo obrigatório vazio."
                        )

                    valores[8] = converter_data(valores[8])
                    valores[9] = converter_data(valores[9])

                    for indice in range(12, 16):
                        valores[indice] = converter_decimal(
                            valores[indice]
                        )

                    inicio, fim = valores[8], valores[9]
                    diarias, passagens, devolucao, outros = valores[12:16]

                    if inicio is not None and fim is not None:
                        duracao = (fim - inicio).days
                        if duracao < 0:
                            raise ValueError(
                                f"Viagem {id_viagem}: duração negativa."
                            )
                    else:
                        duracao = None

                    if all(
                        valor is not None
                        for valor in (diarias, passagens, devolucao, outros)
                    ):
                        valor_total = (
                            diarias + passagens + outros - devolucao
                        )
                    else:
                        valor_total = None

                    valores.extend([valor_total, duracao])
                    linhas_tratadas.append(tuple(valores))

                execute_values(
                    escrita,
                    comando_insert,
                    linhas_tratadas,
                    page_size=1000,
                )

                total += len(linhas_tratadas)
                print(f"silver_viagem: {total:,} linhas processadas")

    return total
def carregar_pagamentos(conexao):
    total = 0

    with conexao.cursor(name="leitura_pagamentos") as leitura:
        leitura.execute("""
            SELECT
                id_viagem,
                num_proposta,
                nome_orgao_pagador,
                nome_ug_pagadora,
                tipo_pagamento,
                valor
            FROM (
                SELECT DISTINCT *
                FROM raw_pagamento
            ) AS pagamentos_distintos
        """)

        with conexao.cursor() as escrita:
            while True:
                bloco = leitura.fetchmany(TAMANHO_BLOCO)

                if not bloco:
                    break

                linhas_tratadas = []

                for linha in bloco:
                    valores = [
                        valor.strip() if valor is not None else None
                        for valor in linha
                    ]

                    if not valores[0] or not valores[4]:
                        raise ValueError(
                            "Pagamento com viagem ou tipo vazio."
                        )

                    valores[5] = converter_decimal(valores[5])
                    linhas_tratadas.append(tuple(valores))

                execute_values(
                    escrita,
                    """
                    INSERT INTO silver_pagamento (
                        id_viagem,
                        num_proposta,
                        nome_orgao_pagador,
                        nome_ug_pagadora,
                        tipo_pagamento,
                        valor
                    ) VALUES %s
                    """,
                    linhas_tratadas,
                    page_size=1000,
                )

                total += len(linhas_tratadas)
                print(f"silver_pagamento: {total:,} linhas processadas")

    return total

def carregar_passagens(conexao):
    total = 0

    with conexao.cursor(name="leitura_passagens") as leitura:
        leitura.execute("""
            SELECT
                id_viagem,
                meio_transporte,
                pais_origem_ida,
                uf_origem_ida,
                cidade_origem_ida,
                pais_destino_ida,
                uf_destino_ida,
                cidade_destino_ida,
                valor_passagem,
                taxa_servico,
                data_emissao
            FROM (
                SELECT DISTINCT *
                FROM raw_passagem
            ) AS passagens_distintas
        """)

        with conexao.cursor() as escrita:
            while True:
                bloco = leitura.fetchmany(TAMANHO_BLOCO)

                if not bloco:
                    break

                linhas_tratadas = []

                for linha in bloco:
                    valores = [
                        valor.strip() if valor is not None else None
                        for valor in linha
                    ]

                    if not valores[0]:
                        raise ValueError("Passagem com viagem vazia.")

                    valores[8] = converter_decimal(valores[8])
                    valores[9] = converter_decimal(valores[9])
                    valores[10] = converter_data(valores[10])

                    linhas_tratadas.append(tuple(valores))

                execute_values(
                    escrita,
                    """
                    INSERT INTO silver_passagem (
                        id_viagem,
                        meio_transporte,
                        pais_origem_ida,
                        uf_origem_ida,
                        cidade_origem_ida,
                        pais_destino_ida,
                        uf_destino_ida,
                        cidade_destino_ida,
                        valor_passagem,
                        taxa_servico,
                        data_emissao
                    ) VALUES %s
                    """,
                    linhas_tratadas,
                    page_size=1000,
                )

                total += len(linhas_tratadas)
                print(f"silver_passagem: {total:,} linhas processadas")

    with conexao.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM silver_passagem")
        quantidade = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM (
                SELECT DISTINCT *
                FROM raw_passagem
            ) AS passagens_distintas
        """)
        esperado = cursor.fetchone()[0]

        if not (quantidade == total == esperado):
            raise RuntimeError("Contagem de passagens divergente.")

    return total

def carregar_trechos(conexao):
    total = 0

    with conexao.cursor(name="leitura_trechos") as leitura:
        leitura.execute("""
            SELECT
                id_viagem,
                sequencia_trecho,
                origem_data,
                origem_uf,
                origem_cidade,
                destino_data,
                destino_uf,
                destino_cidade,
                meio_transporte,
                numero_diarias
            FROM raw_trecho
        """)

        with conexao.cursor() as escrita:
            while True:
                bloco = leitura.fetchmany(TAMANHO_BLOCO)

                if not bloco:
                    break

                linhas_tratadas = []

                for linha in bloco:
                    valores = [
                        valor.strip() if valor is not None else None
                        for valor in linha
                    ]

                    if not valores[0] or not valores[1]:
                        raise ValueError(
                            "Trecho com viagem ou sequência vazia."
                        )

                    valores[1] = int(valores[1])
                    valores[2] = converter_data(valores[2])
                    valores[5] = converter_data(valores[5])
                    valores[9] = converter_decimal(valores[9])

                    linhas_tratadas.append(tuple(valores))

                execute_values(
                    escrita,
                    """
                    INSERT INTO silver_trecho (
                        id_viagem,
                        sequencia_trecho,
                        origem_data,
                        origem_uf,
                        origem_cidade,
                        destino_data,
                        destino_uf,
                        destino_cidade,
                        meio_transporte,
                        numero_diarias
                    ) VALUES %s
                    """,
                    linhas_tratadas,
                    page_size=1000,
                )

                total += len(linhas_tratadas)
                print(f"silver_trecho: {total:,} linhas processadas")

    with conexao.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM silver_trecho")
        quantidade = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM raw_trecho")
        esperado = cursor.fetchone()[0]

        if not (quantidade == total == esperado):
            raise RuntimeError("Contagem de trechos divergente.")

    return total

def transformar():
    conexao = conectar()

    try:
        with conexao:
            with conexao.cursor() as cursor:
                cursor.execute("""
                    TRUNCATE TABLE
                        silver_pagamento,
                        silver_passagem,
                        silver_trecho,
                        silver_viagem
                    RESTART IDENTITY
                """)

            total_viagens = carregar_viagens(conexao)
            total_pagamentos = carregar_pagamentos(conexao)
            carregar_passagens(conexao)
            carregar_trechos(conexao)

            with conexao.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM silver_viagem")
                quantidade_viagens = cursor.fetchone()[0]

                if quantidade_viagens != total_viagens:
                    raise RuntimeError(
                        "Contagem de viagens divergente."
                    )

                cursor.execute("SELECT COUNT(*) FROM silver_pagamento")
                quantidade_pagamentos = cursor.fetchone()[0]

                cursor.execute("""
                    SELECT COUNT(*)
                    FROM (
                        SELECT DISTINCT *
                        FROM raw_pagamento
                    ) AS pagamentos_distintos
                """)
                esperado_pagamentos = cursor.fetchone()[0]

                if not (
                    quantidade_pagamentos
                    == total_pagamentos
                    == esperado_pagamentos
                ):
                    raise RuntimeError(
                        "Contagem de pagamentos divergente."
                    )

        print(f"Viagens confirmadas: {total_viagens:,}")
        print(f"Pagamentos confirmados: {total_pagamentos:,}")
        print("Transação Silver concluída!")

    finally:
        conexao.close()


if __name__ == "__main__":
    try:
        transformar()
    except Exception as erro:
        print(f"Falha na transformação: {erro}")
        raise SystemExit(1)