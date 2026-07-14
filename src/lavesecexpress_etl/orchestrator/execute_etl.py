"""
Módulo: execute_etl.py

Responsabilidade
----------------
Executar o orquestrador principal do ETL da lavanderia.

Contexto
--------
Este módulo é o ponto de entrada principal do projeto. Ele coordena a execução
dos pipelines de ingestão RAW e, ao final, dispara o pipeline de transformação
das camadas Silver, Rules e Gold.
"""

from lavesecexpress_etl.core.database.connection import get_engine
from lavesecexpress_etl.core.database.load_strategy import get_pipeline_mode, get_raw_schema_status
from lavesecexpress_etl.core.database.create_database import create_database_if_not_exists
from lavesecexpress_etl.persistence.raw_structure import ensure_raw_structure
from lavesecexpress_etl.persistence.database_prerequisites import ensure_database_prerequisites

from lavesecexpress_etl.config.settings import DB_CONFIG, validate_settings

from lavesecexpress_etl.pipeline.laundry_system_pipeline import run_laundry_system_pipeline
from lavesecexpress_etl.pipeline.bank1_contacorrente import run_bank1_pipeline
from lavesecexpress_etl.pipeline.bank2_recebimentos import run_bank2_pipeline
from lavesecexpress_etl.pipeline.bank1_faturacartao import run_bank1_faturas_pipeline
from lavesecexpress_etl.pipeline.bank3_contacorrente import run_bank3_pipeline
from lavesecexpress_etl.pipeline.data_transformation import run_pipeline


def run_orchestrator(mode=None, pipelines_to_run=None):
    """
    Executa o orquestrador principal do ETL.

    Parameters
    ----------
    mode : str | None, default=None
        Modo de execução repassado aos pipelines RAW.

        Valores aceitos:
        - "incremental";
        - "foundation";
        - None.

        Quando None, o modo é definido automaticamente com base no estado
        do schema raw, usando get_pipeline_mode(engine).

    pipelines_to_run : list[str] | None, default=None
        Lista opcional com os nomes dos pipelines RAW que devem ser executados.
        Quando None, todos os pipelines registrados em all_pipelines são
        executados.

    Returns
    -------
    None
    """

    print("\n========== ORQUESTRADOR START ==========")

    # ============================================================
    # VALIDAÇÃO DE CONFIGURAÇÃO (.env / variáveis de ambiente)
    # ============================================================
    print("\nValidando variáveis de ambiente obrigatórias...")
    validate_settings()

    # ============================================================
    # CONEXÃO CENTRALIZADA COM O BANCO
    # ============================================================
    print("\nValidando existência do database alvo...")
    create_database_if_not_exists(**DB_CONFIG)

    engine = get_engine(**DB_CONFIG)

    print("\nValidando pré-requisitos do database...")
    ensure_database_prerequisites(engine)

    print("\nValidando estrutura RAW...")
    ensure_raw_structure(engine)

    # ============================================================
    # DEFINIÇÃO AUTOMÁTICA DO MODO DE EXECUÇÃO
    # ============================================================
    if mode is None:
        status_raw = get_raw_schema_status(engine)
        mode = get_pipeline_mode(engine)

        print("\nDiagnóstico do schema RAW:")
        print(f"Schema existe? {status_raw['schema_exists']}")
        print(f"Tabelas encontradas: {status_raw['tables']}")
        print(f"Total de tabelas: {status_raw['total_tables']}")
        print(f"Tabelas com dados: {status_raw['tables_with_data']}")
        print(f"Modo recomendado: {mode.upper()}")

    else:
        print(f"\nModo informado manualmente: {mode.upper()}")

    if mode not in ["incremental", "foundation"]:
        raise ValueError(
            "Modo de execução inválido. "
            "Use 'incremental', 'foundation' ou None para modo automático."
        )

    # ============================================================
    # REGISTRO DOS PIPELINES RAW DISPONÍVEIS
    # ============================================================
    all_pipelines = {
        "laundry_system": run_laundry_system_pipeline,
        "bank1_contacorrente": run_bank1_pipeline,
        "bank2": run_bank2_pipeline,
        "bank1_faturacartao": run_bank1_faturas_pipeline,
        "bank3_contacorrente": run_bank3_pipeline,
    }

    if pipelines_to_run is None:
        pipelines_to_run = list(all_pipelines.keys())

    print("\nPipelines selecionados:")
    for nome in pipelines_to_run:
        print(f"- {nome}")

    # ============================================================
    # EXECUÇÃO DOS PIPELINES RAW
    # ============================================================
    for nome in pipelines_to_run:

        if nome not in all_pipelines:
            raise ValueError(f"Pipeline '{nome}' não existe.")

        print(f"\n🚀 Executando pipeline: {nome.upper()}")
        print(f"Modo: {mode.upper()}")

        # FAIL FAST:
        # Se qualquer pipeline lançar erro, a execução para imediatamente.
        all_pipelines[nome](engine, mode)

        print(f"✅ Pipeline {nome.upper()} finalizado")

    print("\n========== ORQUESTRADOR RAW END ==========\n")

    # ============================================================
    # TRANSFORMAÇÃO PÓS-RAW
    # Silver → Rules → Gold
    # ============================================================
    print("\n========== TRANSFORMATION START ==========")

    run_pipeline()

    print("\n========== TRANSFORMATION END ==========")
    print("\n========== ORQUESTRADOR END ==========\n")


if __name__ == "__main__":
    run_orchestrator()