"""
Módulo: runner.py

Responsabilidade
----------------
Orquestrar a extração completa da integração com o sistema da lavanderia em
memória.

Contexto
--------
Este módulo faz parte da integração com o sistema da lavanderia do pacote
lavesecexpress_etl. Ele utiliza o cliente de API definido em api_client.py
para coletar vendas, máquinas, lavanderias e clientes, consolidando os
resultados em um único dicionário.

Papel no fluxo do sistema da lavanderia
----------------------------------------
- api_timestamp.py:
    calcula as janelas de timestamps que serão usadas para vendas.

- api_client.py:
    executa as chamadas HTTP aos endpoints do sistema da lavanderia.

- runner.py:
    coordena as chamadas por entidade e retorna os dados brutos em memória.

- pipeline:
    consome o retorno do runner e decide como transformar ou persistir os
    dados.

Principais componentes
----------------------
- run_laundry_system_extraction:
    Executa a extração do sistema da lavanderia a partir das janelas de
    timestamp, api_key e CNPJ informados.

Observações
-----------
Este módulo não realiza transformação, limpeza, persistência ou logging manual.
Seu papel é apenas orquestrar chamadas de API e consolidar resultados.
"""

from typing import Dict, Any

from lavesecexpress_etl.sources.laundry_system.api_client import (
    fetch_vendas,
    fetch_maquinas,
    fetch_lavanderias,
    fetch_clientes,
)


def run_laundry_system_extraction(
    datas: dict,
    api_key: str,
    cnpj: str,
) -> Dict[str, Any]:
    """
    Executa a extração completa do sistema da lavanderia em memória.

    A função recebe as janelas de timestamp previamente calculadas, executa a
    coleta de vendas para cada janela e, em seguida, coleta as demais entidades
    cadastrais do sistema da lavanderia.

    Parameters
    ----------
    datas : dict
        Dicionário contendo a chave `timestamp_windows`. Cada item dessa lista
        deve possuir `start_timestamp` e `end_timestamp`.

    api_key : str
        Chave de autenticação da API do sistema da lavanderia.

    cnpj : str
        CNPJ usado como filtro nos endpoints que exigem esse parâmetro.

    Returns
    -------
    dict
        Dicionário contendo:
        - status;
        - vendas;
        - maquinas;
        - lavanderias;
        - clientes;
        - metadata com contagem de registros por entidade.

    Raises
    ------
    RuntimeError
        Quando api_key ou cnpj não são informados.

    Notes
    -----
    - Vendas são extraídas por janela de timestamp.
    - Máquinas, lavanderias e clientes são extraídos uma vez por execução.
    - A função retorna os dados em memória e não realiza persistência.
    """

    if not api_key:
        raise RuntimeError("API_KEY não informado.")

    if not cnpj:
        raise RuntimeError("CNPJ não informado.")

    timestamp_windows = datas.get("timestamp_windows", [])

    if not timestamp_windows:
        return {
            "status": "no_data",
            "vendas": [],
            "maquinas": [],
            "lavanderias": [],
            "clientes": [],
            "metadata": {},
        }

    # ==========================================================
    # VENDAS (por janela de timestamp)
    # ==========================================================
    vendas_consolidado = []

    for janela in timestamp_windows:

        start_timestamp = janela["start_timestamp"]
        end_timestamp = janela["end_timestamp"]

        vendas = fetch_vendas(
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            api_key=api_key,
            cnpj=cnpj,
        )

        vendas_consolidado.extend(vendas)

    # ==========================================================
    # DEMAIS ENDPOINTS
    # ==========================================================
    maquinas = fetch_maquinas(
        api_key=api_key,
        cnpj=cnpj,
    )

    lavanderias = fetch_lavanderias(
        api_key=api_key,
        cnpj=cnpj,
    )

    clientes = fetch_clientes(
        api_key=api_key,
    )

    return {
        "status": "success",
        "vendas": vendas_consolidado,
        "maquinas": maquinas,
        "lavanderias": lavanderias,
        "clientes": clientes,
        "metadata": {
            "vendas_total": len(vendas_consolidado),
            "maquinas_total": len(maquinas),
            "lavanderias_total": len(lavanderias),
            "clientes_total": len(clientes),
        }
    }
