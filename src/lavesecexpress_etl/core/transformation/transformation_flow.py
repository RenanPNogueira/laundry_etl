"""
Módulo: transformation_flow.py

Responsabilidade
----------------
Orquestrar um fluxo genérico de leitura, limpeza e padronização de arquivos
tabulares em nível de pasta.

Contexto
--------
Este módulo faz parte do módulo `core` do pacote `lavesecexpress_etl`, uma biblioteca reutilizável
para engenharia de dados. Ele foi criado para processar arquivos CSV, XLS e
XLSX existentes em uma ou mais pastas, agrupando os dados por origem lógica.

Estratégia do fluxo
-------------------
Para cada arquivo encontrado:
1. valida se a extensão é suportada;
2. identifica a origem do arquivo usando uma função externa;
3. aplica um parser específico, quando fornecido;
4. caso contrário, aplica o fluxo padrão:
   - leitura tabular;
   - limpeza de metadados;
   - padronização de colunas;
5. agrupa os DataFrames por origem;
6. concatena os arquivos pertencentes à mesma origem.

Principais componentes
----------------------
- run: executa o fluxo genérico de transformação por pasta.

Observações
-----------
Este módulo não contém regras específicas de negócio. A identificação da origem
dos arquivos e eventuais parsers específicos devem ser definidos pelo projeto
consumidor.
"""

import os
from typing import Callable, Dict, List

import pandas as pd

from lavesecexpress_etl.core.transformation.column_standardizer import standardize_columns
from lavesecexpress_etl.core.transformation.file_reader import read_tabular_file
from lavesecexpress_etl.core.transformation.metadata_cleaner import clean_metadata


def run(
    folder_paths,
    identify_source: Callable[[str], str],
    parsers: Dict[str, Callable] = None,
    extensions: tuple = (".csv", ".xls", ".xlsx"),
) -> Dict[str, pd.DataFrame]:
    """
    Executa um fluxo genérico de transformação para arquivos tabulares.

    A função percorre uma ou mais pastas, identifica arquivos com extensões
    suportadas, classifica cada arquivo em uma origem lógica e retorna os dados
    agrupados por origem em um dicionário de DataFrames.

    Parameters
    ----------
    folder_paths : str | list[str]
        Caminho de uma pasta ou lista de pastas que serão processadas.

    identify_source : Callable[[str], str]
        Função responsável por identificar a origem lógica do arquivo a partir
        do nome do arquivo. Deve retornar uma string representando a origem.
        Caso retorne valor vazio ou None, o arquivo será ignorado.

    parsers : dict[str, Callable] | None, default=None
        Dicionário opcional de parsers específicos por origem. A chave deve
        ser o nome da origem retornada por `identify_source`, e o valor deve
        ser uma função que recebe `file_path` e retorna um DataFrame.

    extensions : tuple, default=(".csv", ".xls", ".xlsx")
        Extensões de arquivos que serão consideradas no processamento.

    Returns
    -------
    dict[str, pd.DataFrame]
        Dicionário onde cada chave representa uma origem lógica e cada valor
        contém o DataFrame consolidado dos arquivos daquela origem.

    Raises
    ------
    FileNotFoundError
        Quando uma das pastas informadas não existe.

    Notes
    -----
    Quando não houver parser específico para uma origem, a função aplica o
    fluxo padrão:
    - read_tabular_file()
    - clean_metadata()
    - standardize_columns()

    Se nenhum arquivo compatível for encontrado, retorna um dicionário vazio.
    """

    if isinstance(folder_paths, str):
        folder_paths = [folder_paths]

    grouped_data: Dict[str, List[pd.DataFrame]] = {}

    for folder_path in folder_paths:

        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        for file_name in os.listdir(folder_path):

            file_path = os.path.join(folder_path, file_name)

            if not os.path.isfile(file_path):
                continue

            ext = os.path.splitext(file_name)[-1].lower()

            if ext not in extensions:
                continue

            source = identify_source(file_name)

            if not source:
                continue

            parser = parsers.get(source) if parsers else None

            if parser:
                df = parser(file_path)
            else:
                df = read_tabular_file(file_path)
                df = clean_metadata(df)
                df = standardize_columns(df)

            grouped_data.setdefault(source, []).append(df)

    return {
        source: pd.concat(dfs, ignore_index=True)
        for source, dfs in grouped_data.items()
    }