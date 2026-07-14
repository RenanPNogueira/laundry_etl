"""
Script: verificar_overrides.py

Objetivo
--------
Conferir, depois da renomeação de tabelas/colunas do ETL, se os hashes
(`cd_transacao`) usados pelos overrides manuais em `gold_overridedata.py`
ainda batem com as transações que existem hoje nas tabelas Silver.

Este script é SOMENTE LEITURA: não faz INSERT, UPDATE, DELETE nem
TRUNCATE em nenhuma tabela. Ele recalcula o mesmo hash usado em
`gold_loader.py` (f_contacorrente e f_faturacartao) via SELECT puro e
compara com a lista de overrides cadastrada no código.

Como rodar
----------
Dentro do venv do projeto, na raiz do repo:

    python scripts/verificar_overrides.py
"""

from sqlalchemy import text

from lavesecexpress_etl.config.settings import DB_CONFIG
from lavesecexpress_etl.core.database.connection import get_engine
from lavesecexpress_etl.persistence.gold_overridedata import overrides


# ============================================================
# Mesma fórmula de hash usada em gold_loader.py (f_contacorrente)
# ============================================================
QUERY_HASHES_CONTACORRENTE = text(r"""
WITH Base_Referencia_Bruta AS (
    SELECT
        ds_banco
        , datatransacao AS dt_transacao
        , COALESCE(debito, credito) AS vl_transacao
        , debito IS NOT NULL AS fl_debito
        , CONCAT(
            TRIM(COALESCE(documento,'')),' ',
            TRIM(COALESCE(historico,'')),' ',
            TRIM(COALESCE(descricao,''))
        ) AS texto_busca
        , saldo
    FROM silver.bank1

    UNION ALL

    SELECT
        ds_banco
        , datatransacao AS dt_transacao
        , CASE WHEN saida = 0 THEN entrada ELSE saida END AS vl_transacao
        , saida <> 0 AS fl_debito
        , CONCAT(
            TRIM(COALESCE(titulo,'')),' ',
            TRIM(COALESCE(descricao,'')),' '
        ) AS texto_busca
        , saldo_do_dia AS saldo
    FROM silver.bank3
)
SELECT DISTINCT
    md5(
        concat_ws(
            '|'
            , dt_transacao
            , vl_transacao
            , CASE WHEN fl_debito THEN 'True' ELSE 'False' END
            , TRIM(REGEXP_REPLACE(REGEXP_REPLACE(unaccent(LOWER(texto_busca)),'[^a-z0-9 ]','','g'),'\s+',' ','g'))
            , saldo
        )
    ) AS cd_transacao
FROM Base_Referencia_Bruta
""")


# ============================================================
# Mesma fórmula de hash usada em gold_loader.py (f_faturacartao)
# ============================================================
QUERY_HASHES_FATURACARTAO = text(r"""
WITH Base_Referencia_Bruta AS (
    SELECT
        ds_banco
        , data_transacao AS dt_transacao
        , CONCAT(
            TRIM(COALESCE(portador,'')),' ',
            TRIM(COALESCE(cartao,'')),' ',
            TRIM(
                REGEXP_REPLACE(
                    COALESCE(descricao,'')
                    , ' - [0-9]+/[0-9]+$'
                    , ''
                )
            )
        ) AS texto_busca
    FROM silver.bank1_cartoes
    WHERE descricao NOT LIKE '%Pag de Fatura Via Deb Aut%'
)
SELECT DISTINCT
    md5(
        concat_ws(
            '|'
            , dt_transacao
            , TRIM(REGEXP_REPLACE(REGEXP_REPLACE(unaccent(LOWER(texto_busca)),'[^a-z0-9 ]','','g'),'\s+',' ','g'))
        )
    ) AS cd_transacao
FROM Base_Referencia_Bruta
""")


def main():
    engine = get_engine(**DB_CONFIG)

    with engine.connect() as conn:
        hashes_cc = {row[0] for row in conn.execute(QUERY_HASHES_CONTACORRENTE)}
        hashes_fatura = {row[0] for row in conn.execute(QUERY_HASHES_FATURACARTAO)}

    hashes_atuais = hashes_cc | hashes_fatura

    overrides_hashes = [cd for cd, _categoria in overrides]
    overrides_set = set(overrides_hashes)

    encontrados = overrides_set & hashes_atuais
    nao_encontrados = overrides_set - hashes_atuais

    print(f"Total de transações recalculadas hoje (conta corrente + fatura): {len(hashes_atuais)}")
    print(f"Total de overrides cadastrados em gold_overridedata.py: {len(overrides_set)}")
    print(f"Overrides que batem com uma transação atual: {len(encontrados)}")
    print(f"Overrides que NÃO bateram com nenhuma transação atual: {len(nao_encontrados)}")

    if nao_encontrados:
        print("\nHashes de override sem correspondência hoje:")
        for cd, categoria in overrides:
            if cd in nao_encontrados:
                print(f"  - {cd}  (categoria: {categoria})")
    else:
        print("\n✅ Todos os overrides cadastrados batem com transações existentes hoje.")


if __name__ == "__main__":
    main()
