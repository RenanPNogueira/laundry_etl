"""
Módulo: pdf_reader.py

Responsabilidade
----------------
Extrair dados brutos de faturas PDF do cartão do Banco 1.

Contexto
--------
Este módulo faz parte da integração do Banco 1. Ele é usado para processar
relatórios de fatura de cartão em formato PDF,
extraindo transações em uma estrutura tabular para posterior ingestão na
camada RAW.

Estratégia de extração
----------------------
O parser utiliza pdfplumber para extrair texto das páginas do PDF e aplica
regras baseadas em linhas e expressões regulares. A extração não depende de
tabelas estruturadas do PDF.

Principais componentes
----------------------
- extrair_dados_fatura:
    Processa um único PDF e retorna uma lista de registros extraídos.

- processar_pasta:
    Processa todos os PDFs de uma pasta e retorna um DataFrame consolidado.

Campos extraídos
----------------
- arquivo;
- portador;
- cartao;
- data_transacao;
- descricao;
- valores_extraidos;
- linha_original;
- dt_vencimento_fatura.

Observações
-----------
Este módulo não baixa arquivos, não transforma valores em regras finais de
negócio e não persiste dados no banco. Ele apenas extrai e estrutura dados
brutos a partir dos PDFs.
"""

import pdfplumber
import pandas as pd
import re
import os


def extrair_dados_fatura(pdf_path, debug=False):
    """
    Extrai registros brutos de uma fatura PDF do cartão do Banco 1.

    A função lê o texto do PDF, identifica blocos por portador/cartão, detecta
    o início das tabelas de transações e captura linhas contendo datas de
    transação. Para cada linha capturada, extrai valores monetários, descrição
    e metadados de origem.

    Parameters
    ----------
    pdf_path : str
        Caminho completo do arquivo PDF que será processado.

    debug : bool, default=False
        Quando True, imprime uma amostra das linhas extraídas do PDF para
        auxiliar na validação do parser.

    Returns
    -------
    list[dict]
        Lista de registros extraídos do PDF.

    Notes
    -----
    - A função preserva a linha original em `linha_original`.
    - Os valores monetários são mantidos como lista em `valores_extraidos`.
    - A data de vencimento da fatura é extraída de forma heurística.
    - PDFs baseados em imagem podem não ser processados corretamente sem OCR.
    """

    registros = []
    dt_vencimento_fatura = None

    with pdfplumber.open(pdf_path) as pdf:

        linhas = []

        # ===============================
        # 1. EXTRAIR TODAS AS LINHAS
        # ===============================
        for page in pdf.pages:
            texto = page.extract_text()
            if texto:
                linhas.extend(texto.split("\n"))

        if debug:
            print(f"\n📄 DEBUG - Linhas do PDF: {os.path.basename(pdf_path)}")
            for l in linhas[:50]:
                print(l)

        # ===============================
        # 2. EXTRAIR DATA DE VENCIMENTO
        # ===============================
        for linha in linhas:
            if re.search(r'venc', linha, re.IGNORECASE) and re.search(r'\d{2}/\d{2}/\d{4}', linha):
                match = re.search(r'\d{2}/\d{2}/\d{4}', linha)
                if match:
                    dt_vencimento_fatura = match.group()
                    break

        # ===============================
        # 3. STATE MACHINE
        # ===============================
        current_portador = None
        current_cartao = None
        capturando = False

        # ===============================
        # 4. LOOP PRINCIPAL
        # ===============================
        for linha in linhas:

            linha_clean = linha.strip()

            # -------------------------------
            # DETECTAR BLOCO (PORTADOR)
            # -------------------------------
            if "SISPRIME" in linha_clean.upper() and "MASTER" in linha_clean.upper():

                capturando = False

                partes = linha_clean.split("|")

                current_portador = partes[0].strip() if len(partes) > 0 else None

                match_cartao = re.search(r'-\s*(\d+)', linha_clean)
                current_cartao = match_cartao.group(1) if match_cartao else None

                continue

            # -------------------------------
            # DETECTAR HEADER (FLEXÍVEL)
            # -------------------------------
            if (
                re.search(r'data', linha_clean, re.IGNORECASE)
                and re.search(r'descri', linha_clean, re.IGNORECASE)
            ):
                capturando = True
                continue

            # -------------------------------
            # PARAR CAPTURA
            # -------------------------------
            if (
                "Total" in linha_clean
                or "*Valor" in linha_clean
                or "Saldo" in linha_clean
            ):
                capturando = False
                continue

            # -------------------------------
            # LINHAS DE TRANSAÇÃO
            # -------------------------------
            if capturando and current_portador is not None:

                # detectar data em qualquer posição
                match_data = re.search(r'\d{2}/\d{2}/\d{4}', linha_clean)

                if match_data:

                    data = match_data.group()

                    # ===============================
                    # EXTRAIR VALORES (robusto)
                    # ===============================
                    valores = re.findall(r'-?\d{1,3}(?:\.\d{3})*,\d{2}', linha_clean)

                    # ===============================
                    # EXTRAIR DESCRIÇÃO
                    # ===============================
                    descricao = linha_clean

                    descricao = descricao.replace(data, "")

                    for v in valores:
                        descricao = descricao.replace(v, "")

                    descricao = descricao.strip()

                    # ===============================
                    # REGISTRO RAW
                    # ===============================
                    registros.append({
                        "arquivo": os.path.basename(pdf_path),
                        "portador": current_portador,
                        "cartao": current_cartao,
                        "data_transacao": data,
                        "descricao": descricao,
                        "valores_extraidos": valores,
                        "linha_original": linha_clean,
                        "dt_vencimento_fatura": dt_vencimento_fatura
                    })

    return registros


def processar_pasta(pasta_pdf, debug=False):

    arquivos = [f for f in os.listdir(pasta_pdf) if f.lower().endswith(".pdf")]

    if not arquivos:
        print("⚠️ Nenhum arquivo PDF encontrado na pasta.")
        return pd.DataFrame()

    todos_registros = []

    for arquivo in arquivos:

        caminho = os.path.join(pasta_pdf, arquivo)

        print(f"📄 Processando: {arquivo}")

        registros = extrair_dados_fatura(caminho, debug=debug)

        if not registros:
            print(f"🚨 ALERTA: PDF sem registros extraídos -> {arquivo}")

        todos_registros.extend(registros)

    df = pd.DataFrame(todos_registros)

    return df

# # ===============================
# # EXECUÇÃO LOCAL (debug opcional)
# # ===============================
# if __name__ == "__main__":

#     pasta = r"C:\Development\lavesecexpress\lavesecexpress_etl\data\support\bank1_cartoes"

#     df = processar_pasta(pasta, debug=True)

#     print("\n📊 Preview:")
#     print(df.head())

#     print("\n📦 Total de registros:", len(df))

#     print("\n📊 Estrutura:")
#     print(df.info())

#     print("\n🔍 Nulos por coluna:")
#     print(df.isnull().sum())