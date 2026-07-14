"""
Módulo: persistence.py

Responsabilidade
----------------
Fornecer funções utilitárias para persistência de DataFrames em tabelas
PostgreSQL usando uma estratégia de payload JSONB.

Contexto
--------
Este módulo faz parte do módulo `core` do pacote `lavesecexpress_etl`, uma biblioteca reutilizável
para engenharia de dados. Ele é especialmente útil para camadas raw, onde
cada registro extraído deve ser preservado em formato semiestruturado antes
de passar por transformações de negócio.

Estratégia de persistência
--------------------------
Cada linha do DataFrame é convertida em um objeto JSON e armazenada na coluna
`payload`. Para controle de duplicidade, é gerado um hash SHA256 a partir do
conteúdo normalizado de cada registro.

Principais componentes
----------------------
- _generate_hash: gera um hash SHA256 a partir de um dicionário.
- persist_dataframe_as_payload: persiste um DataFrame em uma tabela com
  colunas de metadados e payload JSONB.

Premissas da tabela de destino
------------------------------
Quando `basename` é informado, a tabela de destino deve possuir as colunas:
- basename
- timestampextraction
- payload
- hashid

Quando `basename` não é informado, a tabela de destino deve possuir as colunas:
- timestampextraction
- payload
- hashid
"""

import hashlib
import json
import math
import re
from datetime import datetime
from typing import Optional

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


def _validate_identifier(identifier: str, identifier_name: str) -> None:
    """
    Valida nomes de schema e tabela antes de usá-los em SQL dinâmico.

    A função aceita apenas letras, números e underscore, exigindo que o
    identificador comece por letra ou underscore.

    Parameters
    ----------
    identifier : str
        Valor do identificador a ser validado.

    identifier_name : str
        Nome descritivo do identificador, usado na mensagem de erro.

    Raises
    ------
    ValueError
        Quando o identificador é vazio ou possui caracteres inválidos.
    """

    pattern = r"^[A-Za-z_][A-Za-z0-9_]*$"

    if not identifier or not re.match(pattern, identifier):
        raise ValueError(
            f"O identificador '{identifier_name}' possui valor inválido: {identifier!r}."
        )


def _generate_hash(record: dict) -> str:
    """
    Gera um hash SHA256 a partir de um registro normalizado.

    Parameters
    ----------
    record : dict
        Dicionário representando uma linha do DataFrame.

    Returns
    -------
    str
        Hash SHA256 gerado a partir do conteúdo do registro.

    Notes
    -----
    O hash é calculado com `sort_keys=True`, garantindo que a ordem das chaves
    não altere o resultado. Valores não serializáveis nativamente são
    convertidos para string por meio de `default=str`.
    """

    normalized = json.dumps(record, sort_keys=True, default=str)
    return hashlib.sha256(normalized.encode()).hexdigest()


def _clean_row(row: dict) -> dict:
    """
    Converte valores NaN em None para permitir serialização JSON adequada.

    Parameters
    ----------
    row : dict
        Dicionário representando uma linha do DataFrame.

    Returns
    -------
    dict
        Dicionário com valores NaN substituídos por None.
    """

    return {
        key: None if isinstance(value, float) and math.isnan(value) else value
        for key, value in row.items()
    }


def persist_dataframe_as_payload(
    engine: Engine,
    schema: str,
    table: str,
    dataframe: pd.DataFrame,
    timestampextraction: Optional[datetime] = None,
    basename: Optional[str] = None,
) -> int:
    """
    Persiste um DataFrame como payload JSONB em uma tabela PostgreSQL.

    Cada linha do DataFrame é convertida em um JSON, armazenada na coluna
    `payload` e acompanhada de um `hashid` calculado a partir do conteúdo do
    registro. A função utiliza `ON CONFLICT DO NOTHING` para evitar duplicidade
    conforme a constraint existente na tabela de destino.

    Parameters
    ----------
    engine : Engine
        SQLAlchemy Engine conectado ao banco PostgreSQL.

    schema : str
        Nome do schema onde a tabela de destino está localizada.

    table : str
        Nome da tabela de destino.

    dataframe : pd.DataFrame
        DataFrame que será persistido. Cada linha será convertida em JSONB.

    timestampextraction : datetime | None, default=None
        Data/hora da extração. Quando não informado, será usado o horário UTC
        do momento da execução.

    basename : str | None, default=None
        Nome base do arquivo ou origem da extração. Quando informado, a função
        insere também a coluna `basename` e considera a constraint
        `(basename, hashid)` no `ON CONFLICT`.

    Returns
    -------
    int
        Quantidade de registros efetivamente inseridos no banco.

    Raises
    ------
    ValueError
        Quando schema ou table possuem nomes inválidos.

    Notes
    -----
    - A tabela de destino precisa possuir uma constraint única compatível com
      o `ON CONFLICT` usado:
        - `(basename, hashid)` quando basename for informado;
        - `(hashid)` quando basename não for informado.
    - O hash é gerado apenas a partir do conteúdo do registro.
    - O campo `timestampextraction` não entra no cálculo do hash.
    - O campo `basename` não entra no cálculo do hash.
    """

    _validate_identifier(schema, "schema")
    _validate_identifier(table, "table")

    if dataframe.empty:
        return 0

    if timestampextraction is None:
        timestampextraction = datetime.utcnow()

    records = dataframe.to_dict(orient="records")
    records = [_clean_row(row) for row in records]

    rows_to_insert = []

    for record in records:
        hashid = _generate_hash(record)

        row = {
            "timestampextraction": timestampextraction,
            "payload": json.dumps(record, sort_keys=True, default=str),
            "hashid": hashid,
        }

        if basename is not None:
            row["basename"] = basename

        rows_to_insert.append(row)

    with engine.begin() as conn:
        if basename is not None:
            insert_stmt = text(f"""
                INSERT INTO {schema}.{table}
                (basename, timestampextraction, payload, hashid)
                VALUES (:basename, :timestampextraction, CAST(:payload AS jsonb), :hashid)
                ON CONFLICT (basename, hashid) DO NOTHING
            """)
        else:
            insert_stmt = text(f"""
                INSERT INTO {schema}.{table}
                (timestampextraction, payload, hashid)
                VALUES (:timestampextraction, CAST(:payload AS jsonb), :hashid)
                ON CONFLICT (hashid) DO NOTHING
            """)

        result = conn.execute(insert_stmt, rows_to_insert)

    return result.rowcount