"""
Módulo: create_database.py

Responsabilidade
----------------
Fornecer uma função utilitária para criação de bancos PostgreSQL, com
verificação prévia de existência.

Contexto
--------
Este módulo faz parte do módulo `core` do pacote `lavesecexpress_etl`, uma biblioteca reutilizável
para engenharia de dados. Ele deve conter apenas lógica genérica de
administração de banco, sem depender de regras específicas de qualquer projeto.

Principais componentes
----------------------
- create_database_if_not_exists: verifica se um banco PostgreSQL existe e,
  caso não exista, cria o banco informado.

Observações
-----------
A função se conecta inicialmente ao banco administrativo `postgres`, pois
o PostgreSQL não permite criar um banco enquanto a conexão está apontada para
o próprio banco que ainda será criado.
"""

from psycopg2 import sql
from psycopg2 import OperationalError, Error

from lavesecexpress_etl.core.database.connection import get_psycopg_connection


def create_database_if_not_exists(
    host: str,
    port: int,
    user: str,
    password: str,
    db_name: str,
) -> bool:
    """
    Cria um banco PostgreSQL caso ele ainda não exista.

    A função realiza uma consulta no catálogo interno `pg_database` para
    verificar se o banco informado já existe. Se o banco não existir, executa
    o comando `CREATE DATABASE`.

    Parameters
    ----------
    host : str
        Endereço do servidor PostgreSQL.

    port : int
        Porta utilizada pelo PostgreSQL.

    user : str
        Usuário com permissão para consultar o catálogo e criar bancos.

    password : str
        Senha do usuário informado.

    db_name : str
        Nome do banco de dados que deve ser verificado/criado.

    Returns
    -------
    bool
        Retorna True quando o banco é criado.
        Retorna False quando o banco já existia.

    Raises
    ------
    ValueError
        Quando o nome do banco não é informado.

    ConnectionError
        Quando não for possível estabelecer conexão com o PostgreSQL.

    RuntimeError
        Quando ocorre erro ao consultar ou criar o banco.

    Notes
    -----
    - A conexão é feita no banco administrativo `postgres`.
    - O nome do banco é aplicado ao comando CREATE DATABASE usando
      `psycopg2.sql.Identifier`, evitando SQL dinâmico inseguro.
    - A conexão é configurada com `autocommit=True`, pois comandos como
      CREATE DATABASE não podem ser executados dentro de uma transação comum.
    """

    if not db_name:
        raise ValueError("O nome do banco de dados não foi informado.")

    conn = None
    cur = None

    try:
        conn = get_psycopg_connection(
            host=host,
            port=port,
            user=user,
            password=password,
            db_name="postgres",
        )

        if not conn:
            raise ConnectionError("Não foi possível conectar ao PostgreSQL.")

        conn.autocommit = True
        cur = conn.cursor()

        cur.execute(
            """
            SELECT 1
            FROM pg_database
            WHERE datname = %s;
            """,
            (db_name,),
        )

        database_exists = cur.fetchone() is not None

        if database_exists:
            print(f"⚠️ Banco '{db_name}' já existe.")
            return False

        cur.execute(
            sql.SQL("CREATE DATABASE {}").format(
                sql.Identifier(db_name),
            )
        )

        print(f"🟢 Banco '{db_name}' criado com sucesso.")
        return True

    except OperationalError as error:
        raise ConnectionError(
            "Erro ao conectar no banco administrativo 'postgres'. "
            "Verifique host, porta, usuário e senha."
        ) from error

    except Error as error:
        raise RuntimeError(
            f"Erro ao verificar ou criar o banco '{db_name}'."
        ) from error

    finally:
        if cur:
            cur.close()

        if conn:
            conn.close()