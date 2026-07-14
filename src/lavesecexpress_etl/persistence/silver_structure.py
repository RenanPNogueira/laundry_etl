"""
Módulo: silver_structure.py

Responsabilidade
----------------
Garantir a existência do schema silver e das tabelas relacionais necessárias
para a camada Silver do ETL da lavanderia.

Contexto
--------
Este módulo faz parte da camada de persistência do pacote lavesecexpress_etl.
Ele centraliza os DDLs das tabelas Silver, que recebem dados já extraídos e
transformados a partir da camada RAW.

Estratégia Silver
-----------------
A camada Silver possui tabelas tipadas e mais estruturadas do que a camada RAW.
Enquanto a RAW preserva os registros como payload JSONB, a Silver organiza os
dados em colunas relacionais, com tipos definidos para datas, textos, valores
numéricos e timestamps.

Tabelas criadas
---------------
- silver.bank1
- silver.bank3
- silver.bank1_cartoes
- silver.bank2
- silver.laundry_system_lavanderias
- silver.laundry_system_maquinas
- silver.laundry_system_clientes
- silver.laundry_system_vendas
- silver.laundry_system_ciclos

Principais componentes
----------------------
- ensure_silver_structure:
    cria o schema silver, caso não exista, e executa os DDLs de criação das
    tabelas Silver do projeto.

Observações
-----------
Este módulo não transforma nem carrega dados. Ele apenas prepara a estrutura
física da camada Silver no PostgreSQL.
"""

from sqlalchemy.engine import Engine
from lavesecexpress_etl.core.database.create_schema import create_schema_if_not_exists
from lavesecexpress_etl.core.database.create_table import create_table_from_ddl

# ================= SCHEMA NAME
SILVER_SCHEMA = "silver"


# ================= TABLE STRUCTURE
bank1 = """
CREATE TABLE IF NOT EXISTS silver.bank1 (
    ds_banco          text
    , datatransacao   date
    , documento       text
    , historico       text
    , debito          double precision
    , credito         double precision
    , saldo           double precision
    , descricao       text
    , datepartition   timestamp
);
"""


bank3 =  """
CREATE TABLE IF NOT EXISTS silver.bank3 (
    ds_banco             text
    , datatransacao        date
    , datacontabil       date
    , titulo             text
    , descricao          text
    , entrada            double precision
    , saida              double precision
    , saldo_do_dia       double precision
    , datepartition      timestamp
)
"""


bank1_cartoes =  """
CREATE TABLE IF NOT EXISTS silver.bank1_cartoes (
    ds_banco               text,
    data_transacao         date,
    dt_vencimento_fatura   date,
    portador               text,
    cartao                 text,
    descricao              text,
    valores_extraidos      numeric(12,2),
    datepartition          timestamp default now()
);
"""


bank2 = """
CREATE TABLE IF NOT EXISTS silver.bank2 (
    documento                    text
    , stonecode                  bigint
    , categoria                  text
    , datavenda                  timestamp
    , datavencimento             date
    , datavencimentooriginal     date
    , bandeira                   text
    , produto                    text
    , stoneid                    double precision
    , qtdparcelas                integer
    , noparcela                  integer
    , valorbruto                 double precision
    , valorliquido               double precision
    , descontomdr                double precision
    , descontoantecipacao        double precision
    , descontounificado          double precision
    , ultimostatus               text
    , dataultimostatus           timestamp
    , datepartition              timestamp
)
"""


laundry_system_lavanderias = """
CREATE TABLE IF NOT EXISTS silver.laundry_system_lavanderias (
    id                 bigint
    , nome             text
    , empresa          text
    , cnpj             text
    , endereco         text
    , cidade           text
    , uf               text
    , datepartition   timestamp
);
"""


laundry_system_maquinas = """
CREATE TABLE IF NOT EXISTS silver.laundry_system_maquinas (
    id               bigint
    , idlavanderia   bigint
    , nome           text
    , tipo           text
    , datepartition  timestamp
);
"""


laundry_system_clientes = """
CREATE TABLE IF NOT EXISTS silver.laundry_system_clientes (
    id                bigint
    , cpf             bigint
    , nome            text
    , email           text
    , genero          text
    , telefone        text
    , datacadastro    timestamp
    , primeiracompra  timestamp
    , ultimacompra    timestamp
    , datanascimento  timestamp
    , datepartition   timestamp
);
"""


laundry_system_vendas =  """
CREATE TABLE IF NOT EXISTS silver.laundry_system_vendas (
    idlavanderia                 int
    , lavanderia                 text
    , documentoempresa           text
    , idvenda                    bigint
    , data                       timestamp
    , status                     text
    , tipopagamento              text
    , codigoautorizacaoemissor   text
    , coderro                    text
    , erro                       text
    , cupom                      text
    , voucher                    text
    , nomecategoriavoucher       text
    , valor                      double precision
    , valorsemdesconto           double precision
    , provedor                   text
    , adquirente                 text
    , bandeiracartao             text
    , tipocartao                 text
    , requisicao                 text
    , cpfcliente                 text
    , nomecliente                text
    , telefonecliente            text
    , emailcliente               text
    , datepartition              timestamp
)
"""


laundry_system_ciclos = """
CREATE TABLE IF NOT EXISTS silver.laundry_system_ciclos (
    idlavanderia                 int
    , lavanderia                 text
    , documentoempresa           text
    , idvenda                    bigint
    , data                       timestamp
    , status                     text
    , tipopagamento              text
    , bandeiracartao             text
    , tipocartao                 text
    , codigoautorizacaoemissor   text
    , coderro                    text
    , erro                       text
    , valor                      double precision
    , valorsemdesconto           double precision
    , maquina                    text
    , tiposervico                text
    , servico                    text
    , cpfcliente                 text
    , nomecliente                text
    , telefonecliente            text
    , emailcliente               text
    , datepartition              timestamp
);
"""


#============== MAP TABLES
SILVER_TABLES = [
    {"name": "bank1", "ddl": bank1},
    {"name": "bank3", "ddl": bank3},
    {"name": "bank1_cartoes", "ddl": bank1_cartoes},
    {"name": "bank2", "ddl": bank2},
    {"name": "laundry_system_lavanderias", "ddl": laundry_system_lavanderias},
    {"name": "laundry_system_maquinas", "ddl": laundry_system_maquinas},
    {"name": "laundry_system_clientes", "ddl": laundry_system_clientes},
    {"name": "laundry_system_vendas", "ddl": laundry_system_vendas},
    {"name": "laundry_system_ciclos", "ddl": laundry_system_ciclos},
]


#============== FINAL FUNCTION
def ensure_silver_structure(engine: Engine) -> None:
    """
    Garante a existência do schema silver e das tabelas Silver do projeto.

    A função cria o schema silver, caso ele ainda não exista, e executa os DDLs
    de criação das tabelas relacionais usadas pela camada Silver do ETL.

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
    - A camada Silver contém dados estruturados e tipados, derivados da RAW.
    """
    create_schema_if_not_exists(engine, SILVER_SCHEMA)

    for table in SILVER_TABLES:
        create_table_from_ddl(engine, table["ddl"])
        print(f"🟢 Tabela silver.{table['name']} pronta.")
