"""
Módulo: connection.py

Responsabilidade
----------------
Centralizar funções de conexão com PostgreSQL.

Este módulo fornece duas formas de conexão:

- get_engine:
    Cria um SQLAlchemy Engine, indicado para operações comuns de ETL,
    leitura, escrita e integração com pandas.

- get_psycopg_connection:
    Cria uma conexão direta via psycopg2, indicada para operações
    administrativas, como criação de banco de dados.
"""

import psycopg2
from psycopg2.extensions import connection as PsycopgConnection
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL


def get_engine(
    host: str,
    port: int,
    user: str,
    password: str,
    db_name: str,
    pool_size: int = 5,
    max_overflow: int = 10,
) -> Engine:
    """
    Cria e retorna um SQLAlchemy Engine configurado para PostgreSQL.

    Parameters
    ----------
    host : str
        Endereço do servidor PostgreSQL.

    port : int
        Porta utilizada pelo PostgreSQL.

    user : str
        Usuário de autenticação no banco.

    password : str
        Senha do usuário.

    db_name : str
        Nome do banco de dados.

    pool_size : int, default=5
        Quantidade de conexões persistentes mantidas no pool.

    max_overflow : int, default=10
        Quantidade máxima de conexões extras permitidas além do pool.

    Returns
    -------
    Engine
        Engine SQLAlchemy pronta para uso.
    """

    connection_url = URL.create(
        drivername="postgresql+psycopg2",
        username=user,
        password=password,
        host=host,
        port=port,
        database=db_name,
    )

    engine = create_engine(
        connection_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,
        future=True,
    )

    return engine


def get_psycopg_connection(
    host: str,
    port: int,
    user: str,
    password: str,
    db_name: str,
) -> PsycopgConnection:
    """
    Cria e retorna uma conexão direta com PostgreSQL usando psycopg2.

    Esta função deve ser usada em operações onde uma conexão bruta com
    PostgreSQL é mais adequada do que um SQLAlchemy Engine, como criação de
    bancos de dados, execução de comandos administrativos ou uso direto de
    cursores.

    Parameters
    ----------
    host : str
        Endereço do servidor PostgreSQL.

    port : int
        Porta utilizada pelo PostgreSQL.

    user : str
        Usuário de autenticação no banco.

    password : str
        Senha do usuário.

    db_name : str
        Nome do banco de dados para conexão.

    Returns
    -------
    PsycopgConnection
        Conexão ativa com o PostgreSQL.
    """

    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=db_name,
    )

    return conn