"""
Módulo: laundry_system_pipeline.py

Responsabilidade
----------------
Executar o pipeline de extração e carga RAW da integração com o sistema da
lavanderia.

Contexto
--------
Este módulo faz parte da camada de pipelines do pacote lavesecexpress_etl.
Ele coordena a definição das janelas de timestamp, a extração dos dados da
API do sistema da lavanderia e a persistência das entidades extraídas na
tabela raw.laundry_system.

Fluxo executado
---------------
1. Define os timestamps de extração usando api_timestamp.py.
2. Executa a extração usando sources.laundry_system.runner.
3. Converte cada entidade retornada em DataFrame.
4. Persiste os dados em raw.laundry_system usando payload JSONB.
5. Diferencia cada entidade pelo campo basename.

Entidades carregadas
--------------------
- vendas
- maquinas
- lavanderias
- clientes

Observações
-----------
Este pipeline não transforma dados para Silver e não carrega a camada Gold.
Ele atua apenas na etapa de ingestão RAW do sistema da lavanderia.
"""

import pandas as pd

from lavesecexpress_etl.config.settings import LAUNDRY_SYSTEM_CONFIG
from lavesecexpress_etl.sources.laundry_system.api_timestamp import set_extraction_timestamps
from lavesecexpress_etl.sources.laundry_system.runner import run_laundry_system_extraction

from lavesecexpress_etl.core.database.persistence import persist_dataframe_as_payload

def run_laundry_system_pipeline(engine, mode="incremental"):
    """
    Executa o pipeline de extração e carga RAW do sistema da lavanderia.

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
        A função não retorna valor. Ela executa a extração e persiste os dados
        brutos na tabela raw.laundry_system.

    Notes
    -----
    - As credenciais do sistema da lavanderia são lidas de LAUNDRY_SYSTEM_CONFIG.
    - Todas as entidades são gravadas na tabela raw.laundry_system.
    - O campo basename diferencia vendas, máquinas, lavanderias e clientes.
    - A persistência usa payload JSONB e hashid via lavesecexpress_etl.core.
    """

    print(f"\n========== LAUNDRY SYSTEM PIPELINE START | MODE: {mode.upper()} ==========")
    # ----- 1 - DEFINE TIMESTAMP
    timestamps = set_extraction_timestamps(mode, engine)

    # ----- 2 - RUNNER (EXTRACT)
    laundry_result = run_laundry_system_extraction(
        datas=timestamps,
        api_key=LAUNDRY_SYSTEM_CONFIG["api_key"],
        cnpj=LAUNDRY_SYSTEM_CONFIG["cnpj"],
    )


    if laundry_result.get("status") != "success":
        print("[LAUNDRY SYSTEM] Nenhum dado retornado.")
        print("========== LAUNDRY SYSTEM EXTRACTION END ==========\n")
        return

    print("[LAUNDRY SYSTEM] Extração concluída.")
    print("[LAUNDRY SYSTEM] Metadata:", laundry_result.get("metadata"))

    # ----- 3 - LOAD (RAW)
    entities = ["vendas", "maquinas", "lavanderias", "clientes"]
    for entity in entities:

        data = laundry_result.get(entity)
        if not data:
            print(f"[LAUNDRY SYSTEM] Nenhum dado para entidade: {entity}")
            continue

        df = pd.DataFrame(data)

        inserted = persist_dataframe_as_payload(
            engine=engine,
            schema="raw",
            table="laundry_system",
            dataframe=df,
            basename=entity
        )

        print(f"[LAUNDRY SYSTEM] {inserted} registros inseridos na raw.laundry_system ({entity}).")

    print("========== LAUNDRY SYSTEM PIPELINE END ==========\n")
