"""
Módulo: metadata_cleaner.py

Responsabilidade
----------------
Fornecer funções utilitárias para limpeza genérica de metadados estruturais
em DataFrames tabulares.

Contexto
--------
Este módulo faz parte do módulo `core` do pacote `lavesecexpress_etl`, uma biblioteca reutilizável
para engenharia de dados. Ele é útil para tratar arquivos CSV ou Excel que
possuem linhas informativas antes da tabela principal, rodapés após os dados
ou colunas fantasmas geradas durante a leitura.

Principais componentes
----------------------
- clean_metadata: aplica as etapas genéricas de limpeza estrutural.
- _detect_table_start: identifica a linha provável de início da tabela.
- _remove_footer: remove linhas após a primeira linha totalmente vazia.
- _remove_ghost_columns: remove colunas vazias ou iniciadas por "Unnamed".

Observações
-----------
Este módulo não aplica regras de negócio. Ele apenas prepara a estrutura
tabular para etapas posteriores de transformação.
"""

import pandas as pd


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _detect_table_start(
    df: pd.DataFrame,
    min_filled_columns: int = 4
) -> int:
    """
    Detecta o índice da linha onde a tabela principal provavelmente começa.

    A função considera como início da tabela a primeira linha que possui pelo
    menos `min_filled_columns` células preenchidas e cuja linha seguinte também
    possui pelo menos essa quantidade de células preenchidas.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame bruto que será analisado.

    min_filled_columns : int, default=4
        Quantidade mínima de células preenchidas usada para considerar uma
        linha como candidata ao início da tabela.

    Returns
    -------
    int
        Índice da linha provável de início da tabela. Retorna 0 caso nenhuma
        candidata seja identificada.
    """

    total_rows = len(df)

    for i in range(total_rows - 1):

        current_row = df.iloc[i]
        next_row = df.iloc[i + 1]

        current_filled = (
            current_row.notna() &
            (current_row.astype(str).str.strip() != "")
        ).sum()

        next_filled = (
            next_row.notna() &
            (next_row.astype(str).str.strip() != "")
        ).sum()

        if current_filled >= min_filled_columns and next_filled >= min_filled_columns:
            return i

    return 0


def _remove_footer(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove o rodapé a partir da primeira linha completamente vazia.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame que será avaliado.

    Returns
    -------
    pd.DataFrame
        DataFrame sem o conteúdo posterior à primeira linha vazia.
    """

    empty_rows = df.isna().all(axis=1)

    if empty_rows.any():
        first_empty_index = empty_rows.idxmax()
        df = df.loc[: first_empty_index - 1]

    return df.reset_index(drop=True)


def _remove_ghost_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove colunas fantasmas do DataFrame.

    São consideradas colunas fantasmas:
    - colunas cujo nome começa com "Unnamed";
    - colunas completamente vazias.

    A função também considera cenários com nomes de colunas duplicados, onde
    o acesso a uma coluna pode retornar um DataFrame em vez de uma Series.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame que terá colunas fantasmas removidas.

    Returns
    -------
    pd.DataFrame
        DataFrame sem colunas fantasmas.
    """

    ghost_columns = []

    for col in df.columns:

        if str(col).strip().lower().startswith("unnamed"):
            ghost_columns.append(col)
            continue

        column_data = df.loc[:, col]

        if isinstance(column_data, pd.DataFrame):
            if column_data.isna().all().all():
                ghost_columns.append(col)
        else:
            if column_data.isna().all():
                ghost_columns.append(col)

    if ghost_columns:
        df = df.drop(columns=ghost_columns)

    return df


# ============================================================
# PUBLIC API
# ============================================================

def clean_metadata(
    df: pd.DataFrame,
    detect_header: bool = True,
    min_consecutive_filled: int = 4,
    remove_footer: bool = True,
    remove_ghost_columns: bool = True
) -> pd.DataFrame:
    """
    Aplica etapas genéricas de limpeza estrutural em um DataFrame.

    A função pode detectar o início real da tabela, remover rodapés após a
    primeira linha completamente vazia e excluir colunas fantasmas.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame bruto que será limpo.

    detect_header : bool, default=True
        Indica se a função deve tentar detectar dinamicamente o início da
        tabela principal.

    min_consecutive_filled : int, default=4
        Quantidade mínima de células preenchidas usada para identificar o
        início provável da tabela.

    remove_footer : bool, default=True
        Indica se a função deve remover o conteúdo após a primeira linha
        completamente vazia.

    remove_ghost_columns : bool, default=True
        Indica se a função deve remover colunas vazias ou colunas cujo nome
        começa com "Unnamed".

    Returns
    -------
    pd.DataFrame
        DataFrame limpo, preservando a lógica original da função.

    Notes
    -----
    A função não altera o DataFrame original. Ela cria uma cópia antes de
    aplicar as etapas de limpeza.
    """

    df_clean = df.copy()

    # Detecta a linha de início da tabela principal.
    if detect_header:
        start_index = _detect_table_start(
            df_clean,
            min_filled_columns=min_consecutive_filled
        )

    # Mantém o comportamento original:
    # só desloca o cabeçalho quando o início detectado não está na linha 0.
    if start_index != 0:
        df_clean = df_clean.iloc[start_index:].reset_index(drop=True)
        df_clean.columns = df_clean.iloc[0]
        df_clean = df_clean[1:].reset_index(drop=True)

    if remove_footer:
        df_clean = _remove_footer(df_clean)

    if remove_ghost_columns:
        df_clean = _remove_ghost_columns(df_clean)

    return df_clean