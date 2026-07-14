"""
Módulo: bank3_contacorrente.py

Responsabilidade
----------------
Executar o pipeline de leitura dos arquivos locais de conta corrente do
Banco 3 e carga RAW na tabela raw.bank3.

Contexto
--------
Este módulo faz parte da camada de pipelines do pacote lavesecexpress_etl.
Ele processa arquivos previamente disponibilizados em uma pasta local,
aplicando o parser específico do Banco 3 e persistindo os dados brutos no
banco.

Fluxo executado
---------------
1. Lê a pasta configurada em BANK3_CONFIG["pasta_arquivos"].
2. Valida se a configuração e o caminho existem.
3. Executa transformation_flow.run forçando a fonte bank3_contacorrente.
4. Aplica o parser sources.bank3.parser.parse_bank3.
5. Valida se o DataFrame foi retornado e possui dados.
6. Persiste os dados em raw.bank3 usando payload JSONB.

Observações
-----------
Este pipeline não usa Selenium, não baixa arquivos e não calcula janelas de
datas. O parâmetro mode é recebido apenas para manter compatibilidade com o
padrão dos demais pipelines.
"""

import os

from lavesecexpress_etl.core.transformation.transformation_flow import run
from lavesecexpress_etl.core.database.persistence import persist_dataframe_as_payload

from lavesecexpress_etl.sources.bank3.parser import parse_bank3
from lavesecexpress_etl.config.settings import BANK3_CONFIG


def run_bank3_pipeline(engine, mode):
    """
    Executa o pipeline de ingestão RAW da conta corrente do Banco 3.

    Parameters
    ----------
    engine
        SQLAlchemy Engine conectado ao banco PostgreSQL.

    mode : str
        Parâmetro recebido para compatibilidade com outros pipelines. Neste
        fluxo, não altera a seleção dos arquivos nem o período de extração.

    Returns
    -------
    None
        A função não retorna valor. Ela lê arquivos locais, aplica o parser do
        Banco 3 e persiste os registros em raw.bank3.

    Raises
    ------
    Exception
        Quando a pasta de arquivos do Banco 3 não está configurada ou o
        caminho não existe fisicamente.

    Notes
    -----
    - A fonte é forçada como bank3_contacorrente.
    - O parser usado é parse_bank3.
    - A persistência usa payload JSONB e hashid via lavesecexpress_etl.core.
    """

    print(f"\n========== BANK3 PIPELINE START | MODE: {mode.upper()} ==========")

    # 1️⃣ Caminho
    pasta = BANK3_CONFIG.get("pasta_arquivos")

    if not pasta:
        raise Exception("[BANK3 PIPELINE] Caminho 'pasta_arquivos' não configurado.")

    if not os.path.exists(pasta):
        raise Exception(f"[BANK3 PIPELINE] Caminho não encontrado: {pasta}")

    print(f"[BANK3 PIPELINE] Lendo arquivos de: {pasta}")

    # 2️⃣ 🔥 FORÇANDO PARSER ÚNICO
    data = run(
        pasta,
        lambda _: "bank3_contacorrente",  # <- aqui está o segredo
        parsers={
            "bank3_contacorrente": parse_bank3
        }
    )

    print(f"[BANK3 PIPELINE] Sources identificadas: {list(data.keys())}")

    # 3️⃣ Validação
    if "bank3_contacorrente" not in data:
        print("⚠️ Nenhum arquivo do Banco 3 reconhecido.")
        return

    df = data["bank3_contacorrente"]

    if df.empty:
        print("⚠️ DataFrame vazio.")
        return

    # 4️⃣ Persistência
    inserted = persist_dataframe_as_payload(
        engine=engine,
        schema="raw",
        table="bank3",
        dataframe=df
    )

    print(f"✅ {inserted} registros inseridos na raw.bank3.")
