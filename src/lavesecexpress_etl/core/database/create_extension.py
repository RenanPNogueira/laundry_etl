"""
Módulo: create_extension.py

Responsabilidade
----------------
Fornecer função utilitária para criação/verificação de extensões PostgreSQL.

Contexto
--------
Este módulo faz parte do core do lavesecexpress_etl e contém lógica genérica
de administração de banco. Ele não deve conhecer regras específicas de fontes
ou pipelines do projeto.
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine


def create_extension_if_not_exists(
    engine: Engine,
    extension_name: str,
) -> None:
    """
    Cria uma extensão PostgreSQL caso ela ainda não exista.

    Parameters
    ----------
    engine : Engine
        SQLAlchemy Engine conectado ao banco PostgreSQL alvo.

    extension_name : str
        Nome da extensão que deve ser criada/verificada.

    Returns
    -------
    None
    """

    if not extension_name:
        raise ValueError("O nome da extensão não foi informado.")

    safe_extension_name = extension_name.replace('"', '""')

    with engine.begin() as conn:
        conn.execute(
            text(f'CREATE EXTENSION IF NOT EXISTS "{safe_extension_name}";')
        )

    print(f"🟢 Extensão '{extension_name}' verificada/criada com sucesso.")
