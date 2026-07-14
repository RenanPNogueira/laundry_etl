"""
Módulo: gold_structure.py

Responsabilidade
----------------
Garantir a existência do schema gold e das tabelas analíticas da camada Gold
do ETL da lavanderia.

Contexto
--------
Este módulo faz parte da camada de persistência do pacote lavesecexpress_etl.
Ele define os DDLs das dimensões e fatos usadas para consumo analítico,
especialmente em dashboards financeiros e operacionais.

Estratégia Gold
---------------
A camada Gold representa a camada final de modelagem analítica. Ela organiza
os dados em dimensões e fatos, consolidando informações financeiras,
operacionais e comerciais da lavanderia.

Tabelas criadas
---------------
Dimensões:
- gold.d_bancos
- gold.d_lavanderias
- gold.d_clientes
- gold.d_maquinas
- gold.d_falhas
- gold.d_metodopagamento
- gold.d_voucher
- gold.d_cupom

Fatos:
- gold.f_contacorrente
- gold.f_faturacartao
- gold.f_vendas
- gold.f_ciclos

Principais componentes
----------------------
- ensure_gold_structure:
    cria o schema gold, caso não exista, e executa os DDLs de criação das
    tabelas analíticas do projeto.

Observações
-----------
Este módulo não carrega dados. Ele apenas prepara a estrutura física da camada
Gold no PostgreSQL. A carga dos dados é realizada pelo módulo gold_loader.py.
"""

from sqlalchemy.engine import Engine
from lavesecexpress_etl.core.database.create_schema import create_schema_if_not_exists
from lavesecexpress_etl.core.database.create_table import create_table_from_ddl


# ================= SCHEMA NAME
GOLDE_SCHEMA = "gold"


# ================= TABLE STRUCTURE
d_bancos = """
CREATE TABLE IF NOT EXISTS gold.d_bancos (
    cd_banco INT PRIMARY KEY,
    ds_banco TEXT NOT NULL
);
"""


f_contacorrente = """
CREATE TABLE IF NOT EXISTS gold.f_contacorrente (
    cd_transacao TEXT NOT NULL,
    cd_banco INTEGER NOT NULL, 
    dt_transacao DATE NOT NULL,
    fl_debito BOOLEAN,
    cd_detalhetransacao INTEGER,
    vl_transacao NUMERIC(14,2)
);
"""


f_faturacartao = """
CREATE TABLE IF NOT EXISTS gold.f_faturacartao (
    cd_transacao TEXT NOT NULL
    , cd_banco INTEGER NOT NULL
	, ds_portador TEXT NOT NULL
	, nr_cartao INTEGER
	, dt_transacao DATE NOT NULL 
	, dt_fatura DATE NOT NULL
	, fl_parcelado BOOLEAN
	, nr_parcela INTEGER
	, nr_totalparcelas INTEGER
	, fl_debito BOOLEAN
	, cd_detalhetransacao INTEGER
	, vl_transacao DOUBLE PRECISION
);
""" 


d_lavanderias = """ 
CREATE TABLE IF NOT EXISTS gold.d_lavanderias (
    cd_lavanderia BIGINT PRIMARY KEY
	, ds_lavanderia TEXT
	, cd_cnpj TEXT
);
"""


d_clientes =  """ 
CREATE TABLE IF NOT EXISTS gold.d_clientes (
    nr_cpfcliente BIGINT PRIMARY KEY
	, ds_nome TEXT
	, ds_email TEXT
    , ds_genero TEXT
    , ds_telefone TEXT
    , dt_nascimento DATE
    , dt_cadastro DATE
    , datepartition TIMESTAMP
);
"""


d_maquinas = """
CREATE TABLE IF NOT EXISTS gold.d_maquinas (
    cd_maquina BIGINT PRIMARY KEY
    , cd_lavanderia BIGINT
    , ds_maquina TEXT
    , ds_servico TEXT
);
"""


d_falhas =  """
CREATE TABLE IF NOT EXISTS gold.d_falhas (
    cd_erro INT PRIMARY KEY
    , cd_erroapi INT
    , ds_erro TEXT
);
"""


d_metodopagamento =  """
CREATE TABLE IF NOT EXISTS gold.d_metodopagamento (
    cd_modalidadepagamento INT
    , ds_tipo TEXT
    , ds_bandeiracartao TEXT
    , ds_tipopagamento TEXT
);
"""


d_voucher =  """
CREATE TABLE IF NOT EXISTS gold.d_voucher (
    cd_voucher TEXT PRIMARY KEY
    , ds_nome TEXT
);
"""


d_cupom =  """
CREATE TABLE IF NOT EXISTS gold.d_cupom (
    cd_cupom INT PRIMARY KEY
    , ds_cupom TEXT 
);
"""


f_vendas =  """
CREATE TABLE IF NOT EXISTS gold.f_vendas (
    dh_venda                     TIMESTAMP
    , dt_compensacaopagamento    DATE
    , ds_statuspagamento         TEXT
    , cd_venda                   BIGINT
    , cd_lavanderia              INT
    , fl_status                  BOOLEAN
    , nr_cpfcliente              BIGINT
    , cd_modalidadepagamento     INT
    , cd_erro                    INT
    , cd_cupom                   INT
    , cd_voucher                 TEXT
    , vl_bruto                   DOUBLE PRECISION
    , vl_custooperacional        DOUBLE PRECISION
    , vl_brutosemdesconto        DOUBLE PRECISION
    , vl_liquido                 DOUBLE PRECISION
    , dt_partition               TIMESTAMP
);
"""


f_ciclos =  """
CREATE TABLE IF NOT EXISTS gold.f_ciclos (
    dh_ciclo                 TIMESTAMP
    , cd_venda               BIGINT
    , cd_lavanderia          INT
    , cd_maquina             INT
    , fl_status              BOOLEAN
    , cd_erro                INT
    , cd_modalidadepagamento INT
    , nr_cpfcliente          BIGINT
);
"""


#============== MAP TABLES
GOLD_TABLES = [
    {"name": "d_bancos", "ddl": d_bancos},
    {"name": "f_contacorrente", "ddl": f_contacorrente},
    {"name": "f_faturacartao", "ddl": f_faturacartao},
    {"name": "d_lavanderias", "ddl": d_lavanderias},
    {"name": "d_clientes", "ddl": d_clientes},
    {"name": "d_maquinas", "ddl": d_maquinas},
    {"name": "d_falhas", "ddl": d_falhas},
    {"name": "d_metodopagamento", "ddl": d_metodopagamento},
    {"name": "d_voucher", "ddl": d_voucher},
    {"name": "d_cupom", "ddl": d_cupom},
    {"name": "f_vendas", "ddl": f_vendas},
    {"name": "f_ciclos", "ddl": f_ciclos},
]


#============== FINAL FUNCTION
def ensure_gold_structure(engine: Engine) -> None:
    """
    Garante a existência do schema gold e das tabelas Gold do projeto.

    A função cria o schema gold, caso ele ainda não exista, e executa os DDLs
    necessários para criar dimensões e fatos da camada analítica.

    Parameters
    ----------
    engine : Engine
        SQLAlchemy Engine conectado ao banco PostgreSQL.

    Returns
    -------
    None
        A função não retorna valor. Apenas executa comandos DDL no banco.

    Notes
    -----
    - As tabelas são criadas com CREATE TABLE IF NOT EXISTS.
    - A função não executa migrações em tabelas já existentes.
    - A carga dos dados é responsabilidade do gold_loader.py.
    """
    create_schema_if_not_exists(engine, GOLDE_SCHEMA)

    for table in GOLD_TABLES:
        create_table_from_ddl(engine, table["ddl"])
        print(f"🟢 Tabela gold.{table['name']} pronta.")