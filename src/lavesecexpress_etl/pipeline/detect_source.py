"""
Módulo: detect_source.py

Responsabilidade
----------------
Identificar a fonte de um arquivo local com base no nome do arquivo.

Contexto
--------
Este módulo faz parte da camada de pipelines do pacote lavesecexpress_etl.
Ele fornece uma função auxiliar usada para classificar arquivos de entrada em
identificadores padronizados de fonte, permitindo que fluxos genéricos de
transformação saibam como agrupar ou processar cada arquivo.

Fontes identificadas
--------------------
- bank3_contacorrente
- bank1_contacorrente
- bank2_recebimentos

Observações
-----------
A identificação é feita por busca de substrings no nome do arquivo. A função
não valida o conteúdo do arquivo e não garante que a classificação esteja
correta se o nome estiver fora do padrão esperado.
"""

def identify_source(filename: str) -> str | None:
    """
    Identifica a fonte de um arquivo a partir do nome.

    Parameters
    ----------
    filename : str
        Nome ou caminho do arquivo que será analisado.

    Returns
    -------
    str | None
        Identificador padronizado da fonte quando reconhecida:
        - "bank3_contacorrente";
        - "bank1_contacorrente";
        - "bank2_recebimentos".

        Retorna None quando nenhuma regra é atendida.

    Notes
    -----
    - A comparação é feita em minúsculas.
    - A função usa substrings simples, não regex.
    - A ordem das regras importa.
    """
    name = filename.lower()

    if "bank3" in name:
        return "bank3_contacorrente"

    if "bank1" in name or "contacorrente" in name:
        return "bank1_contacorrente"

    if "bank2" in name or "recebimentos" in name:
        return "bank2_recebimentos"



    return None
