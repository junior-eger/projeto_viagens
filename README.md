# Análise de Viagens a Serviço — Portal da Transparência

Projeto avaliativo do curso Análise de Dados com Python — T6.

**Autor:** Junior Eger

## Objetivo

Construir um pipeline de dados com Python e PostgreSQL para baixar,
preservar, tratar e analisar dados de viagens a serviço do Governo
Federal, seguindo a arquitetura Medallion: Raw, Silver e Gold.

## Fonte dos dados

Dados do Portal da Transparência disponibilizados pela escola no
arquivo `viagens_2025_6meses.zip`, com o recorte de seis meses de 2025.

[Arquivo ZIP fornecido pela escola](https://drive.google.com/file/d/1pQjKacyHdIsyteknQbwKGM5_4hL5V4RV/view)

O ZIP contém:

- `2025_Viagem.csv`
- `2025_Pagamento.csv`
- `2025_Passagem.csv`
- `2025_Trecho.csv`

Os arquivos usam separador `;`, encoding `latin-1`, valores com
vírgula decimal e datas no formato `DD/MM/AAAA`.

## Tecnologias

- Python 3.14, utilizado no desenvolvimento.
- PostgreSQL e pgAdmin.
- psycopg2 para conexão e carga no banco.
- gdown para download do Google Drive.
- pandas para apresentação dos resultados.
- Matplotlib para os gráficos.
- Jupyter Notebook no VS Code.
- Git e GitHub para versionamento.

As versões das bibliotecas estão em `requirements.txt`.

## Arquivos do projeto

| Arquivo | Finalidade |
|---|---|
| `config.py` | Caminhos, parâmetros e leitura do `.env` |
| `banco.py` | Conexão e funções auxiliares do banco |
| `.env.example` | Modelo de configuração sem credenciais reais |
| `.gitignore` | Exclusão de credenciais, ambiente e dados locais |
| `requirements.txt` | Dependências e versões |
| `0_criar_banco.sql` | Criação das quatro tabelas Raw e quatro Silver |
| `1_extrair.py` | Download, descompactação e carga Raw |
| `2_transformar.py` | Conversões, cálculos e carga Silver |
| `3_analise.ipynb` | Gold, consultas, gráficos e interpretações |
| `teste_conexao.py` | Teste de conexão com o PostgreSQL |
| `conferir_csv.py` | Conferência dos cabeçalhos dos CSVs |

## Arquitetura

### Raw

Preserva todas as colunas e os valores dos CSVs como texto.
Os nomes das colunas foram padronizados para uso em SQL.

As tabelas não possuem constraints e todas as colunas são `VARCHAR`.

A carga é feita em blocos de 50.000 registros, com `TRUNCATE`
antes da inserção. As quatro cargas pertencem à mesma transação.

### Silver

Converte os dados para os tipos definidos no dicionário do projeto:

- Valores financeiros e diárias para `DECIMAL`.
- Datas para `DATE`.
- Sequência dos trechos para inteiro.
- Identificadores preservados como texto, incluindo zeros à esquerda.

As tabelas possuem chaves primárias, chaves estrangeiras e as
restrições adicionais exigidas no enunciado.

As repetições exatas são removidas de pagamentos e passagens,
comparando todas as colunas da Raw antes de selecionar as colunas
utilizadas na Silver.

Valores financeiros e datas vazios são convertidos para `NULL`.
O processo interrompe a carga ao encontrar erros de conversão ou
violações das restrições, desfazendo a transação.

### Gold

O notebook responde às sete perguntas de negócio com consultas SQL,
tabelas, seis gráficos e interpretações.

Também cria e atualiza agregações no PostgreSQL:

| Tabela | VIEW | Agrupamento |
|---|---|---|
| `gold_pagamentos` | `vw_gold_pagamentos` | Órgão pagador e tipo de pagamento |
| `gold_trechos` | `vw_gold_trechos` | Transporte e UF de destino |

As VIEWs utilizam `JOIN` e `GROUP BY`. As tabelas armazenam os
resultados das agregações no momento da execução do notebook.

## Regras de cálculo

### Custo líquido da viagem

`valor_total = valor_diarias + valor_passagens + valor_outros_gastos - valor_devolucao`

Se algum componente estiver ausente, o total fica `NULL`.

### Duração

`duracao_dias = data_fim - data_inicio`

A duração representa a diferença entre as datas. Viagens iniciadas
e encerradas no mesmo dia têm duração zero.

Datas finais posteriores a junho de 2025 foram preservadas.

### Custo médio por destino

Cada viagem é contada uma vez por combinação de cidade e UF visitadas.

Utiliza-se o custo líquido completo da viagem, sem rateio entre
destinos. Assim, os valores de diferentes destinos não devem ser
somados como gastos exclusivos de cada cidade.

### Pagamentos

As médias são calculadas pela soma dos valores dividida pela
quantidade de registros com valor informado.

O total por órgão pagador soma todos os tipos de pagamento,
inclusive restituições, conforme registrados. Essa métrica é
diferente do custo líquido calculado na tabela de viagens.

## Como executar no Windows

### 1. Preparar o ambiente

Instale Python, PostgreSQL, Git e VS Code.

No VS Code, habilite as extensões Python e Jupyter.

Abra a pasta do projeto e execute no terminal:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Configurar a conexão

Copie `.env.example` para `.env` e preencha:

```dotenv
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=sua_senha_aqui
POSTGRES_DATABASE=projeto_viagens
```

Use sua senha local do PostgreSQL. O `.env` não deve ser enviado
ao GitHub.

Confirme o identificador do ZIP em `config.py`:

```python
DRIVE_FILE_ID = "1pQjKacyHdIsyteknQbwKGM5_4hL5V4RV"
```

O download depende da disponibilidade do arquivo e das permissões
de acesso no Google Drive.

### 3. Preparar o banco

Abra `0_criar_banco.sql` no pgAdmin.

1. No Query Tool conectado ao banco `postgres`, com autocommit
   habilitado, execute somente `CREATE DATABASE projeto_viagens;`.
   Pule essa instrução se o banco já existir.
2. Abra outro Query Tool conectado ao banco `projeto_viagens`.
3. Execute somente os comandos `CREATE TABLE` do arquivo.

Teste a conexão no terminal do VS Code:

```powershell
.\.venv\Scripts\python.exe teste_conexao.py
```


### 4. Executar a extração

```powershell
.\.venv\Scripts\python.exe 1_extrair.py
```

O script baixa o ZIP, descompacta os CSVs na pasta `data`
e carrega as quatro tabelas Raw.

### 5. Executar a transformação

```powershell
.\.venv\Scripts\python.exe 2_transformar.py
```

O script reconstrói as quatro tabelas Silver em uma transação,
carregando viagens antes dos registros dependentes.

### 6. Executar as análises

Abra `3_analise.ipynb`, salvo na mesma pasta de `banco.py`
e `config.py`.

Selecione o kernel da `.venv` e execute todas as células em ordem.

Após uma nova carga Silver, execute novamente o notebook para
atualizar as tabelas Gold, as análises e os gráficos.

## Contagens verificadas

| Conjunto | Raw | Silver |
|---|---:|---:|
| Viagens | 341.860 | 341.860 |
| Pagamentos | 606.916 | 568.811 |
| Passagens | 167.260 | 167.210 |
| Trechos | 763.349 | 763.349 |
| **Total** | **1.879.385** | **1.841.230** |

Foram removidas 38.105 repetições exatas em pagamentos e 50 em
passagens. Os registros originais permanecem na Raw.

## Principais resultados

1. O Ministério da Justiça e Segurança Pública apresentou o maior
   custo líquido entre os órgãos superiores: R$ 486,93 milhões.

2. Tejupá/SP, Chavantes/SP e Teolândia/BA apresentaram os maiores
   custos médios por viagem. Cada destino tinha apenas uma viagem,
   limitando a generalização do resultado.

3. A maior duração registrada foi de 383 dias, em uma viagem do
   Ministério da Previdência Social, com custo líquido de R$ 0,00.

4. PASSAGEM apresentou o maior valor médio por pagamento:
   R$ 1.856,78.

5. Veículo Oficial foi o transporte mais utilizado:
   386.424 trechos.

6. São Paulo foi a UF de destino mais frequente:
   82.722 trechos.

7. A categoria "Sigiloso" apresentou R$ 170.659.883,35 em pagamentos.
   Entre os órgãos identificados, o Fundo Nacional de Segurança
   Pública liderou com R$ 141.911.719,64.

## Validações realizadas

- Contagens das tabelas Raw comparadas às linhas lidas dos CSVs.
- Conferência de repetições exatas e chaves duplicadas.
- Conferência de vínculos com viagens.
- Verificação dos campos obrigatórios selecionados.
- Verificação de valores negativos nos campos sujeitos a `CHECK`.
- Comparação dos custos e durações com suas fórmulas.
- Conferência da quantidade de trechos representados na Gold.
- Comparação das tabelas Gold com suas VIEWs por `EXCEPT ALL`.
- Execução do notebook após reiniciar o kernel.
- Verificação de dependências com `pip check`.

## Limitações

- Existem 26.659 trechos classificados como transporte "Inválido".
  A classificação foi mantida visível, sem presumir o transporte.
- "Sigiloso" não identifica um órgão específico e pode reunir
  registros com diferentes órgãos omitidos.
- A viagem de 383 dias com custo zero merece investigação na origem;
  o resultado isolado não comprova erro nem ausência de despesas
  fora da base.
- Maiores gastos totais não comprovam ineficiência.
- As análises descrevem o recorte fornecido pela escola e não
  representam automaticamente todas as viagens do ano de 2025.

## Melhorias futuras

- Automatizar a emissão de relatórios de qualidade.
- Registrar logs de execução em arquivo.
- Investigar valores atípicos com contexto dos dados de origem.
- Padronizar classificações de transporte e localização.
- Acrescentar testes automatizados para as regras de transformação.

## Credenciais e dados locais

O `.gitignore` exclui `.env`, `.venv`, caches, CSVs, ZIPs e `data/`.

O repositório contém o código e o modelo `.env.example`.
Os dados são obtidos pelo script de extração.