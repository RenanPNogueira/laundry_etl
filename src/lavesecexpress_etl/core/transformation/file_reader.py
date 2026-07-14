"""
Módulo: file_reader.py

Responsabilidade
----------------
Fornecer funções utilitárias para leitura padronizada de arquivos tabulares
em pipelines de dados.

Contexto
--------
Este módulo faz parte do módulo `core` do pacote `lavesecexpress_etl`, uma biblioteca reutilizável
para engenharia de dados. Ele foi criado para centralizar a leitura de arquivos
CSV e Excel, evitando duplicação de código entre diferentes projetos.

Formatos suportados
-------------------
- .csv
- .xls
- .xlsx

Principais componentes
----------------------
- detect_csv_delimiter: tenta identificar automaticamente o delimitador de um
  arquivo CSV.
- read_tabular_file: lê arquivos tabulares e retorna um DataFrame pandas.

Observações
-----------
Por padrão, os dados são lidos como string. Essa decisão preserva valores
originais em camadas iniciais de ingestão e evita inferências automáticas
indevidas feitas pelo pandas.
"""

import csv
import os
from itertools import islice
from typing import Optional

import pandas as pd


SUPPORTED_EXCEL_EXTENSIONS = (".xls", ".xlsx")
SUPPORTED_CSV_EXTENSIONS = (".csv",)


def detect_csv_delimiter(
    file_path: str,
    sample_lines: int = 5,
    encoding: str = "utf-8-sig",
) -> str:
    """
    Detecta automaticamente o delimitador de um arquivo CSV.

    A função lê uma pequena amostra do arquivo e utiliza `csv.Sniffer` para
    inferir o delimitador. Caso a detecção falhe, retorna ponto e vírgula
    como fallback, por ser comum em exportações CSV em ambientes brasileiros.

    Parameters
    ----------
    file_path : str
        Caminho completo do arquivo CSV.

    sample_lines : int, default=5
        Quantidade máxima de linhas usadas na amostra para inferência.

    encoding : str, default="utf-8-sig"
        Encoding usado na leitura do arquivo.

    Returns
    -------
    str
        Delimitador detectado. Retorna ";" caso a detecção falhe.

    Notes
    -----
    O fallback para ";" é intencional, pois muitos arquivos CSV exportados
    em sistemas nacionais utilizam ponto e vírgula como separador.
    """

    try:
        with open(file_path, "r", encoding=encoding) as file:
            sample = "".join(islice(file, sample_lines))

        if not sample.strip():
            return ";"

        sniffer = csv.Sniffer()
        return sniffer.sniff(sample).delimiter

    except Exception:
        return ";"


def read_tabular_file(
    file_path: str,
    encoding: str = "utf-8-sig",
    force_delimiter: Optional[str] = None,
) -> pd.DataFrame:
    """
    Lê arquivos tabulares CSV ou Excel e retorna um DataFrame pandas.

    A função identifica automaticamente o tipo do arquivo pela extensão.
    Para arquivos CSV, detecta o delimitador automaticamente, exceto quando
    `force_delimiter` é informado.

    Parameters
    ----------
    file_path : str
        Caminho completo do arquivo que será lido.

    encoding : str, default="utf-8-sig"
        Encoding usado na leitura de arquivos CSV.

    force_delimiter : str | None, default=None
        Delimitador manual para arquivos CSV. Quando informado, substitui a
        detecção automática.

    Returns
    -------
    pd.DataFrame
        DataFrame carregado com todas as colunas como string.

    Raises
    ------
    FileNotFoundError
        Quando o arquivo informado não existe.

    ValueError
        Quando a extensão do arquivo não é suportada.

    Notes
    -----
    - Arquivos Excel são lidos com `pd.read_excel`.
    - Arquivos CSV são lidos com `pd.read_csv`.
    - O parâmetro `dtype=str` preserva os valores originais como texto.
    """

    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

    extension = os.path.splitext(file_path)[-1].lower()

    if extension in SUPPORTED_EXCEL_EXTENSIONS:
        return pd.read_excel(
            file_path,
            dtype=str,
        )

    if extension in SUPPORTED_CSV_EXTENSIONS:
        delimiter = (
            force_delimiter
            if force_delimiter is not None
            else detect_csv_delimiter(
                file_path=file_path,
                encoding=encoding,
            )
        )

        return pd.read_csv(
            file_path,
            sep=delimiter,
            dtype=str,
            encoding=encoding,
        )

    raise ValueError(f"Formato de arquivo não suportado: {extension}")