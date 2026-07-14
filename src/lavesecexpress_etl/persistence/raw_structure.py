"""
Módulo: raw_structure.py

Responsabilidade
----------------
Garantir a existência do schema raw e das tabelas brutas necessárias para os
pipelines do ETL da lavanderia.

Contexto
--------
Este módulo faz parte da camada de persistência do lavesecexpress_etl. Ele
define os DDLs das tabelas RAW usadas pelas integrações do projeto e executa
a criação dessas estruturas quando necessário.

Estratégia RAW
--------------
As tabelas da camada raw armazenam os dados extraídos em formato semiestruturado
na coluna payload JSONB. Cada registro recebe um hashid para controle de
duplicidade.

Tabelas criadas
---------------
- raw.laundry_system
- raw.bank2
- raw.bank1
- raw.bank1_cartao
- raw.bank3

Principais componentes
----------------------
- ensure_raw_structure:
    cria o schema raw, caso não exista, e executa os DDLs de criação das
    tabelas RAW do projeto.

Observações
-----------
Este módulo não realiza ingestão, transformação ou carga de dados. Ele apenas
prepara a estrutura física da camada RAW no PostgreSQL.
"""

from sqlalchemy.engine import Engine
from lavesecexpress_etl.core.database.create_schema import create_schema_if_not_exists
from lavesecexpress_etl.core.database.create_table import create_table_from_ddl


RAW_SCHEMA = "raw"


RAW_LAUNDRY_SYSTEM_DDL = """
CREATE TABLE IF NOT EXISTS raw.laundry_system (
    id BIGSERIAL PRIMARY KEY,
    basename VARCHAR(50) NOT NULL,
    timestampextraction TIMESTAMP NOT NULL,
    payload JSONB NOT NULL,
    hashid VARCHAR(64) NOT NULL,
    CONSTRAINT uq_laundry_system_basename_hash UNIQUE (basename, hashid)
);
"""


RAW_BANK2_DDL = """
CREATE TABLE IF NOT EXISTS raw.bank2 (
    id BIGSERIAL PRIMARY KEY,
    timestampextraction TIMESTAMP NOT NULL,
    payload JSONB NOT NULL,
    hashid VARCHAR(64) NOT NULL,
    CONSTRAINT uq_bank2_hash UNIQUE (hashid)
);
"""


RAW_BANK1_DDL = """
CREATE TABLE IF NOT EXISTS raw.bank1 (
    id BIGSERIAL PRIMARY KEY,
    timestampextraction TIMESTAMP NOT NULL,
    payload JSONB NOT NULL,
    hashid VARCHAR(64) NOT NULL,
    CONSTRAINT uq_bank1_hash UNIQUE (hashid)
);
"""


RAW_BANK1_CARTAO_DDL = """
CREATE TABLE IF NOT EXISTS raw.bank1_cartao (
    id BIGSERIAL PRIMARY KEY,
    timestampextraction TIMESTAMP NOT NULL,
    payload JSONB NOT NULL,
    hashid VARCHAR(64) NOT NULL,
    CONSTRAINT uq_bank1_cartao_hash UNIQUE (hashid)
);
"""


RAW_BANK3_DDL = """
CREATE TABLE IF NOT EXISTS raw.bank3 (
    id BIGSERIAL PRIMARY KEY,
    timestampextraction TIMESTAMP NOT NULL,
    payload JSONB NOT NULL,
    hashid VARCHAR(64) NOT NULL,
    CONSTRAINT uq_bank3_hash UNIQUE (hashid)
);
"""


def ensure_raw_structure(engine: Engine) -> None:
    """
    Garante a existência do schema raw e das tabelas RAW do projeto.

    A função cria o schema raw, caso ele ainda não exista, e executa os DDLs
    de criação das tabelas brutas necessárias para as fontes integradas ao
    ETL da lavanderia.

    Parameters
    ----------
    engine : Engine
        SQLAlchemy Engine conectado ao banco PostgreSQL.

    Returns
    -------
    None
        A função não retorna valor. Apenas executa comandos DDL no banco.

    Notes
    -----
    - As tabelas são criadas com CREATE TABLE IF NOT EXISTS.
    - A tabela raw.laundry_system usa constraint única em (basename, hashid).
    - As demais tabelas usam constraint única em hashid.
    - A função não executa migrações em tabelas já existentes.
    """

    create_schema_if_not_exists(engine, RAW_SCHEMA)

    create_table_from_ddl(engine, RAW_LAUNDRY_SYSTEM_DDL)
    create_table_from_ddl(engine, RAW_BANK2_DDL)
    create_table_from_ddl(engine, RAW_BANK1_DDL)
    create_table_from_ddl(engine, RAW_BANK1_CARTAO_DDL)
    create_table_from_ddl(engine, RAW_BANK3_DDL)
