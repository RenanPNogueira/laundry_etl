"""
Módulo: data_transformation.py

Responsabilidade
----------------
Executar o pipeline de transformação das camadas Silver, Rules e Gold do ETL
da lavanderia.

Contexto
--------
Este módulo faz parte da camada de pipelines do pacote lavesecexpress_etl.
Ele deve ser executado após as cargas RAW das fontes terem sido concluídas.

Fluxo executado
---------------
1. Cria uma conexão única com o banco PostgreSQL usando DB_CONFIG.
2. Executa a carga da camada Silver.
3. Executa a carga da camada Rules.
4. Executa a carga da camada Gold.

Ordem de execução
-----------------
A ordem é obrigatória:

    Silver → Rules → Gold

A Silver estrutura os dados brutos da RAW. A Rules carrega tabelas auxiliares
de categorização. A Gold consome Silver e Rules para montar dimensões e fatos
analíticos.

Observações
-----------
Este módulo não realiza extração de fontes externas e não carrega dados na
camada RAW. Ele atua apenas na transformação pós-ingestão.
"""

from lavesecexpress_etl.core.database.connection import get_engine
from lavesecexpress_etl.config.settings import DB_CONFIG

# Imports dos loaders
from lavesecexpress_etl.persistence.silver_loader import load_silver_layer
from lavesecexpress_etl.persistence.rules_loader import load_rules_layer
from lavesecexpress_etl.persistence.gold_loader import load_gold_layer


def run_pipeline():
    """
    Executa o pipeline completo de transformação pós-RAW.

    A função cria uma engine única de conexão com o PostgreSQL e executa as
    cargas Silver, Rules e Gold em ordem controlada.

    Returns
    -------
    None
        A função não retorna valor. Ela executa as cargas de transformação e
        imprime mensagens de acompanhamento.

    Raises
    ------
    Exception
        Qualquer erro ocorrido nas cargas é impresso e relançado para o
        processo chamador.

    Notes
    -----
    - As configurações de banco vêm de DB_CONFIG.
    - A ordem Silver → Rules → Gold deve ser preservada.
    - A função não executa ingestões RAW.
    """
    print("🚀 Iniciando pipeline ETL da lavanderia...")

    # 🔌 Conexão única (evita recriar engine 3x)
    engine = get_engine(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        db_name=DB_CONFIG["db_name"]
    )

    try:
        # Ordem importa
        print("🟡 Camada SILVER...")
        load_silver_layer(engine)

        print("🟡 Camada RULES...")
        load_rules_layer(engine)

        print("🟡 Camada GOLD...")
        load_gold_layer(engine)

        print("✅ Pipeline finalizado com sucesso!")

    except Exception as e:
        print("❌ Erro no pipeline:", str(e))
        raise


if __name__ == "__main__":
    run_pipeline()