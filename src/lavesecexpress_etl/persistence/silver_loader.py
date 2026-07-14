"""
Módulo: silver_loader.py

Responsabilidade
----------------
Executar a carga da camada Silver a partir das tabelas RAW do ETL da
lavanderia.

Contexto
--------
Este módulo faz parte da camada de persistência do pacote lavesecexpress_etl.
Ele transforma registros brutos armazenados como payload JSONB em tabelas
relacionais tipadas no schema silver.

Estratégia de carga
-------------------
Cada tabela Silver configurada em SILVER_LOAD_CONFIG é carregada com estratégia
TRUNCATE + INSERT. A estrutura da camada Silver é garantida antes da carga por
ensure_silver_structure.

Principais fontes
-----------------
- raw.bank1:
    origem da conta corrente do Banco 1.

- raw.bank1_cartao:
    origem das faturas PDF de cartão.

- raw.bank2:
    origem dos recebimentos do Banco 2.

- raw.bank3:
    origem do extrato do Banco 3.

- raw.laundry_system:
    origem das entidades operacionais do sistema da lavanderia, separadas por
    basename.

Observações
-----------
Este módulo não extrai dados externos e não carrega a camada Gold. Ele apenas
normaliza dados RAW em estruturas relacionais intermediárias.
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine
from lavesecexpress_etl.persistence.silver_structure import ensure_silver_structure


# ========== SQL CODES
bank1 = """
INSERT INTO silver.bank1 (
    ds_banco
    , datatransacao
    , documento
    , historico
    , debito
    , credito
    , saldo
    , descricao
    , datepartition
)

WITH base AS (
    SELECT DISTINCT
        'bank1' AS ds_banco
        , to_date(payload ->> 'data', 'DD/MM/YYYY') AS datatransacao
        , TRIM(payload ->> 'documento') AS documento
        , TRIM(payload ->> 'histrico') AS historico
        , NULLIF(REPLACE(payload ->> 'dbito', ',', '.'), '')::double precision AS debito
        , NULLIF(REPLACE(payload ->> 'crdito', ',', '.'), '')::double precision AS credito
        , NULLIF(REPLACE(payload ->> 'saldo', ',', '.'), '')::double precision AS saldo
        , TRIM(payload ->> 'descrio') AS descricao
        , now() AS datepartition
    FROM raw.bank1
)

SELECT
    ds_banco
    , datatransacao
    , documento
    , historico
    , debito
    , credito
    , saldo
    , descricao
    , datepartition
FROM base
WHERE datatransacao IS NOT NULL
  AND COALESCE(debito, credito) IS NOT NULL;
"""


bank3 = """
INSERT INTO silver.bank3

SELECT DISTINCT
    'bank3' AS ds_banco
    , CASE
        WHEN payload ->> 'data_lancamento' ~ '^\d{2}/\d{2}/\d{4}$'
            THEN to_date(payload ->> 'data_lancamento', 'DD/MM/YYYY')
        WHEN payload ->> 'data_lancamento' ~ '^\d{4}-\d{2}-\d{2}'
            THEN (payload ->> 'data_lancamento')::timestamp::date
        ELSE NULL
    END AS datatransacao
    , CASE
        WHEN payload ->> 'data_contabil' ~ '^\d{2}/\d{2}/\d{2,4}$'
            THEN to_date(payload ->> 'data_contabil', 'DD/MM/YYYY')
        WHEN payload ->> 'data_contabil' ~ '^\d{4}-\d{2}-\d{2}'
            THEN (payload ->> 'data_contabil')::timestamp::date
        ELSE NULL
    END AS datacontabil
    , TRIM(payload ->> 'titulo') AS titulo
    , TRIM(payload ->> 'descricao') AS descricao
    , replace(payload ->> 'entrada', ',', '.')::double precision AS entrada
    , replace(payload ->> 'saida', ',', '.')::double precision AS saida
    , replace(payload ->> 'saldo_do_dia', ',', '.')::double precision AS saldododia
    , now() AS datepartition
FROM raw.bank3
WHERE payload ->> 'data_lancamento' IS NOT NULL
  AND (
        payload ->> 'entrada' IS NOT NULL
        OR payload ->> 'saida' IS NOT NULL
  );
"""


bank1_cartoes = """
INSERT INTO silver.bank1_cartoes
    SELECT
	    'bank1' AS ds_banco
        , to_date(payload ->> 'data_transacao', 'DD/MM/YYYY') AS data_transacao
        , to_date(payload ->> 'dt_vencimento_fatura', 'DD/MM/YYYY') AS dt_vencimento_fatura
        , payload ->> 'portador' AS portador
        , payload ->> 'cartao' AS cartao
        , payload ->> 'descricao' AS descricao
        , replace(
            replace((payload -> 'valores_extraidos' ->> 0), '.', ''),
            ',', '.'
            )::numeric(12,2)
        AS valores_extraidos
        , now() AS datepartition
    FROM raw.bank1_cartao;
"""


bank2 = """
INSERT INTO silver.bank2

SELECT DISTINCT ON ((payload ->> 'stone_id')::double precision)
    payload ->> 'documento'                                                         AS documento
    , (payload ->> 'stonecode')::bigint                                             AS stonecode
    , payload ->> 'categoria'                                                       AS categoria
    , to_timestamp(payload ->> 'data_da_venda', 'DD/MM/YYYY HH24:MI:SS')            AS datavenda
    , to_date(payload ->> 'data_de_vencimento', 'DD/MM/YYYY')                       AS datavencimento
    , to_date(payload ->> 'data_de_vencimento_original', 'DD/MM/YYYY')              AS datavencimentooriginal
    , payload ->> 'bandeira'                                                        AS bandeira
    , payload ->> 'produto'                                                         AS produto
    , (payload ->> 'stone_id')::double precision                                    AS stoneid
    , (payload ->> 'qtd_de_parcelas')::integer                                      AS qtdparcelas
    , (payload ->> 'no_da_parcela')::integer                                        AS noparcela
    , replace(payload ->> 'valor_bruto', ',', '.')::double precision                AS valorbruto
    , replace(payload ->> 'valor_liquido', ',', '.')::double precision              AS valorliquido
    , replace(payload ->> 'desconto_de_mdr', ',', '.')::double precision            AS descontomdr
    , replace(payload ->> 'desconto_de_antecipacao', ',', '.')::double precision    AS descontoantecipacao
    , replace(payload ->> 'desconto_unificado', ',', '.')::double precision         AS descontounificado
    , payload ->> 'ultimo_status'                                                   AS ultimostatus
    , to_timestamp(payload ->> 'data_do_ultimo_status', 'DD/MM/YYYY HH24:MI:SS')    AS dataultimostatus
    , now()                                                                         AS datepartition
FROM raw.bank2

ORDER BY
    (payload ->> 'stone_id')::double precision
    , timestampextraction DESC
;
"""


laundry_system_lavanderias = """
INSERT INTO silver.laundry_system_lavanderias

SELECT DISTINCT ON ((payload ->> 'id'))
    (payload ->> 'id')::bigint                                      AS id
    , payload ->> 'nome'                                             AS nome
    , payload ->> 'empresa'                                          AS empresa
    , payload -> 'documentoEmpresa' ->> 'identificador'              AS cnpj
    , concat_ws(
        ' ',
        payload -> 'endereco' ->> 'logradouro',
        payload -> 'endereco' ->> 'numero',
        payload -> 'endereco' ->> 'complemento'
      )                                                              AS endereco
    , payload -> 'endereco' ->> 'nomeCidade'                         AS cidade
    , payload -> 'endereco' -> 'cidade' ->> 'uf'                     AS uf
    , now()                                                          AS datepartition
FROM raw.laundry_system
WHERE basename = 'lavanderias'

ORDER BY
      (payload ->> 'id')
    , timestampextraction DESC
"""


laundry_system_maquinas = """
INSERT INTO silver.laundry_system_maquinas

SELECT DISTINCT
    (payload ->> 'id')::bigint                  AS id
    , (payload ->> 'idLavanderia')::bigint       AS idlavanderia
    , payload ->> 'nome'                         AS nome
    , payload ->> 'tipo'                         AS tipo
    , now()                                      AS datepartition
FROM raw.laundry_system
WHERE basename = 'maquinas'

"""


laundry_system_clientes = """
INSERT INTO silver.laundry_system_clientes

SELECT DISTINCT ON ((payload ->> 'id'))
    (payload ->> 'id')::bigint AS id
    , (payload ->> 'cpf')::bigint AS cpf
    , payload ->> 'nome' AS nome
    , payload ->> 'email' AS email
    , payload ->> 'genero' AS genero
    , payload ->> 'telefone' AS telefone
    , (payload ->> 'dataCadastro')::timestamp AS datacadastro
    , (payload ->> 'primeiraCompra')::timestamp AS primeiracompra
    , (payload ->> 'ultimaCompra')::timestamp AS ultimacompra
    , (payload ->> 'dataNascimento')::timestamp AS datanascimento
    , now() AS datepartition
FROM raw.laundry_system
WHERE basename = 'clientes'

ORDER BY
      (payload ->> 'id')
    , (payload ->> 'ultimaCompra')::timestamp DESC
"""


laundry_system_vendas = """
INSERT INTO silver.laundry_system_vendas

SELECT
    (payload ->> 'idLavanderia')::int                         as idlavanderia
    , payload ->> 'lavanderia'                                as lavanderia
    , payload -> 'documentoEmpresa' ->> 'identificador'       as documentoempresa
    , (payload ->> 'idVenda')::bigint                         as idvenda
    , (payload ->> 'data')::timestamp - interval '3 hour'     as data
    , payload ->> 'status'                                    as status
    , payload ->> 'tipoPagamento'                             as tipopagamento
    , payload ->> 'codigoAutorizacaoEmissor'                  as codigoautorizacaoemissor
    , payload ->> 'codErro'                                   as coderro
    , payload ->> 'erro'                                      as erro
    , payload ->> 'cupom'                                     as cupom
    , payload ->> 'voucher'                                   as voucher
    , payload ->> 'nomeCategoriaVoucher'                      as nomecategoriavoucher
    , (payload ->> 'valor')::double precision                 as valor
    , (payload ->> 'valorSemDesconto')::double precision      as valorsemdesconto
    , payload ->> 'provedor'                                  as provedor
    , payload ->> 'adquirente'                                as adquirente
    , payload ->> 'bandeiraCartao'                            as bandeiracartao
    , payload ->> 'tipoCartao'                                as tipocartao
    , payload ->> 'requisicao'                                as requisicao
    , payload ->> 'cpfCliente'                                as cpfcliente
    , payload ->> 'nomeCliente'                               as nomecliente
    , payload ->> 'telefoneCliente'                           as telefonecliente
    , payload ->> 'emailCliente'                              as emailcliente
    , now()                                                   as datepartition
FROM raw.laundry_system
WHERE basename = 'vendas'
"""


laundry_system_ciclos = """
INSERT INTO silver.laundry_system_ciclos

WITH raw_vendas_deduplicada AS (

    SELECT
        r.id
        , r.basename
        , r.timestampextraction
        , r.payload
        , r.hashid
        , ROW_NUMBER() OVER (
            PARTITION BY
                r.payload ->> 'idVenda'
                , r.payload ->> 'data'
                , r.payload ->> 'requisicao'
                , r.payload ->> 'idLavanderia'
                , r.payload ->> 'valor'
            ORDER BY
                r.id
        ) AS rn
    FROM raw.laundry_system r
    WHERE 1=1
        AND r.basename = 'vendas'

)

SELECT
    (payload ->> 'idLavanderia')::int                       AS idlavanderia
    , payload ->> 'lavanderia'                              AS lavanderia
    , payload -> 'documentoEmpresa' ->> 'identificador'     AS documentoempresa
    , (payload ->> 'idVenda')::bigint                       AS idvenda
    , (payload ->> 'data')::timestamp - interval '3 hour'   AS data
    , payload ->> 'status'                                  AS status
    , payload ->> 'tipoPagamento'                           AS tipopagamento
    , payload ->> 'bandeiraCartao'                          AS bandeiracartao
    , payload ->> 'tipoCartao'                              AS tipocartao
    , payload ->> 'codigoAutorizacaoEmissor'                AS codigoautorizacaoemissor
    , payload ->> 'codErro'                                 AS coderro
    , payload ->> 'erro'                                    AS erro
    , (payload ->> 'valor')::double precision               AS valor
    , (payload ->> 'valorSemDesconto')::double precision    AS valorsemdesconto
    , item ->> 'maquina'                                    AS maquina
    , item ->> 'tipoServico'                                AS tiposervico
    , item ->> 'servico'                                    AS servico
    , payload ->> 'cpfCliente'                              AS cpfcliente
    , payload ->> 'nomeCliente'                             AS nomecliente
    , payload ->> 'telefoneCliente'                         AS telefonecliente
    , payload ->> 'emailCliente'                            AS emailcliente
    , now()                                                 AS datepartition
FROM raw_vendas_deduplicada

CROSS JOIN LATERAL jsonb_array_elements(payload -> 'pedido' -> 'itens') AS item

WHERE rn = 1
"""


#============ CONFIG
SILVER_LOAD_CONFIG = [
    {
        "name": "bank1",
        "table": "silver.bank1",
        "sql": bank1,
    },
    {
        "name": "bank1_cartoes",
        "table": "silver.bank1_cartoes",
        "sql": bank1_cartoes,
    },
    {
        "name": "bank2",
        "table": "silver.bank2",
        "sql": bank2,
    },
    {
        "name": "bank3",
        "table": "silver.bank3",
        "sql": bank3,
    },
    {
        "name": "laundry_system_lavanderias",
        "table": "silver.laundry_system_lavanderias",
        "sql": laundry_system_lavanderias,
    },
    {
        "name": "laundry_system_maquinas",
        "table": "silver.laundry_system_maquinas",
        "sql": laundry_system_maquinas,
    },
    {
        "name": "laundry_system_clientes",
        "table": "silver.laundry_system_clientes",
        "sql": laundry_system_clientes,
    },
    {
        "name": "laundry_system_vendas",
        "table": "silver.laundry_system_vendas",
        "sql": laundry_system_vendas,
    },
    {
        "name": "laundry_system_ciclos",
        "table": "silver.laundry_system_ciclos",
        "sql": laundry_system_ciclos,
    }
]


#================== ORCHESTRATOR
def execute_silver_load(engine: Engine, config: dict) -> None:
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {config['table']}"))
        conn.execute(text(config["sql"]))

    print(f"🟢 Carga da tabela {config['table']} concluída.")


#================== FINAL FUNCTION
def load_silver_layer(engine: Engine) -> None:
    ensure_silver_structure(engine)

    print("🚀 Iniciando carga da camada SILVER")

    for config in SILVER_LOAD_CONFIG:
        execute_silver_load(engine, config)

    print("✅ Carga da camada SILVER finalizada")
