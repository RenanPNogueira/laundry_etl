"""
Módulo: create_schema.py

Responsabilidade
----------------
Fornecer uma função utilitária para criação de schemas PostgreSQL usando
um SQLAlchemy Engine.

Contexto
--------
Este módulo faz parte do módulo `core` do pacote `lavesecexpress_etl`, uma biblioteca reutilizável
para engenharia de dados. Ele deve conter apenas lógica genérica de
administração de banco, sem depender de regras específicas de qualquer projeto.

Principais componentes
----------------------
- create_schema_if_not_exists: verifica/cria um schema PostgreSQL usando
  um Engine SQLAlchemy já existente.

Observações
-----------
Este módulo é útil para preparação automatizada de ambientes antes da execução
de pipelines ETL, especialmente quando o projeto utiliza separação por schemas
como raw, staging, prd, analytics ou datawarehouse.
"""

from sqlalchemy.engine import Engine
from sqlalchemy.schema import CreateSchema


def create_schema_if_not_exists(
    engine: Engine,
    schema_name: str,
) -> None:
    """
    Cria um schema PostgreSQL caso ele ainda não exista.

    A função recebe um SQLAlchemy Engine já configurado e executa o comando
    de criação de schema utilizando o construtor `CreateSchema` do SQLAlchemy.

    Parameters
    ----------
    engine : Engine
        SQLAlchemy Engine conectado ao banco PostgreSQL onde o schema deve ser
        verificado/criado.

    schema_name : str
        Nome do schema que deve ser criado caso ainda não exista.

    Returns
    -------
    None
        A função não retorna valor. Apenas executa a criação/verificação do
        schema no banco.

    Notes
    -----
    - Usa `CreateSchema` em vez de montar SQL manualmente com f-string.
    - O parâmetro `if_not_exists=True` evita erro caso o schema já exista.
    - A execução ocorre dentro de `engine.begin()`, garantindo controle
      transacional pelo SQLAlchemy.
    """

    with engine.begin() as conn:
        conn.execute(
            CreateSchema(
                name=schema_name,
                if_not_exists=True,
            )
        )

    print(f"🟢 Schema '{schema_name}' verificado/criado com sucesso.")