"""
Módulo: bank1_contacorrente.py

Responsabilidade
----------------
Executar o pipeline de extração e carga RAW do extrato de conta corrente do
Banco 1.

Contexto
--------
Este módulo faz parte da camada de pipelines do pacote lavesecexpress_etl.
Ele coordena a definição de datas, extração via Selenium, leitura do arquivo
baixado e persistência dos dados brutos na tabela raw.bank1.

Fluxo executado
---------------
1. Define as janelas de datas usando shared.selenium_dates.
2. Executa a extração Selenium com sources.bank1.contacorrente.runner.
3. Lê os arquivos baixados na pasta temporária usando transformation_flow.run.
4. Persiste o DataFrame em raw.bank1 usando payload JSONB.
5. Limpa a pasta temporária após a carga.

Observações
-----------
Este pipeline não transforma dados para Silver e não carrega a camada Gold.
Ele atua apenas na ingestão RAW do extrato de conta corrente do Banco 1.
"""

import os
import pandas as pd

from lavesecexpress_etl.core.database.persistence import persist_dataframe_as_payload
from lavesecexpress_etl.core.transformation.transformation_flow import run
from lavesecexpress_etl.core.transformation.delete_folder_files import delete_folder_files


from lavesecexpress_etl.config.settings import BANK1_CONFIG, temp_folder
from lavesecexpress_etl.shared.selenium_dates import set_extraction_dates
from lavesecexpress_etl.sources.bank1.contacorrente.runner import run_bank1_extraction



def run_bank1_pipeline(engine, mode="incremental"):
    """
    Executa o pipeline de extração e carga RAW da conta corrente do Banco 1.

    Parameters
    ----------
    engine
        SQLAlchemy Engine conectado ao banco PostgreSQL.

    mode : str, default="incremental"
        Modo de execução da extração. Valores esperados:
        - "incremental";
        - "foundation".

    Returns
    -------
    None
        A função não retorna valor. Ela executa a extração, leitura do arquivo
        e persistência dos dados brutos em raw.bank1.

    Notes
    -----
    - As credenciais e pasta de download vêm de BANK1_CONFIG.
    - As datas vêm de set_extraction_dates.
    - O arquivo baixado é lido a partir de temp_folder.
    - A persistência usa payload JSONB e hashid via lavesecexpress_etl.core.
    - A pasta temporária é limpa ao final da carga.
    """

    print(f"\n========== BANK1 PIPELINE START | MODE: {mode.upper()} ==========")

    # -----------------------------------
    # 1 - DEFINE DATAS
    datas = set_extraction_dates(mode, engine)
    datas_bank1 = datas["bank1"]

    # -----------------------------------
    # 2 - EXTRACT (SELENIUM)
    run_bank1_extraction(
        usuario=BANK1_CONFIG["usuario"],
        senha=BANK1_CONFIG["senha"],
        datas=datas_bank1,
        pasta_downloads=BANK1_CONFIG["pasta_downloads"],
        pasta_destino=temp_folder,
        login_url=BANK1_CONFIG["login_url"],
    )

    print("[BANK1] Extração concluída.")

    # -----------------------------------
    # 3 - LEITURA
    data = run(
       temp_folder,
       lambda _: "bank1_contacorrente"
    )

    df = data["bank1_contacorrente"]

    # -----------------------------------
    # 5 - LOAD (RAW)
    inserted = persist_dataframe_as_payload(
        engine=engine,
        schema="raw",
        table="bank1",
        dataframe=df
    )
    delete_folder_files(temp_folder)

    print(f"[BANK1] {inserted} registros inseridos na raw.bank1.")
    print("========== BANK1 PIPELINE END ==========\n")
