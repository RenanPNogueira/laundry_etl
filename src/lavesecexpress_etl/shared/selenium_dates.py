"""
Módulo: selenium_dates.py

Responsabilidade
----------------
Definir a estratégia de datas para extrações realizadas via Selenium no
ETL da lavanderia.

Contexto
--------
Este módulo faz parte da camada shared do pacote lavesecexpress_etl. Ele
centraliza regras compartilhadas de janelas de extração para fontes que
dependem de automação via navegador, como Banco 1 e Banco 2.

Modos suportados
----------------
- foundation:
    Utilizado para carga histórica inicial. Cada fonte utiliza sua data inicial
    histórica configurada e extrai dados até BASELINE_END_DATE.

- incremental:
    Utilizado para cargas recorrentes. A data inicial é calculada com base na
    maior data já existente na camada raw, podendo aplicar margens para trás
    ou para frente conforme a fonte.

Fontes configuradas
-------------------
- bank1:
    Fonte de conta corrente. Usa a maior data do payload raw.bank1 como
    referência incremental.

- bank2:
    Fonte de recebimentos. Usa a maior data de vencimento do payload raw.bank2
    como referência incremental.

Principais componentes
----------------------
- generate_date_windows:
    Quebra um intervalo de datas em janelas menores.

- get_foundation_dates:
    Retorna as janelas de extração para carga histórica inicial.

- get_incremental_dates:
    Retorna as janelas de extração incremental consultando a maior data
    existente no banco.

- set_extraction_dates:
    Interface pública para escolher a estratégia de datas com base no modo
    informado.

Observações
-----------
Este módulo não executa a extração Selenium. Ele apenas calcula os períodos
que serão usados por outros componentes do pipeline.
"""

from datetime import date, timedelta
from typing import Dict, List, Optional

# GLOBAL CONFIGURATION
BASELINE_END_DATE = date(2025, 12, 31)
DEFAULT_SELENIUM_INTERVAL_DAYS = 150

SELENIUM_SOURCES = {
    "bank1": {
        "table_name": "bank1_contacorrente",
        "foundation_start_date": date(2023, 12, 14),
        "incremental_forward_days": 2,
        "max_date_query": """
            SELECT MAX(
                to_date(payload ->> 'data', 'DD/MM/YYYY')
            )
            FROM raw.bank1
        """,
    },
    "bank2": {
        "table_name": "bank2_recebimentos",
        "foundation_start_date": date(2024, 3, 27),
        "incremental_back_days": 60,
        "incremental_forward_days": 90,
        "max_date_query": """
            SELECT MAX(
                to_date(payload ->> 'data_de_vencimento', 'DD/MM/YYYY')
            )
            FROM raw.bank2
        """,
    }
}


# UTIL — DATE WINDOW GENERATOR
def generate_date_windows(
    start_date: date,
    end_date: date,
    interval_days: int
) -> List[Dict]:

    windows = []
    current_start = start_date

    while current_start <= end_date:
        current_end = min(
            current_start + timedelta(days=interval_days - 1),
            end_date
        )

        windows.append({
            "start_date": current_start,
            "end_date": current_end
        })

        current_start = current_end + timedelta(days=1)

    return windows


# FOUNDATION
def get_foundation_dates() -> Dict:

    result = {}

    for source, config in SELENIUM_SOURCES.items():

        start_date = config["foundation_start_date"]
        end_date = BASELINE_END_DATE

        windows = generate_date_windows(
            start_date,
            end_date,
            DEFAULT_SELENIUM_INTERVAL_DAYS
        )

        result[source] = {
            "start_date": start_date,
            "end_date": end_date,
            "extractions_count": len(windows),
            "date_windows": windows,
            "interval_days": DEFAULT_SELENIUM_INTERVAL_DAYS
        }

    return result


# INCREMENTAL
def get_incremental_dates(engine) -> Dict:

    from sqlalchemy import text

    today = date.today()
    result = {}

    for source, config in SELENIUM_SOURCES.items():

        table_name = config["table_name"]

        try:

            query = text(config["max_date_query"])

            with engine.connect() as conn:
                data_max = conn.execute(query).scalar()

        except Exception:

            data_max = None

        if not data_max:
            start_date = config["foundation_start_date"]
        else:
            back_days = config.get("incremental_back_days", 0)
            start_date = data_max - timedelta(days=back_days)

        forward_days = config.get("incremental_forward_days", 0)
        end_date = today + timedelta(days=forward_days)

        windows = generate_date_windows(
            start_date,
            end_date,
            DEFAULT_SELENIUM_INTERVAL_DAYS
        )

        result[source] = {
            "start_date": start_date,
            "end_date": end_date,
            "extractions_count": len(windows),
            "date_windows": windows,
            "interval_days": DEFAULT_SELENIUM_INTERVAL_DAYS
        }

    return result


# PUBLIC INTERFACE
def set_extraction_dates(
    mode: str = "foundation",
    engine=None
) -> Dict:

    mode = mode.lower().strip()

    if mode == "foundation":
        return get_foundation_dates()

    if mode == "incremental":

        if engine is None:
            raise ValueError(
                "[set_extraction_dates] Engine is required for incremental mode."
            )

        return get_incremental_dates(engine)

    raise ValueError(
        f"[set_extraction_dates] Invalid mode '{mode}'. Use 'foundation' or 'incremental'."
    )