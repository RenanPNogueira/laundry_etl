"""
Módulo: gold_loader.py

Responsabilidade
----------------
Executar a carga da camada Gold do ETL da lavanderia.

Contexto
--------
Este módulo faz parte da camada de persistência do pacote lavesecexpress_etl.
Ele consome tabelas da camada Silver e tabelas auxiliares do schema rules para
construir dimensões e fatos analíticos usados em dashboards e análises
financeiras/operacionais.

Estratégia de carga
-------------------
Cada tabela Gold configurada em GOLD_LOAD_CONFIG é carregada com estratégia
TRUNCATE + INSERT. A estrutura da camada Gold é garantida antes da carga por
ensure_gold_structure.

Principais grupos de carga
--------------------------
- Dimensões financeiras:
    d_bancos

- Fatos financeiras:
    f_contacorrente
    f_faturacartao

- Dimensões operacionais do sistema da lavanderia:
    d_lavanderias
    d_clientes
    d_maquinas
    d_metodopagamento
    d_falhas
    d_voucher
    d_cupom

- Fatos operacionais:
    f_vendas
    f_ciclos

Observações
-----------
Este módulo concentra regras de negócio importantes, especialmente regras de
categorização financeira, overrides manuais, regex de classificação e
relacionamento entre vendas do sistema da lavanderia e recebimentos do Banco 2.
"""


from sqlalchemy import text
from sqlalchemy.engine import Engine
from lavesecexpress_etl.persistence.gold_structure import ensure_gold_structure
from lavesecexpress_etl.persistence.gold_overridedata import overrides
from lavesecexpress_etl.persistence.regex_bank1_rules import regex_rules
from lavesecexpress_etl.persistence.rules_detalhestransacoes import categorias


## ========= SQL SCRIPTS
d_bancos =  """
INSERT INTO gold.d_bancos
(
    cd_banco,
    ds_banco
)

WITH

Bases_Bancos AS (
SELECT DISTINCT
	ds_banco
FROM silver.bank1

UNION ALL

SELECT DISTINCT
	ds_banco
FROM silver.bank3
)

SELECT
	ROW_NUMBER() OVER( ORDER BY ds_banco ):: INT AS cd_banco
	, ds_banco
FROM Bases_Bancos;
 """


f_contacorrente =  """
INSERT INTO gold.f_contacorrente
(
    cd_transacao,
    cd_banco,
    dt_transacao,
    fl_debito,
    cd_detalhetransacao,
    vl_transacao
)

WITH

Base_Referencia_Bruta AS (
--- Banco 1
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

--- Banco 3
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

, Base_Referencia_Hash AS (
SELECT
	ds_banco
	, dt_transacao
	, vl_transacao
	, fl_debito
	, UNACCENT( LOWER( texto_busca ) ) AS texto_busca
	, saldo
	, md5(
 		concat_ws(
		'|'
		, dt_transacao
		, vl_transacao
		, CASE
			WHEN fl_debito THEN 'True'
			ELSE 'False'
		END
		, TRIM(REGEXP_REPLACE(REGEXP_REPLACE(unaccent(LOWER(texto_busca)),'[^a-z0-9 ]','','g'),'\\s+',' ','g'))
		, saldo
       )
     ) AS cd_transacao
FROM Base_Referencia_Bruta
)


, Base_RegrasManuais_PadroesRegex AS (
SELECT
	-- a.ds_banco
	d.cd_banco
	, a.cd_transacao
	, a.fl_debito
	, a.dt_transacao
	, a.vl_transacao
	, a.texto_busca AS ds_original
	-- , b.ds_categoria AS ds_categorizacaopadrao
	-- , c.texto_busca AS ds_override
	, CASE
		WHEN a.texto_busca LIKE '%deb cartao%' AND vl_transacao = 0.01 THEN 'Ciclo Interno Lavanderia'
		WHEN COALESCE( c.texto_busca, b.ds_categoria ) = 'Estorno ciclos PIX' AND a.vl_transacao >= 80 THEN 'Transação não Identificada - Avaliar'
		WHEN COALESCE( c.texto_busca, b.ds_categoria ) IS NULL THEN 'Transação não Identificada - Avaliar'
		ELSE COALESCE( c.texto_busca, b.ds_categoria )
	END AS ds_final
FROM Base_Referencia_Hash AS a

	LEFT JOIN LATERAL (
	    SELECT
			ds_categoria
	    FROM rules.regexpadrao_detalhes_transacoes b

		    WHERE 1=1
				AND a.texto_busca ~ b.ds_regex
		    ORDER BY b.nr_prioridade

	    LIMIT 1
	) b ON TRUE

	LEFT JOIN rules.ajustes_manuais_transacoes AS c
		ON c.cd_transacao = a.cd_transacao

	LEFT JOIN gold.d_bancos AS d
		ON d.ds_banco = a.ds_banco
)

, Base_Final AS (
	SELECT
		a.cd_banco
		, a.cd_transacao
		, a.fl_debito
		, a.dt_transacao
		, a.vl_transacao
		-- , a.ds_original
		, b.cd_descricao
		-- , a.ds_final AS ds_detalhe -- Usado para validação
		-- , b.ds_tipodebito -- Usado para validação
		-- , b.fl_fixo -- Usado para validação
		-- , b.fl_operacional -- Usado para validação
		-- , b.fl_diluivel -- Usado para validação
		-- , b.fl_recorrente -- Usado para validação
	FROM Base_RegrasManuais_PadroesRegex AS a

		LEFT JOIN rules.padronizacao_categorias_transacoes AS b
			ON b.descricao = a.ds_final
)

SELECT
	cd_transacao
	, cd_banco
	, dt_transacao
	, fl_debito
	, cd_descricao AS cd_detalhetransacao
	, vl_transacao
FROM Base_Final

	ORDER BY dt_transacao DESC
"""


f_faturacartao =   """
INSERT INTO gold.f_faturacartao
(
    cd_transacao
    , cd_banco
	, ds_portador
	, nr_cartao
	, dt_transacao
	, dt_fatura
	, fl_parcelado
	, nr_parcela
	, nr_totalparcelas
	, fl_debito
	, cd_detalhetransacao
	, vl_transacao
)

WITH

Base_Referencia_Bruta AS (
SELECT
	ds_banco
	, data_transacao AS dt_transacao
	, dt_vencimento_fatura AS dt_fatura
	, portador AS ds_portador
	, cartao::INT AS nr_cartao
    , valores_extraidos::FLOAT AS vl_transacao
    , descricao ~ ' - [0-9]+/[0-9]+$' AS fl_parcelado
    , CASE
        WHEN descricao ~ ' - [0-9]+/[0-9]+$'
        THEN (regexp_match(descricao, ' - ([0-9]+)/([0-9]+)$'))[1]::INT
        ELSE 1
      END AS nr_parcela
    , CASE
        WHEN descricao ~ ' - [0-9]+/[0-9]+$'
        THEN (regexp_match(descricao, ' - ([0-9]+)/([0-9]+)$'))[2]::INT
        ELSE 1
      END AS nr_totalparcelas
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

	WHERE 1=1
		AND descricao NOT LIKE '%Pag de Fatura Via Deb Aut%'
)


, Base_Referencia_Hash AS (
SELECT
	ds_banco
	, dt_transacao
	, dt_fatura
	, ds_portador
	, nr_cartao
    , vl_transacao
    , fl_parcelado
    , nr_parcela
    , nr_totalparcelas
    , UNACCENT( LOWER( texto_busca ) ) AS texto_busca
	, md5(
 		concat_ws(
		'|'
		, dt_transacao
		, TRIM(REGEXP_REPLACE(REGEXP_REPLACE(unaccent(LOWER(texto_busca)),'[^a-z0-9 ]','','g'),'\\s+',' ','g'))
       )
     ) AS cd_transacao
FROM Base_Referencia_Bruta
)

, Base_RegrasManuais_PadroesRegex AS (
SELECT
	d.cd_banco
	, a.cd_transacao
	, a.dt_transacao
	, a.dt_fatura
	, a.ds_portador
	, a.nr_cartao
	, a.vl_transacao
	, a.fl_parcelado
	, a.nr_parcela
	, a.nr_totalparcelas
	, a.texto_busca AS ds_original
	-- , b.ds_categoria AS ds_categorizacaopadrao
	-- , c.texto_busca AS ds_override
	, CASE
		WHEN COALESCE( c.texto_busca, b.ds_categoria ) = 'Pagamento de Cliente via PIX' AND a.vl_transacao >= 80 THEN 'Transação não Identificada - Avaliar'
		WHEN COALESCE( c.texto_busca, b.ds_categoria ) = 'Estorno para Cliente via PIX' AND a.vl_transacao >= 80 THEN 'Transação não Identificada - Avaliar'
		WHEN COALESCE( c.texto_busca, b.ds_categoria ) IS NULL THEN 'Transação não Identificada - Avaliar'
		ELSE COALESCE( c.texto_busca, b.ds_categoria )
	END AS ds_final
FROM Base_Referencia_Hash AS a

	LEFT JOIN LATERAL (
	    SELECT
			ds_categoria
	    FROM rules.regexpadrao_detalhes_transacoes b

		    WHERE 1=1
				AND a.texto_busca ~ b.ds_regex
		    ORDER BY b.nr_prioridade

	    LIMIT 1
	) b ON TRUE

	LEFT JOIN rules.ajustes_manuais_transacoes AS c
		ON c.cd_transacao = a.cd_transacao

	LEFT JOIN gold.d_bancos AS d
		ON d.ds_banco = a.ds_banco
)

, Base_Final AS (
SELECT

	a.cd_transacao
	, a.cd_banco
	, a.dt_transacao
	, a.dt_fatura
	, a.ds_portador
	, a.nr_cartao
	, a.vl_transacao
	, a.fl_parcelado
	, a.nr_parcela
	, a.nr_totalparcelas
	-- , a.ds_original -- Usado para validação
	, b.cd_descricao
	-- , a.ds_final AS ds_detalhe
	-- , b.ds_tipodebito
	-- , b.fl_fixo
	-- , b.fl_operacional
	-- , b.fl_diluivel
	-- , b.fl_recorrente
FROM Base_RegrasManuais_PadroesRegex AS a

	LEFT JOIN rules.padronizacao_categorias_transacoes AS b
		ON b.descricao = a.ds_final
)

SELECT
	cd_transacao
	, cd_banco
	, ds_portador
	, nr_cartao
	, dt_transacao
	, dt_fatura
	, fl_parcelado
	, nr_parcela
	, nr_totalparcelas
	, vl_transacao > 0 AS fl_debito --- manter caso haja estorno ou cashback --- REVER REGRAS
	, cd_descricao AS cd_detalhetransacao
	, vl_transacao
FROM Base_Final;
 """


## SISTEMA DA LAVANDERIA
d_lavanderias = """
INSERT INTO gold.d_lavanderias
SELECT
	id AS cd_lavanderia
	, nome AS ds_lavanderia
	, cnpj AS cd_cnpj
FROM silver.laundry_system_lavanderias;
"""


d_clientes = """
INSERT INTO gold.d_clientes
	SELECT
		cpf AS nr_cpfcliente
		, nome AS ds_nome
		, email AS ds_email
		, genero AS ds_genero
		, telefone AS ds_telefone
		, datanascimento AS dt_nascimento
		, datacadastro AS dt_cadastro
		, datepartition AS datepartition
	FROM silver.laundry_system_clientes;
"""


d_maquinas =  """
INSERT INTO gold.d_maquinas
SELECT
	id AS cd_maquina
	, idlavanderia AS cd_lavanderia
	, nome AS ds_maquina
	, tipo AS ds_servico
FROM silver.laundry_system_maquinas;
"""


d_metodopagamento =  """
INSERT INTO gold.d_metodopagamento
WITH
Base_MetodoPagamentos AS (
	SELECT DISTINCT
		tipopagamento AS ds_tipo
	    , bandeiracartao AS ds_bandeiracartao
	    , tipocartao AS ds_tipopagamento
	    , MIN(CAST( "data" AS DATE ) ) AS dt_primeiroregistro
	FROM silver.laundry_system_vendas

	GROUP BY
    	tipopagamento
	    , bandeiracartao
	    , tipocartao

	 ORDER BY
     	dt_primeiroregistro
        , tipopagamento
        , bandeiracartao
        , tipocartao
)

SELECT
	ROW_NUMBER() OVER( ORDER BY dt_primeiroregistro, ds_tipo ) AS cd_modalidadepagamento
	, ds_tipo
	, ds_bandeiracartao
	, ds_tipopagamento
	-- , dt_primeiroregistro
FROM Base_MetodoPagamentos;
"""


d_falhas =   """
INSERT INTO gold.d_falhas
SELECT DISTINCT
	ROW_NUMBER() OVER() AS cd_erro
	, CAST( coderro AS INT )  AS cd_erroapi
	, erro
FROM silver.laundry_system_vendas

	WHERE 1=1
		AND status = 'FALHA'
		AND coderro <> ''

	GROUP BY
		CAST( coderro AS INT )
		, erro;
"""


d_voucher =   """
INSERT INTO gold.d_voucher
SELECT DISTINCT
	voucher AS cd_voucher
	, CASE
		WHEN nomecategoriavoucher IS NULL THEN 'Voucher não cadastrado no sistema'
		ELSE nomecategoriavoucher
	END AS ds_nome
FROM silver.laundry_system_VENDAS

	WHERE 1=1
		AND voucher <> ''
		AND voucher IS NOT NULL;
"""


d_cupom =   """
INSERT INTO gold.d_cupom
SELECT
	ROW_NUMBER() OVER( ORDER BY cupom ) AS cd_cupom
	, cupom AS ds_cupom
from silver.laundry_system_vendas

	WHERE 1=1
		AND cupom IS NOT NULL

	GROUP BY
		cupom;
"""


f_vendas =   """
INSERT INTO gold.f_vendas
SELECT
	a."data" AS dh_venda
	, g.datavencimento AS dt_compensacaopagamento
	, g.ultimostatus AS ds_statuspagamento
	, idvenda AS cd_venda
	, a.idlavanderia AS cd_lavanderia
	, a.status = 'SUCESSO' AS fl_status
	, a.cpfcliente:: BIGINT AS nr_cpfcliente
	, b.cd_modalidadepagamento
	, NULLIF(coderro, '')::INT AS cd_erro
	, c.cd_cupom
	, NULLIF( a.voucher, '') AS cd_voucher
	, a.valor AS vl_bruto
	, g.descontomdr AS vl_custooperacional
	, a.valorsemdesconto AS vl_brutosemdesconto
	, g.valorliquido AS vl_liquido
	, a.datepartition AS dt_partition
FROM silver.laundry_system_vendas AS a

	--- JOINS
	LEFT JOIN gold.d_metodopagamento AS b
		ON LOWER(TRIM(b.ds_tipo)) = LOWER(TRIM(a.tipopagamento))
		AND b.ds_bandeiracartao IS NOT DISTINCT FROM a.bandeiracartao
		AND b.ds_tipopagamento IS NOT DISTINCT FROM a.tipocartao

	LEFT JOIN gold.d_cupom AS c
		ON LOWER( TRIM( c.ds_cupom ) ) = LOWER( TRIM( a.cupom ) )

	LEFT JOIN silver.bank2 AS g
		ON CAST(g.stoneid AS VARCHAR) = REGEXP_REPLACE(TRIM(a.requisicao), '\.\d+$', '');
"""


f_ciclos =   """
INSERT INTO gold.f_ciclos
SELECT
	a.data AS dh_ciclo
	, a.idvenda AS cd_venda
	, idlavanderia AS cd_lavanderia
	, b.cd_maquina
	, a.status = 'SUCESSO' AS fl_status
	, NULLIF(coderro, '')::INT AS cd_erro
	, c.cd_modalidadepagamento
	, a.cpfcliente:: BIGINT AS nr_cpfcliente
FROM silver.laundry_system_ciclos AS a

	LEFT JOIN gold.d_maquinas AS b
		ON LOWER( TRIM( b.ds_maquina ) ) = LOWER( TRIM( a.maquina ) )
		AND LOWER( TRIM( b.ds_servico ) ) = LOWER( TRIM( a.tiposervico ) )
		AND b.cd_lavanderia = a.idlavanderia

	LEFT JOIN gold.d_metodopagamento AS c
		ON LOWER(TRIM(c.ds_tipo)) = LOWER(TRIM(a.tipopagamento))
		AND c.ds_bandeiracartao IS NOT DISTINCT FROM a.bandeiracartao
		AND c.ds_tipopagamento IS NOT DISTINCT FROM a.tipocartao;
"""


#============ CONFIG
GOLD_LOAD_CONFIG = [
    {
        "name": "d_bancos",
        "type": "sql",
        "table": "gold.d_bancos",
        "sql": d_bancos
    },
    {
        "name": "f_contacorrente",
        "type": "sql",
        "table": "gold.f_contacorrente",
        "sql": f_contacorrente
    },
    {
        "name": "f_faturacartao",
        "type": "sql",
        "table": "gold.f_faturacartao",
        "sql": f_faturacartao
    },
    # ================= DIMENSÕES (SISTEMA DA LAVANDERIA)
    {
        "name": "d_lavanderias",
        "type": "sql",
        "table": "gold.d_lavanderias",
        "sql": d_lavanderias
    },
    {
        "name": "d_clientes",
        "type": "sql",
        "table": "gold.d_clientes",
        "sql": d_clientes
    },
    {
        "name": "d_maquinas",
        "type": "sql",
        "table": "gold.d_maquinas",
        "sql": d_maquinas
    },
    {
        "name": "d_metodopagamento",
        "type": "sql",
        "table": "gold.d_metodopagamento",
        "sql": d_metodopagamento
    },
    {
        "name": "d_falhas",
        "type": "sql",
        "table": "gold.d_falhas",
        "sql": d_falhas
    },
    {
        "name": "d_voucher",
        "type": "sql",
        "table": "gold.d_voucher",
        "sql": d_voucher
    },
    {
        "name": "d_cupom",
        "type": "sql",
        "table": "gold.d_cupom",
        "sql": d_cupom
    },

    # ================= FATOS (dependem das dims)
    {
        "name": "f_vendas",
        "type": "sql",
        "table": "gold.f_vendas",
        "sql": f_vendas
    },
    {
        "name": "f_ciclos",
        "type": "sql",
        "table": "gold.f_ciclos",
        "sql": f_ciclos
    }
]


#================== ORCHESTRATOR
def execute_gold_load(engine: Engine, config: dict) -> None:

    name = config.get("name", "unknown")

    try:
        with engine.begin() as conn:

            # ================= SQL PURO
            if config["type"] == "sql":
                conn.execute(text(f"TRUNCATE TABLE {config['table']}"))
                conn.execute(text(config["sql"]))

            # ================= SQL COM PARAMETROS
            elif config["type"] == "sql_with_params":
                conn.execute(text(f"TRUNCATE TABLE {config['table']}"))
                conn.execute(
                    text(config["sql"]),
                    config["data"]
                )

            # ================= PYTHON (caso futuro)
            elif config["type"] == "python":
                config["func"](engine)

            else:
                raise ValueError(f"Tipo desconhecido: {config['type']}")

        print(f"🟢 [{name}] executado com sucesso.")

    except Exception as e:
        print(f"🔴 Erro na etapa [{name}]")
        raise e


#================== FINAL FUNCTION
def load_gold_layer(engine: Engine) -> None:
    ensure_gold_structure(engine)

    print("🚀 Iniciando carga da camada GOLD")

    for config in GOLD_LOAD_CONFIG:
        execute_gold_load(engine, config)

    print("✅ Carga da camada GOLD finalizada")
