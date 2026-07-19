"""
Módulo: api_client.py

Responsabilidade
----------------
Centralizar as chamadas HTTP para a API externa do sistema da lavanderia.

Contexto
--------
Este módulo faz parte da integração com o sistema da lavanderia do pacote
lavesecexpress_etl. Ele contém funções responsáveis por consultar endpoints
da API e retornar os registros brutos recebidos, sem aplicar transformação
ou persistência.

Endpoints consumidos
--------------------
- vendas
- maquinas
- lavanderias
- clientes

Principais componentes
----------------------
- _fetch_paginated:
    Helper interno para endpoints com paginação baseada em página e quantidade.

- fetch_vendas:
    Coleta vendas em uma janela de timestamps.

- fetch_maquinas:
    Coleta máquinas associadas ao CNPJ informado.

- fetch_lavanderias:
    Coleta dados de lavanderias associadas ao CNPJ informado.

- fetch_clientes:
    Coleta clientes da base do sistema da lavanderia, ordenados por data de
    cadastro.

Observações
-----------
Este módulo não calcula janelas de extração e não grava dados no banco.
A definição de períodos deve ser feita por api_timestamp.py, enquanto a
persistência deve ser feita pelos pipelines ou módulos de carga.
"""

import requests
from typing import List, Dict

from lavesecexpress_etl.config.settings import LAUNDRY_SYSTEM_CONFIG


BASE_URL = LAUNDRY_SYSTEM_CONFIG["base_url"]

#===
# INTERNAL PAGINATION HANDLER
#===

def _fetch_paginated(
    endpoint: str,
    headers: Dict,
    params: Dict,
    quantidade: int = 1000,
    timeout: int = 60
) -> List[Dict]:
    
    """
    Executa requisições paginadas em um endpoint da API do sistema da lavanderia.

    A função inicia na página 0 e continua requisitando novas páginas até que
    a API retorne uma lista vazia. Todos os registros recebidos são acumulados
    em uma lista única.

    Parameters
    ----------
    endpoint : str
        Nome do endpoint relativo à BASE_URL.

    headers : dict
        Headers HTTP da requisição, incluindo chave de autenticação.

    params : dict
        Parâmetros base da requisição. A função adiciona automaticamente
        pagina e quantidade.

    quantidade : int, default=1000
        Quantidade de registros solicitados por página.

    timeout : int, default=60
        Tempo máximo, em segundos, para cada requisição HTTP.

    Returns
    -------
    list[dict]
        Lista consolidada de registros retornados pela API.

    Raises
    ------
    Exception
        Quando a API retorna status HTTP diferente de 200.
    """

    url = f"{BASE_URL}/{endpoint}"

    pagina = 0
    todos_registros = []

    while True:

        print(f"📡 API Sistema Lavanderia | {endpoint} | página {pagina}")

        params_paginados = {
            **params,
            "pagina": pagina,
            "quantidade": quantidade
        }

        response = requests.get(
            url=url,
            headers=headers,
            params=params_paginados,
            timeout=timeout
        )

        if response.status_code != 200:
            raise Exception(
                f"[API Sistema Lavanderia - {endpoint}] "
                f"Erro {response.status_code} - {response.text}"
            )

        dados = response.json()

        if not dados:
            print("🛑 Fim da paginação.")
            break

        print(f"📦 Registros recebidos: {len(dados)}")

        todos_registros.extend(dados)
        pagina += 1

    print(f"✅ Total coletado: {len(todos_registros)}")

    return todos_registros

#===
# PUBLIC ENDPOINTS
#===

def fetch_vendas(
    start_timestamp: str,
    end_timestamp: str,
    api_key: str,
    cnpj: str
) -> List[Dict]:

    """
    Coleta vendas da API do sistema da lavanderia dentro de uma janela de
    timestamps.

    Parameters
    ----------
    start_timestamp : str
        Timestamp inicial da extração.

    end_timestamp : str
        Timestamp final da extração.

    api_key : str
        Chave de autenticação da API do sistema da lavanderia.

    cnpj : str
        CNPJ utilizado como filtro da consulta.

    Returns
    -------
    list[dict]
        Lista de registros de vendas retornados pela API.

    Notes
    -----
    A extração utiliza somenteSucesso=false, trazendo não apenas vendas
    concluídas com sucesso, mas também registros que podem representar falhas
    ou tentativas não aprovadas.
    """

    headers = {
        "x-api-key": api_key
    }

    params = {
        "dataInicio": start_timestamp,
        "dataTermino": end_timestamp,
        "somenteSucesso": "false",
        "cnpj": cnpj
    }

    return _fetch_paginated(
        endpoint="vendas",
        headers=headers,
        params=params
    )


def fetch_maquinas(
    api_key: str,
    cnpj: str,
    quantidade: int = 100,
    timeout: int = 60
):

    headers = {
        "x-api-key": api_key
    }

    todos_registros = []
    pagina = 0

    print("📡 API Sistema Lavanderia | maquinas")

    while True:

        params = {
            "cnpj": cnpj,
            "pagina": pagina,
            "quantidade": quantidade,
            # "estadoCadastro": True
        }

        response = requests.get(
            url=f"{BASE_URL}/maquinas",
            headers=headers,
            params=params,
            timeout=timeout
        )

        if response.status_code != 200:
            print("STATUS CODE:", response.status_code)
            print("RESPONSE TEXT:", response.text)
            raise Exception(
                f"[API Sistema Lavanderia - maquinas] Erro {response.status_code}"
            )

        dados = response.json()

        if not dados:
            print("🛑 Fim da paginação.")
            break

        print(f"📦 Página {pagina} | Registros: {len(dados)}")

        todos_registros.extend(dados)
        pagina += 1

    print(f"✅ Total coletado: {len(todos_registros)}")

    return todos_registros


def fetch_lavanderias(
    api_key: str,
    cnpj: str,
    pagina: int = 0,
    quantidade: int = 100,
    timeout: int = 60
):

    headers = {
        "x-api-key": api_key
    }

    params = {
        "cnpj": cnpj,
        "pagina": pagina,
        "quantidade": quantidade
    }

    print("📡 API Sistema Lavanderia | lavanderias")

    response = requests.get(
        url=f"{BASE_URL}/lavanderias",
        headers=headers,
        params=params,
        timeout=timeout
    )

    if response.status_code != 200:
        print("STATUS CODE:", response.status_code)
        print("RESPONSE TEXT:", response.text)
        raise Exception(
            f"[API Sistema Lavanderia - lavanderias] Erro {response.status_code}"
        )

    dados = response.json()

    print(f"📦 Registros recebidos: {len(dados)}")

    return dados


def fetch_clientes(
    api_key: str,
    quantidade: int = 1000,
    timeout: int = 60
):

    headers = {
        "x-api-key": api_key
    }

    todos_registros = []
    pagina = 0

    print("📡 API Sistema Lavanderia | clientes")

    while True:

        params = {
            "pagina": pagina,
            "quantidade": quantidade,
            "campoOrdenacao": "dataCadastro",
            "direcaoOrdenacao": "asc"
        }

        response = requests.get(
            url=f"{BASE_URL}/clientes",
            headers=headers,
            params=params,
            timeout=timeout
        )

        if response.status_code != 200:
            print("STATUS CODE:", response.status_code)
            print("RESPONSE TEXT:", response.text)
            raise Exception(
                f"[API Sistema Lavanderia - clientes] Erro {response.status_code}"
            )

        dados = response.json()

        if not dados:
            print("🛑 Fim da paginação.")
            break

        print(f"📦 Página {pagina} | Registros: {len(dados)}")

        todos_registros.extend(dados)
        pagina += 1

    print(f"✅ Total coletado: {len(todos_registros)}")

    return todos_registros
