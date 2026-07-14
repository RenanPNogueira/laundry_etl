"""
Módulo: column_standardizer.py

Responsabilidade
----------------
Fornecer funções utilitárias para padronização de nomes de colunas em
DataFrames pandas.

Contexto
--------
Este módulo faz parte do módulo `core` do pacote `lavesecexpress_etl`, uma biblioteca reutilizável
para engenharia de dados. Ele deve conter apenas regras genéricas de
normalização de colunas, sem depender de fontes de dados ou regras de negócio
específicas.

Principais componentes
----------------------
- standardize_columns: retorna uma cópia do DataFrame com nomes de colunas
  padronizados.
- _normalize_column_name: aplica as regras de normalização em uma coluna.
- _remove_accents: remove acentuação de textos.

Regras de padronização
----------------------
- converte o nome da coluna para string;
- converte para minúsculas;
- remove acentos;
- substitui espaços e hífens por underscore;
- remove caracteres especiais;
- remove underscores duplicados;
- remove underscores no início e no fim;
- torna nomes duplicados únicos com sufixos incrementais.
"""

import re
import unicodedata

import pandas as pd


def _remove_accents(text: str) -> str:
    """
    Remove acentos de uma string.

    Parameters
    ----------
    text : str
        Texto original que será normalizado.

    Returns
    -------
    str
        Texto sem acentuação.
    """

    normalized = unicodedata.normalize("NFKD", text)
    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )


def _normalize_column_name(column: str) -> str:
    """
    Aplica regras de normalização a um único nome de coluna.

    Parameters
    ----------
    column : str
        Nome original da coluna.

    Returns
    -------
    str
        Nome da coluna padronizado.
    """

    column = str(column)
    column = column.lower()
    column = _remove_accents(column)
    column = re.sub(r"[ \-]+", "_", column)
    column = re.sub(r"[^a-z0-9_]", "", column)
    column = re.sub(r"_+", "_", column)
    column = column.strip("_")

    return column


def _make_unique_column_names(columns: list[str]) -> list[str]:
    """
    Garante que a lista de colunas não possua nomes duplicados.

    Quando um nome de coluna aparece mais de uma vez, a função adiciona
    sufixos incrementais a partir da segunda ocorrência.

    Examples
    --------
    ["debito", "debito", "credito"] vira:
    ["debito", "debito_2", "credito"]

    Parameters
    ----------
    columns : list[str]
        Lista de nomes de colunas já normalizados.

    Returns
    -------
    list[str]
        Lista de nomes de colunas únicos.
    """

    seen: dict[str, int] = {}
    unique_columns: list[str] = []

    for column in columns:
        if column not in seen:
            seen[column] = 1
            unique_columns.append(column)
            continue

        seen[column] += 1
        unique_columns.append(f"{column}_{seen[column]}")

    return unique_columns


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Retorna uma cópia do DataFrame com os nomes das colunas padronizados.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame original cujas colunas serão padronizadas.

    Returns
    -------
    pd.DataFrame
        Cópia do DataFrame original com nomes de colunas normalizados.

    Notes
    -----
    A função não altera o DataFrame original. Ela cria uma cópia antes de
    aplicar a padronização.

    Caso duas ou mais colunas resultem no mesmo nome após a normalização,
    são adicionados sufixos incrementais para garantir unicidade.
    """

    df_clean = df.copy()

    normalized_columns = [
        _normalize_column_name(column)
        for column in df_clean.columns
    ]

    df_clean.columns = _make_unique_column_names(normalized_columns)

    return df_clean