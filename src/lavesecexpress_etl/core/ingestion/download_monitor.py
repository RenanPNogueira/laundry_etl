"""
Módulo: download_monitor.py

Responsabilidade
----------------
Monitorar uma pasta de downloads, identificar arquivos com base em regras
simples de nome, renomear o arquivo encontrado e movê-lo para uma pasta de
destino.

Contexto
--------
Este módulo faz parte do módulo `core` do pacote `lavesecexpress_etl`, uma biblioteca reutilizável
para engenharia de dados. Ele foi desenhado para apoiar processos de ingestão
em que arquivos são baixados automaticamente por ferramentas externas, como
Selenium, navegadores ou sistemas legados.

Principais componentes
----------------------
- wait_for_download: monitora uma pasta até encontrar um arquivo compatível
  com as regras informadas, renomeando e movendo o arquivo.
- _matches_rules: valida se um nome de arquivo atende aos filtros definidos.

Observações
-----------
Este módulo não realiza o download diretamente. Ele apenas monitora uma pasta
local e organiza o arquivo após sua chegada.
"""

import os
import shutil
import time
from datetime import datetime
from typing import Optional


TEMPORARY_DOWNLOAD_EXTENSIONS = (
    ".crdownload",
    ".part",
    ".tmp",
)


def wait_for_download(
    download_dir: str,
    destination_dir: str,
    final_prefix: str,
    startswith: Optional[str] = None,
    contains: Optional[str] = None,
    endswith: Optional[str] = None,
    timeout_seconds: int = 300,
    poll_interval: int = 1,
) -> Optional[str]:
    """
    Monitora uma pasta até encontrar um arquivo compatível com as regras
    informadas, renomeia esse arquivo e o move para uma pasta de destino.

    Parameters
    ----------
    download_dir : str
        Diretório que será monitorado. Normalmente é a pasta temporária onde
        o navegador salva arquivos baixados.

    destination_dir : str
        Diretório final para onde o arquivo encontrado será movido.

    final_prefix : str
        Prefixo aplicado ao novo nome do arquivo.

    startswith : str | None, default=None
        Regra opcional indicando que o nome do arquivo deve começar com esse
        texto.

    contains : str | None, default=None
        Regra opcional indicando que o nome do arquivo deve conter esse texto.

    endswith : str | None, default=None
        Regra opcional indicando que o nome do arquivo deve terminar com esse
        texto. Exemplo: ".csv", ".xlsx", ".xls".

    timeout_seconds : int, default=300
        Tempo máximo, em segundos, que a função aguardará pelo arquivo.

    poll_interval : int, default=1
        Intervalo, em segundos, entre cada verificação da pasta.

    Returns
    -------
    str | None
        Caminho completo do arquivo movido quando encontrado.
        Retorna None se nenhum arquivo compatível for encontrado dentro do
        tempo limite.

    Raises
    ------
    FileNotFoundError
        Quando o diretório de download informado não existe.

    ValueError
        Quando nenhum critério de busca é informado.

    Notes
    -----
    - A função ignora arquivos temporários de download, como `.crdownload`,
      `.part` e `.tmp`.
    - A extensão original do arquivo encontrado é preservada no novo nome.
    - A pasta de destino é criada automaticamente caso não exista.
    """

    if not os.path.isdir(download_dir):
        raise FileNotFoundError(
            f"O diretório de download não existe: {download_dir}"
        )

    if not any([startswith, contains, endswith]):
        raise ValueError(
            "Informe ao menos uma regra de busca: startswith, contains ou endswith."
        )

    os.makedirs(destination_dir, exist_ok=True)

    print(f"📥 Monitorando downloads em: {download_dir}")
    print(f"⏳ Timeout: {timeout_seconds} segundos")

    start_time = time.time()

    while time.time() - start_time < timeout_seconds:
        files = os.listdir(download_dir)

        for filename in files:
            if _is_temporary_download_file(filename):
                continue

            if not _matches_rules(
                filename=filename,
                startswith=startswith,
                contains=contains,
                endswith=endswith,
            ):
                continue

            source_path = os.path.join(download_dir, filename)

            if not os.path.isfile(source_path):
                continue

            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            _, extension = os.path.splitext(filename)

            new_filename = f"{final_prefix}-{timestamp}{extension}"
            destination_path = os.path.join(destination_dir, new_filename)

            shutil.move(source_path, destination_path)

            print(f"✅ Arquivo detectado e movido para: {destination_path}")

            return destination_path

        time.sleep(poll_interval)

    print("⚠️ Timeout atingido. Nenhum arquivo compatível foi encontrado.")
    return None


def _matches_rules(
    filename: str,
    startswith: Optional[str],
    contains: Optional[str],
    endswith: Optional[str],
) -> bool:
    """
    Valida se um nome de arquivo atende às regras de busca informadas.

    Parameters
    ----------
    filename : str
        Nome do arquivo que será validado.

    startswith : str | None
        Texto que o nome do arquivo deve iniciar.

    contains : str | None
        Texto que o nome do arquivo deve conter.

    endswith : str | None
        Texto que o nome do arquivo deve terminar.

    Returns
    -------
    bool
        True quando o arquivo atende a todas as regras informadas.
        False caso contrário.
    """

    if startswith and not filename.startswith(startswith):
        return False

    if contains and contains not in filename:
        return False

    if endswith and not filename.lower().endswith(endswith.lower()):
        return False

    return True


def _is_temporary_download_file(filename: str) -> bool:
    """
    Identifica arquivos temporários gerados durante downloads em andamento.

    Parameters
    ----------
    filename : str
        Nome do arquivo que será avaliado.

    Returns
    -------
    bool
        True quando o arquivo possui extensão temporária de download.
        False caso contrário.
    """

    return filename.lower().endswith(TEMPORARY_DOWNLOAD_EXTENSIONS)