"""
Módulo: rules_loader.py

Responsabilidade
----------------
Executar a carga das tabelas auxiliares do schema rules no PostgreSQL.

Contexto
--------
Este módulo faz parte da camada de persistência/regras do pacote
lavesecexpress_etl. Ele carrega no banco as regras financeiras usadas pela
camada Gold para categorizar transações de conta corrente e fatura de cartão.

Fontes das regras
-----------------
- gold_overridedata.py:
    fornece overrides manuais por cd_transacao.

- regex_bank1_rules.py:
    fornece padrões regex com prioridade e categoria.

- rules_detalhestransacoes.py:
    fornece categorias financeiras padronizadas e flags analíticas, incluindo a marcação de custo por ciclo.

Tabelas carregadas
------------------
- rules.ajustes_manuais_transacoes
- rules.regexpadrao_detalhes_transacoes
- rules.padronizacao_categorias_transacoes

Estratégia de carga
-------------------
Cada tabela é carregada com TRUNCATE + INSERT parametrizado. Isso faz com que
as tabelas rules reflitam integralmente as listas Python atuais a cada execução.

Principais componentes
----------------------
- execute_rules_load:
    executa uma carga individual com base na configuração recebida.

- load_rules_layer:
    garante a estrutura do schema rules e executa todas as cargas configuradas.

Observações
-----------
Este módulo deve ser executado antes da carga Gold quando houver dependência
das regras financeiras nas fatos analíticas.
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine
from lavesecexpress_etl.persistence.rules_structure import ensure_rules_structure
from lavesecexpress_etl.persistence.gold_overridedata import overrides
from lavesecexpress_etl.persistence.regex_bank1_rules import regex_rules
from lavesecexpress_etl.persistence.rules_detalhestransacoes import categorias
# ========== SQL CODES
ajustes_manuais_transacoes = """
    INSERT INTO rules.ajustes_manuais_transacoes (cd_transacao, texto_busca)
    VALUES (:cd_transacao, :texto_busca)
"""


regexpadrao_detalhes_transacoes = """
    INSERT INTO rules.regexpadrao_detalhes_transacoes (nr_prioridade, ds_regex, ds_categoria)
    VALUES (:nr_prioridade, :ds_regex, :ds_categoria)
"""


padronizacao_categorias_transacoes = """
INSERT INTO rules.padronizacao_categorias_transacoes
(cd_descricao, descricao, ds_tipodebito, fl_fixo, fl_operacional, fl_diluivel, fl_recorrente, fl_custociclo)
VALUES
(:cd_descricao,:descricao,:ds_tipodebito,:fl_fixo,:fl_operacional,:fl_diluivel,:fl_recorrente,:fl_custociclo)
"""


#============ CONFIG
RULES_LOAD_CONFIG = [
    {
        "name": "override",
        "type": "sql_with_params",
        "table": "rules.ajustes_manuais_transacoes",
        "sql": ajustes_manuais_transacoes,
        "data": [
            {"cd_transacao": cd, "texto_busca": txt}
            for cd, txt in overrides
        ]
    },
    {
        "name": "regex",
        "type": "sql_with_params",
        "table": "rules.regexpadrao_detalhes_transacoes",
        "sql": regexpadrao_detalhes_transacoes,
        "data": [
            {
                "nr_prioridade": prioridade,
                "ds_regex": regex,
                "ds_categoria": categoria
            }
            for prioridade, regex, categoria in regex_rules
        ]
    },
    {
        "name": "categorias",
        "type": "sql_with_params",
        "table": "rules.padronizacao_categorias_transacoes",
        "sql": padronizacao_categorias_transacoes,
        "data": [
            {
                "cd_descricao": rn,
                "descricao": d,
                "ds_tipodebito": t,
                "fl_fixo": gf,
                "fl_operacional": go,
                "fl_diluivel": gd,
                "fl_recorrente": gr,
                "fl_custociclo": gc
            }
            for rn, d, t, gf, go, gd, gr, gc in categorias
        ]
    }
]


#================== ORCHESTRATOR 
def execute_rules_load(engine: Engine, config: dict) -> None:

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
def load_rules_layer(engine: Engine) -> None:
    """
    Executa a carga completa do schema rules.

    A função garante que o schema rules e suas tabelas existam, depois percorre
    RULES_LOAD_CONFIG para carregar overrides manuais, regras regex e categorias
    padronizadas.

    Parameters
    ----------
    engine : Engine
        SQLAlchemy Engine conectado ao banco PostgreSQL.

    Returns
    -------
    None
        A função não retorna valor. Apenas executa a carga das tabelas rules.

    Notes
    -----
    - As tabelas são truncadas antes de cada carga.
    - As regras carregadas são usadas posteriormente pela camada Gold.
    - A fonte da verdade atual das regras está em arquivos Python do projeto.
    """
    
    ensure_rules_structure(engine)

    print("🚀 Iniciando carga da camada GOLD")

    for config in RULES_LOAD_CONFIG:
        execute_rules_load(engine, config)

    print("✅ Carga da camada GOLD finalizada")