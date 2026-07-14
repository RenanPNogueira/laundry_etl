"""
Módulo: api_timestamp.py

Responsabilidade
----------------
Definir a estratégia de timestamps para extrações da API do sistema da
lavanderia.

Contexto
--------
Este módulo faz parte da integração com o sistema da lavanderia e centraliza
o cálculo das janelas temporais usadas nas chamadas à API. Ele suporta carga
histórica inicial (foundation) e carga incremental.

Modos suportados
----------------
- foundation:
    Utiliza timestamps fixos de início e fim, definidos por
    FOUNDATION_START_TIMESTAMP e BASELINE_END_TIMESTAMP.

- incremental:
    Consulta a maior data já carregada em raw.laundry_system para basename='vendas',
    aplica uma pequena margem de segurança para trás e extrai até o horário
    atual em UTC.

Principais componentes
----------------------
- generate_timestamp_windows:
    Quebra um intervalo ISO em janelas menores.

- get_foundation_timestamps:
    Retorna as janelas de extração para carga histórica inicial.

- get_incremental_timestamps:
    Retorna as janelas de extração incremental com base na maior data já
    carregada no banco.

- set_extraction_timestamps:
    Interface pública para obter os timestamps conforme o modo informado.

Observações
-----------
Este módulo não executa chamadas à API. Ele apenas calcula os intervalos que
serão usados por outros componentes da integração com o sistema da lavanderia.
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy import text

MAX_VM_WINDOW_DAYS = 90

FOUNDATION_START_TIMESTAMP = "2024-04-01T00:00:00Z"
BASELINE_END_TIMESTAMP = "2025-12-31T23:59:59Z"


def generate_timestamp_windows(start_iso: str, end_iso: str):
    """
    Gera janelas de timestamps entre um início e fim informados.

    A função divide o intervalo total em blocos de até MAX_VM_WINDOW_DAYS.
    Cada janela contém um timestamp inicial e um timestamp final, ambos em
    formato ISO com sufixo Z.

    Parameters
    ----------
    start_iso : str
        Timestamp inicial no formato ISO, com sufixo Z.

    end_iso : str
        Timestamp final no formato ISO, com sufixo Z.

    Returns
    -------
    list[dict]
        Lista de janelas contendo start_timestamp e end_timestamp.
    """
    start_dt = datetime.fromisoformat(start_iso.replace("Z", ""))
    end_dt = datetime.fromisoformat(end_iso.replace("Z", ""))

    windows = []
    current_start = start_dt

    while current_start <= end_dt:

        current_end = min(
            current_start + timedelta(days=MAX_VM_WINDOW_DAYS - 1),
            end_dt
        )

        windows.append({
            "start_timestamp": current_start.isoformat() + "Z",
            "end_timestamp": current_end.replace(
                hour=23,
                minute=59,
                second=59,
                microsecond=999999
            ).isoformat() + "Z"
        })

        current_start = current_end + timedelta(seconds=1)

    return windows


def get_foundation_timestamps():

    windows = generate_timestamp_windows(
        FOUNDATION_START_TIMESTAMP,
        BASELINE_END_TIMESTAMP
    )

    return {
        "start_timestamp_real": FOUNDATION_START_TIMESTAMP,
        "end_timestamp_real": BASELINE_END_TIMESTAMP,
        "timestamp_windows": windows
    }


def get_incremental_timestamps(engine):
    """
    Calcula as janelas incrementais de extração do sistema da lavanderia.

    A função consulta a maior data já carregada na tabela raw.laundry_system para
    registros com basename='vendas'. Quando essa data existe, o início da nova
    extração é calculado voltando 5 segundos a partir dela. Quando não existe,
    a extração volta para FOUNDATION_START_TIMESTAMP.

    Parameters
    ----------
    engine
        SQLAlchemy Engine usado para consultar o banco PostgreSQL.

    Returns
    -------
    dict
        Dicionário contendo timestamp inicial real, timestamp final real e
        lista de janelas de extração.
    """
    try:

        query = text("""
            SELECT
                MAX((payload ->> 'data')::timestamp)
            FROM raw.laundry_system
            WHERE basename = 'vendas'
        """)

        with engine.connect() as conn:
            data_max = conn.execute(query).scalar()

        print("DEBUG data_max:", data_max)

    except Exception:
        data_max = None

    if not data_max:

        start_iso = FOUNDATION_START_TIMESTAMP

    else:
        start_dt = data_max - timedelta(seconds=5)
        start_iso = start_dt.isoformat() + "Z"

    end_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    windows = generate_timestamp_windows(
        start_iso,
        end_iso
    )

    return {
        "start_timestamp_real": start_iso,
        "end_timestamp_real": end_iso,
        "timestamp_windows": windows
    }


# PUBLIC INTERFACE
def set_extraction_timestamps(mode: str = "foundation", engine=None):

    mode = mode.lower().strip()

    if mode == "foundation":
        return get_foundation_timestamps()

    if mode == "incremental":

        if engine is None:
            raise ValueError(
                "Engine required for incremental mode"
            )

        return get_incremental_timestamps(engine)

    raise ValueError(
        "Mode must be 'foundation' or 'incremental'"
    )