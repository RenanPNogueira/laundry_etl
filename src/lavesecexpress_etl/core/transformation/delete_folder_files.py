"""
Módulo: delete_folder_files.py

Responsabilidade
----------------
Fornecer uma função utilitária para limpar o conteúdo interno de uma pasta,
mantendo a pasta principal existente.

Contexto
--------
Este módulo faz parte do módulo `core` do pacote `lavesecexpress_etl`, uma biblioteca reutilizável
para engenharia de dados. Ele pode ser usado em pipelines para limpar
diretórios temporários, pastas de download ou áreas intermediárias antes ou
depois da execução de processos de ingestão.

Principais componentes
----------------------
- delete_folder_files: remove todos os arquivos, links simbólicos e subpastas
  existentes dentro de uma pasta.

Observações
-----------
A função não remove a pasta principal. Apenas limpa seu conteúdo interno.
"""

import os
import shutil


def delete_folder_files(folder_path: str) -> None:
    """
    Remove todos os arquivos, links simbólicos e subpastas de uma pasta.

    A função mantém a pasta principal e remove apenas os itens existentes
    dentro dela. É útil para limpar diretórios temporários usados por pipelines
    de dados, como pastas de download ou áreas de staging local.

    Parameters
    ----------
    folder_path : str
        Caminho da pasta cujo conteúdo será removido.

    Returns
    -------
    None
        A função não retorna valor. Apenas executa a limpeza da pasta.

    Raises
    ------
    FileNotFoundError
        Quando o caminho informado não existe.

    NotADirectoryError
        Quando o caminho informado existe, mas não é uma pasta.

    Notes
    -----
    - A pasta principal é preservada.
    - Arquivos internos são removidos.
    - Links simbólicos internos são removidos.
    - Subpastas internas são removidas recursivamente.
    """

    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Pasta não encontrada: {folder_path}")

    if not os.path.isdir(folder_path):
        raise NotADirectoryError(f"O caminho informado não é uma pasta: {folder_path}")

    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)

        if os.path.isfile(item_path) or os.path.islink(item_path):
            os.remove(item_path)

        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)

    print(f"🧹 Pasta limpa com sucesso: {folder_path}")