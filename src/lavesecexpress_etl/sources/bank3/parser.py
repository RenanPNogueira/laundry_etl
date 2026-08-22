import csv
import re
import pandas as pd

from lavesecexpress_etl.core.transformation.column_standardizer import standardize_columns


def parse_valor_bank3(valor):
    if valor is None:
        return None

    valor = str(valor).strip()

    if valor == "" or valor.lower() in ["none", "nan"]:
        return None

    # Exemplo: 1.234,56
    if "," in valor and "." in valor:
        valor = valor.replace(".", "").replace(",", ".")

    # Exemplo: 1234,56
    elif "," in valor:
        valor = valor.replace(",", ".")

    # Exemplo: 1234.56
    # Mantém como está.

    return pd.to_numeric(valor, errors="coerce")


def _recover_fully_quoted_row(linha, expected_columns):
    """Recupera uma linha CSV inteira que foi encapsulada por aspas."""

    if len(linha) != 1 or not isinstance(linha[0], str):
        return linha

    conteudo = linha[0].strip()

    if not re.match(r"^\d{2}/\d{2}/\d{4},", conteudo):
        return linha

    linha_recuperada = next(csv.reader([conteudo], delimiter=",", quotechar='"'))

    if len(linha_recuperada) == expected_columns:
        return linha_recuperada

    return linha


def parse_bank3(file_path: str) -> pd.DataFrame:

    with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter=",", quotechar='"')
        linhas = list(reader)

    header_index = None

    for i, linha in enumerate(linhas):
        if any("Data Lançamento" in str(col) for col in linha):
            header_index = i
            break

    if header_index is None:
        raise ValueError("Header do Banco 3 não encontrado")

    header = linhas[header_index]

    header = [
        re.sub(r"\(.*?\)", "", str(col).strip().strip('"')).strip()
        for col in header
    ]

    linhas_processadas = []

    for line_number, linha in enumerate(
        linhas[header_index + 1:],
        start=header_index + 2,
    ):

        if not linha or all(str(col).strip() == "" for col in linha):
            continue

        linha = _recover_fully_quoted_row(linha, len(header))

        primeira_coluna = str(linha[0]).strip() if linha else ""

        if len(linha) != len(header) and re.match(
            r"^\d{2}/\d{2}/\d{4}(?:,|$)", primeira_coluna
        ):
            raise ValueError(
                f"Linha {line_number} inválida no arquivo do Banco 3 "
                f"'{file_path}': esperadas {len(header)} colunas, "
                f"encontradas {len(linha)}."
            )

        if len(linha) < len(header):
            linha += [None] * (len(header) - len(linha))
        elif len(linha) > len(header):
            linha = linha[:len(header)]

        linha = [
            str(col).strip().strip('"') if col is not None and str(col).strip() != "" else None
            for col in linha
        ]

        linhas_processadas.append(linha)

    df = pd.DataFrame(linhas_processadas, columns=header)

    df = standardize_columns(df)

    colunas_esperadas = [
        "data_lancamento",
        "data_contabil",
        "titulo",
        "descricao",
        "entrada",
        "saida",
        "saldo_do_dia",
    ]

    colunas_ausentes = [col for col in colunas_esperadas if col not in df.columns]

    if colunas_ausentes:
        raise ValueError(
            f"Colunas esperadas não encontradas no extrato do Banco 3: {colunas_ausentes}. "
            f"Colunas encontradas: {list(df.columns)}"
        )

    df["data_lancamento"] = pd.to_datetime(
        df["data_lancamento"],
        format="%d/%m/%Y",
        errors="coerce",
    )

    df["data_contabil"] = pd.to_datetime(
        df["data_contabil"],
        format="%d/%m/%Y",
        errors="coerce",
    )

    for col in ["entrada", "saida", "saldo_do_dia"]:
        df[col] = df[col].apply(parse_valor_bank3)

    # Remove qualquer linha que não seja lançamento real.
    df = df[
        df["data_lancamento"].notna()
        & (
            df["entrada"].notna()
            | df["saida"].notna()
        )
    ].copy()

    return df
