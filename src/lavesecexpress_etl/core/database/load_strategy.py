"""
Módulo: load_strategy.py

Responsabilidade
----------------
Definir a estratégia de carga do pipeline com base no estado do schema raw.

Contexto
--------
Este módulo faz parte do módulo `core` do pacote `lavesecexpress_etl` e fornece funções utilitárias
para diagnosticar se o ambiente já possui estrutura e dados suficientes para
executar uma carga incremental.

Regra arquitetural
------------------
O schema raw é a referência oficial para definição do modo de carga.

- Se o schema raw não existir, o pipeline deve rodar em modo foundation.
- Se o schema raw existir, mas não possuir tabelas, o pipeline deve rodar em modo foundation.
- Se alguma tabela do schema raw estiver vazia, o pipeline deve rodar em modo foundation.
- Se todas as tabelas existentes no schema raw possuírem dados, o pipeline pode rodar em modo incremental.

Principais componentes
----------------------
- get_raw_schema_status: retorna diagnóstico completo do schema raw.
- is_incremental_load: retorna True/False para carga incremental.
- get_pipeline_mode: retorna "incremental" ou "foundation".
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine


# O schema raw é usado como referência oficial para definir
# se o pipeline deve rodar em modo foundation ou incremental.
RAW_SCHEMA = "raw"


def get_raw_schema_status(engine: Engine) -> dict:
    """
    Retorna o diagnóstico completo do estado do schema raw.

    A função verifica se o schema raw existe, lista suas tabelas e identifica
    quantas dessas tabelas possuem ao menos uma linha de dados.

    Parameters
    ----------
    engine : Engine
        SQLAlchemy Engine conectado ao banco PostgreSQL.

    Returns
    -------
    dict
        Dicionário com o diagnóstico do schema raw, contendo:
        - schema_exists: indica se o schema raw existe.
        - tables: lista de tabelas encontradas no schema raw.
        - tables_with_data: quantidade de tabelas com pelo menos uma linha.
        - total_tables: quantidade total de tabelas encontradas.
        - incremental: indica se o ambiente está apto para carga incremental.

    Notes
    -----
    A regra atual considera carga incremental somente quando:
    - o schema raw existe;
    - existe pelo menos uma tabela no schema raw;
    - todas as tabelas existentes no schema raw possuem dados.
    """

    with engine.connect() as conn:
        schema_exists = conn.execute(
            text("""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.schemata
                    WHERE schema_name = :schema
                )
            """),
            {"schema": RAW_SCHEMA},
        ).scalar()

        if not schema_exists:
            return {
                "schema_exists": False,
                "tables": [],
                "tables_with_data": 0,
                "total_tables": 0,
                "incremental": False,
            }

        tables = conn.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = :schema
                  AND table_type = 'BASE TABLE'
            """),
            {"schema": RAW_SCHEMA},
        ).fetchall()

        total_tables = len(tables)
        tables_with_data = 0

        for (table_name,) in tables:
            has_data = conn.execute(
                text(f"""
                    SELECT EXISTS (
                        SELECT 1
                        FROM {RAW_SCHEMA}.{table_name}
                        LIMIT 1
                    )
                """)
            ).scalar()

            if has_data:
                tables_with_data += 1

        incremental = (
            schema_exists
            and total_tables > 0
            and tables_with_data == total_tables
        )

        return {
            "schema_exists": schema_exists,
            "tables": [table[0] for table in tables],
            "tables_with_data": tables_with_data,
            "total_tables": total_tables,
            "incremental": incremental,
        }


def is_incremental_load(engine: Engine) -> bool:
    """
    Indica se o pipeline deve executar em modo incremental.

    Parameters
    ----------
    engine : Engine
        SQLAlchemy Engine conectado ao banco PostgreSQL.

    Returns
    -------
    bool
        True se o schema raw estiver apto para carga incremental.
        False caso contrário.
    """

    status = get_raw_schema_status(engine)
    return status["incremental"]


def get_pipeline_mode(engine: Engine) -> str:
    """
    Retorna o modo de execução recomendado para o pipeline.

    Parameters
    ----------
    engine : Engine
        SQLAlchemy Engine conectado ao banco PostgreSQL.

    Returns
    -------
    str
        "incremental" quando o schema raw está apto para carga incremental.
        "foundation" quando o ambiente ainda exige carga inicial.
    """

    return "incremental" if is_incremental_load(engine) else "foundation"