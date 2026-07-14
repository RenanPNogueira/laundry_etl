"""
Módulo: database_prerequisites.py

Responsabilidade
----------------
Garantir pré-requisitos de banco específicos do ETL da lavanderia.
"""

from sqlalchemy.engine import Engine

from lavesecexpress_etl.core.database.create_extension import create_extension_if_not_exists


def ensure_database_prerequisites(engine: Engine) -> None:
    """
    Garante as extensões e pré-requisitos necessários para o ETL
    da lavanderia.
    """

    create_extension_if_not_exists(engine, "unaccent")