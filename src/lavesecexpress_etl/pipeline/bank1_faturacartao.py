"""
Módulo: bank1_faturacartao.py

Responsabilidade
----------------
Executar o pipeline de leitura de PDFs de fatura de cartão do Banco 1 e carga
RAW na tabela raw.bank1_cartao.

Contexto
--------
Este módulo faz parte da camada de pipelines do pacote lavesecexpress_etl.
Diferente do pipeline de conta corrente do Banco 1, este fluxo não usa
Selenium nem janelas de datas. A entrada é uma pasta local contendo PDFs de
faturas.

Fluxo executado
---------------
1. Lê a pasta de PDFs configurada em BANK1_CONFIG["pasta_faturas"].
2. Valida se a configuração e o caminho existem.
3. Se não houver PDFs, encerra este pipeline sem erro e preserva a RAW atual.
4. Processa os PDFs usando sources.bank1.cartoes.pdf_reader.processar_pasta.
5. Valida se o DataFrame extraído possui dados.
6. Persiste os dados em raw.bank1_cartao usando payload JSONB.

Observações
-----------
O parâmetro mode é recebido para manter compatibilidade com a assinatura dos
demais pipelines, mas não controla o período de extração deste fluxo.
"""

import os

from lavesecexpress_etl.core.database.persistence import persist_dataframe_as_payload
from lavesecexpress_etl.sources.bank1.cartoes.pdf_reader import processar_pasta
from lavesecexpress_etl.config.settings import BANK1_CONFIG


def run_bank1_faturas_pipeline(engine, mode="incremental"):
    """
    Executa o pipeline de ingestão RAW das faturas de cartão do Banco 1.

    Parameters
    ----------
    engine
        SQLAlchemy Engine conectado ao banco PostgreSQL.

    mode : str, default="incremental"
        Parâmetro mantido por compatibilidade com outros pipelines. Neste fluxo,
        não é usado para cálculo de datas.

    Returns
    -------
    None
        A função não retorna valor. Ela processa PDFs e persiste os registros em
        raw.bank1_cartao.

    Raises
    ------
    Exception
        Quando a pasta de faturas não está configurada, quando o caminho não
        existe ou quando há PDFs, mas nenhum dado pode ser extraído deles.

    Notes
    -----
    - A entrada é uma pasta local de PDFs.
    - Uma pasta existente sem PDFs é tratada como ausência de nova carga.
    - A extração dos PDFs é delegada ao pdf_reader.py.
    - A persistência usa payload JSONB e hashid via lavesecexpress_etl.core.
    """

    print(f"\n========== BANK1 FATURAS PIPELINE START | MODE: {mode.upper()} ==========")

    # -----------------------------------
    # CAMINHO FIXO (não depende de mode)
    pasta_pdf = BANK1_CONFIG.get("pasta_faturas")

    if not pasta_pdf:
        raise Exception("[BANK1 FATURAS] pasta_faturas não configurado")

    if not os.path.exists(pasta_pdf):
        raise Exception(f"[BANK1 FATURAS] Caminho não existe: {pasta_pdf}")

    arquivos_pdf = [
        entrada
        for entrada in os.scandir(pasta_pdf)
        if entrada.is_file() and entrada.name.lower().endswith(".pdf")
    ]

    if not arquivos_pdf:
        print(
            "[BANK1 FATURAS] Nenhum PDF encontrado. "
            "Pipeline ignorado; dados já existentes na RAW foram preservados."
        )
        print("========== BANK1 FATURAS PIPELINE END (SKIPPED) ==========\n")
        return {"status": "skipped", "detail": "sem arquivo novo"}

    # -----------------------------------
    # TRANSFORM
    df = processar_pasta(pasta_pdf)

    if df.empty:
        raise Exception("[BANK1 FATURAS] Nenhum dado extraído dos PDFs.")

    # -----------------------------------
    # LOAD
    inserted = persist_dataframe_as_payload(
        engine=engine,
        schema="raw",
        table="bank1_cartao",
        dataframe=df
    )

    print(f"[BANK1 FATURAS] {inserted} registros inseridos.")

    print("========== BANK1 FATURAS PIPELINE END ==========\n")
