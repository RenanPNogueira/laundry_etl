"""
Módulo: rules_structure.py

Responsabilidade
----------------
Garantir a existência do schema rules e das tabelas auxiliares de regras de
negócio usadas pelo ETL da lavanderia.

Contexto
--------
Este módulo faz parte da camada de persistência do pacote lavesecexpress_etl.
Ele define estruturas de banco utilizadas para armazenar ajustes manuais,
padrões regex e padronizações finais de categorias financeiras.

Estratégia do schema rules
--------------------------
O schema rules separa as regras de classificação financeira das tabelas finais
da camada Gold. Essas regras são usadas principalmente para categorizar
transações de conta corrente e fatura de cartão.

Tabelas criadas
---------------
- rules.ajustes_manuais_transacoes:
    armazena overrides manuais por cd_transacao.

- rules.regexpadrao_detalhes_transacoes:
    armazena padrões regex com prioridade e categoria.

- rules.padronizacao_categorias_transacoes:
    armazena categorias finais e atributos analíticos, como flags de gasto
    fixo, operacional, diluível, recorrente e custo por ciclo.

Principais componentes
----------------------
- ensure_rules_structure:
    cria o schema rules, caso não exista, e executa os DDLs de criação das
    tabelas auxiliares de regras.

Observações
-----------
Este módulo não insere dados nas tabelas e não aplica as regras diretamente.
Ele apenas prepara a estrutura física usada pelas cargas posteriores.
"""

from sqlalchemy.engine import Engine
from lavesecexpress_etl.core.database.create_schema import create_schema_if_not_exists
from lavesecexpress_etl.core.database.create_table import create_table_from_ddl
# ================= SCHEMA NAME
RULES_SCHEMA = "rules"


# ================= TABLE STRUCTURE
ajustes_manuais_transacoes = """
CREATE TABLE IF NOT EXISTS rules.ajustes_manuais_transacoes (
    cd_transacao TEXT PRIMARY KEY,
    texto_busca TEXT
);
"""


regexpadrao_detalhes_transacoes = """
CREATE TABLE IF NOT EXISTS rules.regexpadrao_detalhes_transacoes (
    nr_prioridade   integer
    , ds_regex      text
    , ds_categoria  text
);
"""


padronizacao_categorias_transacoes = """
CREATE TABLE IF NOT EXISTS rules.padronizacao_categorias_transacoes (
    cd_descricao INTEGER PRIMARY KEY
    , descricao TEXT     
    , ds_tipodebito TEXT    
    , fl_fixo BOOLEAN   
    , fl_operacional BOOLEAN    
    , fl_diluivel BOOLEAN   
    , fl_recorrente BOOLEAN
    , fl_custociclo BOOLEAN
);
"""


padronizacao_categorias_transacoes_add_fl_custociclo = """
ALTER TABLE rules.padronizacao_categorias_transacoes
ADD COLUMN IF NOT EXISTS fl_custociclo BOOLEAN;
"""



#============== MAP TABLES
rules_TABLES = [
    {"name": "ajustes_manuais_transacoes", "ddl": ajustes_manuais_transacoes},
    {"name": "regexpadrao_detalhes_transacoes", "ddl": regexpadrao_detalhes_transacoes},
    {"name": "padronizacao_categorias_transacoes", "ddl": padronizacao_categorias_transacoes},
    {"name": "padronizacao_categorias_transacoes_add_fl_custociclo", "ddl": padronizacao_categorias_transacoes_add_fl_custociclo},
]


#============== FINAL FUNCTION
def ensure_rules_structure(engine: Engine) -> None:
    """
    Garante a existência do schema rules e das tabelas auxiliares de regras.

    A função cria o schema rules, caso ainda não exista, e executa os DDLs
    necessários para armazenar ajustes manuais, regras regex e padronizações
    de categorias financeiras.

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
    - Migrações simples são executadas com ALTER TABLE ... ADD COLUMN IF NOT EXISTS.
    - O schema rules é consumido principalmente pela carga da camada Gold.
    """
    create_schema_if_not_exists(engine, RULES_SCHEMA)

    for table in rules_TABLES:
        create_table_from_ddl(engine, table["ddl"])
        print(f"🟢 Tabela rules.{table['name']} pronta.")