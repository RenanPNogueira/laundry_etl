"""
Módulo: create_table.py

Responsabilidade
----------------
Fornecer uma função utilitária para execução de comandos DDL relacionados
à criação de tabelas em bancos acessados via SQLAlchemy.

Contexto
--------
Este módulo faz parte do módulo `core` do pacote `lavesecexpress_etl`, uma biblioteca reutilizável
para engenharia de dados. Ele deve conter apenas lógica genérica de execução
de DDL, sem depender de regras específicas de qualquer projeto.

Principais componentes
----------------------
- create_table_from_ddl: executa uma instrução DDL recebida como string,
  normalmente utilizada para criação ou verificação de tabelas.

Observações
-----------
Este módulo não define a estrutura das tabelas. A responsabilidade de montar
o DDL pertence ao projeto consumidor, como um pipeline específico ou script
de inicialização de banco.
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine


def create_table_from_ddl(
    engine: Engine,
    ddl_sql: str,
) -> None:
    """
    Executa um comando DDL para criação ou manutenção de tabela.

    A função recebe um SQLAlchemy Engine e uma string contendo uma instrução
    DDL. Em geral, essa instrução será um `CREATE TABLE IF NOT EXISTS`,
    mas a função pode executar qualquer comando DDL compatível com o banco
    conectado.

    Parameters
    ----------
    engine : Engine
        SQLAlchemy Engine conectado ao banco onde o DDL será executado.

    ddl_sql : str
        String contendo o comando DDL a ser executado. Normalmente será uma
        instrução `CREATE TABLE IF NOT EXISTS`.

    Returns
    -------
    None
        A função não retorna valor. Apenas executa o comando informado.

    Raises
    ------
    SQLAlchemyError
        Caso o DDL seja inválido ou ocorra erro durante a execução no banco.

    Notes
    -----
    - O DDL deve ser definido por código confiável do projeto.
    - Esta função não valida semanticamente o conteúdo do SQL recebido.
    - A execução ocorre dentro de `engine.begin()`, garantindo controle
      transacional pelo SQLAlchemy quando aplicável.
    """

    if not ddl_sql or not ddl_sql.strip():
        raise ValueError("O parâmetro 'ddl_sql' não pode estar vazio.")

    with engine.begin() as conn:
        conn.execute(text(ddl_sql))

    print("🟢 DDL de tabela executado com sucesso.")