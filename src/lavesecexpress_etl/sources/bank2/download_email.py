"""
Módulo: download_email.py

Responsabilidade
----------------
Buscar no Gmail o e-mail de relatório do Banco 2, extrair o link de download
e salvar o arquivo CSV em uma pasta local.

Contexto
--------
Este módulo faz parte da integração do Banco 2.

Ele substitui o fluxo manual em que o usuário precisava abrir o e-mail do
Banco 2 e clicar no botão "Baixar relatório". O download passa a ser feito
automaticamente via IMAP + requests.

Fluxo
-----
1. Conecta ao Gmail via IMAP.
2. Busca e-mails do Banco 2.
3. Filtra pelo assunto esperado.
4. Opcionalmente filtra por data/hora mínima de recebimento.
5. Extrai o HTML do e-mail.
6. Captura o link do botão "Baixar relatório".
7. Faz o download do CSV.
8. Salva o arquivo na pasta temporária.

Observações
-----------
- Este módulo não lê variáveis de ambiente.
- Este módulo não importa settings.py.
- As credenciais e configurações devem ser recebidas por parâmetro.
- A responsabilidade de montar o email_config é do pipeline, orquestrador
  ou script de teste.
"""

import email
import imaplib
import re
import time
import unicodedata
from datetime import datetime, timezone
from email.header import decode_header
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup


def normalizar_texto(texto: str) -> str:
    """
    Remove acentos e coloca o texto em minúsculas.

    Isso permite comparar textos como:
    - "Seu relatório chegou!"
    - "seu relatorio chegou"
    """

    if not texto:
        return ""

    texto = unicodedata.normalize("NFKD", texto)

    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )

    return texto.lower().strip()


def decodificar_texto(valor: str) -> str:
    """
    Decodifica cabeçalhos de e-mail, como assunto e remetente.

    Alguns e-mails podem vir com encoding especial, principalmente quando
    possuem acentos ou caracteres especiais.
    """

    if not valor:
        return ""

    partes = decode_header(valor)
    texto_final = ""

    for texto, encoding in partes:
        if isinstance(texto, bytes):
            texto_final += texto.decode(encoding or "utf-8", errors="ignore")
        else:
            texto_final += texto

    return texto_final


def conectar_gmail(email_config: dict) -> imaplib.IMAP4_SSL:
    """
    Conecta ao Gmail usando IMAP + senha de app.

    Parameters
    ----------
    email_config : dict
        Dicionário de configuração contendo:
        - imap_server
        - imap_port
        - email_user
        - email_password

    Returns
    -------
    imaplib.IMAP4_SSL
        Conexão IMAP autenticada.
    """

    imap_server = email_config.get("imap_server")
    imap_port = email_config.get("imap_port")
    email_user = email_config.get("email_user")
    email_password = email_config.get("email_password")

    if not imap_server:
        raise ValueError("Servidor IMAP não encontrado na configuração.")

    if not imap_port:
        raise ValueError("Porta IMAP não encontrada na configuração.")

    if not email_user:
        raise ValueError("E-mail do Gmail não encontrado na configuração.")

    if not email_password:
        raise ValueError("Senha de app do Gmail não encontrada na configuração.")

    # print("📧 Conectando ao Gmail...")
    # print(f"📧 Conta: {email_user}")

    mail = imaplib.IMAP4_SSL(imap_server, imap_port)
    mail.login(email_user, email_password)

    # print("✅ Login no Gmail realizado com sucesso.")

    return mail


def extrair_html_email(mensagem) -> str | None:
    """
    Extrai o corpo HTML de uma mensagem de e-mail.

    O botão "Baixar relatório" do Banco 2 normalmente fica no HTML do e-mail.
    """

    if mensagem.is_multipart():
        for parte in mensagem.walk():
            content_type = parte.get_content_type()
            content_disposition = str(parte.get("Content-Disposition"))

            # Ignora anexos.
            if "attachment" in content_disposition.lower():
                continue

            if content_type == "text/html":
                payload = parte.get_payload(decode=True)
                charset = parte.get_content_charset() or "utf-8"

                return payload.decode(charset, errors="ignore")

    else:
        if mensagem.get_content_type() == "text/html":
            payload = mensagem.get_payload(decode=True)
            charset = mensagem.get_content_charset() or "utf-8"

            return payload.decode(charset, errors="ignore")

    return None


def obter_data_recebimento(mensagem) -> datetime | None:
    """
    Converte o header Date do e-mail para datetime.

    Returns
    -------
    datetime | None
        Data/hora do e-mail com timezone, quando possível.

    Notes
    -----
    O header Date normalmente é suficiente para este fluxo, porque o e-mail
    do Banco 2 é gerado e enviado logo após a solicitação do relatório.
    """

    data_header = mensagem.get("Date")

    if not data_header:
        return None

    try:
        data_email = parsedate_to_datetime(data_header)

        if data_email.tzinfo is None:
            data_email = data_email.replace(tzinfo=timezone.utc)

        return data_email

    except Exception:
        return None


def normalizar_datetime_para_comparacao(
    valor: datetime | None,
) -> datetime | None:
    """
    Garante que o datetime usado na comparação tenha timezone.

    Isso evita erro ao comparar datetime sem timezone com datetime com timezone.
    """

    if valor is None:
        return None

    if valor.tzinfo is None:
        return valor.astimezone()

    return valor


def buscar_html_email_bank2(
    email_config: dict,
    received_after: datetime | None = None,
    max_emails_to_scan: int = 50,
) -> tuple[str, bytes]:
    """
    Busca o HTML do e-mail mais recente do Banco 2 que atende aos critérios.

    Parameters
    ----------
    email_config : dict
        Configuração do e-mail contendo:
        - imap_server
        - imap_port
        - email_user
        - email_password
        - sender
        - subject

    received_after : datetime | None
        Quando informado, só aceita e-mails recebidos após esse momento.

    max_emails_to_scan : int
        Quantidade máxima de e-mails recentes analisados.

    Returns
    -------
    tuple[str, bytes]
        HTML do e-mail e ID da mensagem IMAP.
    """

    mail = conectar_gmail(email_config)

    sender = email_config.get("sender")
    subject = email_config.get("subject")

    if not sender:
        raise ValueError("Remetente do Banco 2 não informado no email_config.")

    if not subject:
        raise ValueError("Assunto do Banco 2 não informado no email_config.")

    subject_normalizado = normalizar_texto(subject)
    received_after = normalizar_datetime_para_comparacao(received_after)

    try:
        mail.select("INBOX")

        print("📧 Checando e-mail do Banco 2...")

        status, dados = mail.search(
            None,
            "FROM",
            f'"{sender}"',
        )

        if status != "OK":
            raise RuntimeError("Erro ao buscar e-mails do Banco 2 no Gmail.")

        ids_email = dados[0].split()

        if not ids_email:
            print("⚠️ Nenhum e-mail encontrado pelo remetente.")
            print("🔎 Buscando e-mails recentes da INBOX como fallback...")

            status, dados = mail.search(None, "ALL")

            if status != "OK":
                raise RuntimeError("Erro ao buscar e-mails recentes no Gmail.")

            ids_email = dados[0].split()

        if not ids_email:
            raise FileNotFoundError("Nenhum e-mail encontrado na INBOX.")

        ids_para_analisar = list(reversed(ids_email))[:max_emails_to_scan]

        # print(f"📨 E-mails que serão analisados: {len(ids_para_analisar)}")

        for email_id in ids_para_analisar:
            status, dados_email = mail.fetch(email_id, "(RFC822)")

            if status != "OK":
                continue

            mensagem = email.message_from_bytes(dados_email[0][1])

            assunto = decodificar_texto(mensagem.get("Subject"))
            remetente = decodificar_texto(mensagem.get("From"))
            data_recebimento = obter_data_recebimento(mensagem)

            assunto_normalizado = normalizar_texto(assunto)

            # print("---- DEBUG EMAIL ----")
            # print("ID:", email_id)
            # print("Remetente:", remetente)
            # print("Assunto:", assunto)
            # print("Assunto normalizado:", assunto_normalizado)
            # print("Data recebimento:", data_recebimento)
            # print("Received after:", received_after)
            # print("---------------------")

            if subject_normalizado not in assunto_normalizado:
                continue

            # Quando received_after for informado, o e-mail precisa ter
            # uma data válida e posterior ao momento de referência.
            if received_after:
                if not data_recebimento:
                    continue

                if data_recebimento <= received_after:
                    continue

            # print()
            # print("✅ E-mail do Banco 2 encontrado:")
            # print("Remetente:", remetente)
            # print("Assunto:", assunto)
            # print("Data:", data_recebimento)
            # print()
            print("✅ E-mail do Banco 2 encontrado.")

            html = extrair_html_email(mensagem)

            if not html:
                raise RuntimeError(
                    "O e-mail foi encontrado, mas não possui corpo HTML."
                )

            return html, email_id

        raise FileNotFoundError(
            "Nenhum e-mail do Banco 2 compatível foi encontrado "
            "entre os e-mails analisados."
        )

    finally:
        mail.logout()
        # print("📧 Conexão com Gmail encerrada.")


def extrair_link_download(html_email: str) -> str:
    """
    Extrai o link de download do relatório no HTML do e-mail.

    Estratégia:
    1. Procura link cujo texto seja "Baixar relatório".
    2. Se não encontrar, procura link com padrão SendGrid.
    """

    soup = BeautifulSoup(html_email, "html.parser")

    links = []

    for tag in soup.find_all("a", href=True):
        texto = tag.get_text(strip=True)
        href = tag["href"]

        links.append(
            {
                "texto": texto,
                "href": href,
            }
        )

    print(f"🔗 Links encontrados no e-mail: {len(links)}")

    for link in links:
        texto_normalizado = normalizar_texto(link["texto"])

        if "baixar relatorio" in texto_normalizado:
            print("✅ Link encontrado pelo texto do botão.")
            return link["href"]

    for link in links:
        href = link["href"]

        if "sendgrid.net/ls/click" in href:
            print("✅ Link encontrado pelo padrão SendGrid.")
            return href

    print("Links encontrados no e-mail:")
    for indice, link in enumerate(links, start=1):
        print(f"{indice}. Texto: {link['texto']}")
        print(f"   Href: {link['href'][:120]}...")
        print()

    raise RuntimeError("Link de download não encontrado no HTML do e-mail.")


def extrair_nome_arquivo(content_disposition: str) -> str:
    """
    Extrai o nome do arquivo a partir do header Content-Disposition.

    Quando o Banco 2 não envia o nome do arquivo no header, gera um nome
    único seguindo a convenção:
        bank2_recebimentos_YYYY-MM-DD_HH-MM-SS.csv

    A inclusão de microssegundos evita sobrescrita caso dois arquivos sejam
    salvos no mesmo segundo.
    """

    if not content_disposition:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
        return f"bank2_recebimentos_{timestamp}.csv"

    match = re.search(r'filename="?([^"]+)"?', content_disposition)

    if not match:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
        return f"bank2_recebimentos_{timestamp}.csv"

    return unquote(match.group(1))


def validar_resposta_csv(
    content_type: str,
    nome_arquivo: str,
    conteudo: bytes,
) -> None:
    """
    Valida se a resposta baixada parece ser um arquivo CSV.

    Parameters
    ----------
    content_type : str
        Header Content-Type retornado pelo servidor.

    nome_arquivo : str
        Nome do arquivo identificado pelo Content-Disposition.

    conteudo : bytes
        Conteúdo retornado pela requisição.

    Raises
    ------
    RuntimeError
        Quando a resposta aparenta não ser um CSV válido.
    """

    content_type = (content_type or "").lower()
    nome_arquivo = (nome_arquivo or "").lower()

    if not conteudo:
        raise RuntimeError("O download retornou conteúdo vazio.")

    if "text/html" in content_type:
        raise RuntimeError(
            "O link retornou HTML em vez do CSV. "
            "Provavelmente caiu em uma página intermediária."
        )

    parece_csv_por_header = "csv" in content_type
    parece_csv_por_nome = nome_arquivo.endswith(".csv")

    if not parece_csv_por_header and not parece_csv_por_nome:
        raise RuntimeError(
            "O arquivo baixado não parece ser um CSV. "
            f"Content-Type recebido: {content_type}. "
            f"Nome do arquivo: {nome_arquivo}."
        )


def baixar_arquivo_por_link(
    url: str,
    output_folder: Path,
) -> Path:
    """
    Baixa o arquivo CSV a partir do link do e-mail.

    Parameters
    ----------
    url : str
        Link do botão "Baixar relatório".

    output_folder : Path
        Pasta onde o arquivo será salvo.

    Returns
    -------
    Path
        Caminho do arquivo baixado.
    """

    output_folder.mkdir(parents=True, exist_ok=True)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    print("📥 Iniciando download do relatório via link do e-mail...")

    response = requests.get(
        url,
        headers=headers,
        allow_redirects=True,
        timeout=60,
    )

    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "").lower()
    content_disposition = response.headers.get("Content-Disposition", "")
    nome_arquivo = extrair_nome_arquivo(content_disposition)

    print("Status:", response.status_code)
    print("Content-Type:", content_type)
    print("Content-Disposition:", content_disposition)
    print("Tamanho em bytes:", len(response.content))

    validar_resposta_csv(
        content_type=content_type,
        nome_arquivo=nome_arquivo,
        conteudo=response.content,
    )

    caminho_arquivo = output_folder / nome_arquivo

    # Evita sobrescrever arquivos caso o nome já exista na pasta.
    if caminho_arquivo.exists():
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
        caminho_arquivo = output_folder / f"bank2_recebimentos_{timestamp}.csv"

    with open(caminho_arquivo, "wb") as arquivo:
        arquivo.write(response.content)

        print(f"✅ Arquivo salvo em: {caminho_arquivo}")

        return caminho_arquivo


def aguardar_e_baixar_relatorio_bank2(
    email_config: dict,
    output_folder: Path,
    received_after: datetime | None = None,
    timeout_seconds: int = 600,
    polling_interval_seconds: int = 15,
) -> Path:
    """
    Aguarda o e-mail do Banco 2 chegar e baixa o relatório CSV.

    Parameters
    ----------
    email_config : dict
        Configuração de conexão e filtros do e-mail.

    output_folder : Path
        Pasta onde o arquivo será salvo.

    received_after : datetime | None
        Data/hora mínima de recebimento do e-mail.

    timeout_seconds : int
        Tempo máximo de espera pelo e-mail.

    polling_interval_seconds : int
        Intervalo entre as tentativas.

    Returns
    -------
    Path
        Caminho do CSV baixado.
    """

    inicio = time.time()
    ultima_excecao = None

    print("📨 Aguardando e-mail do Banco 2 com o relatório...")

    while time.time() - inicio < timeout_seconds:
        try:
            html_email, _email_id = buscar_html_email_bank2(
                email_config=email_config,
                received_after=received_after,
            )

            link_download = extrair_link_download(html_email)

            caminho_arquivo = baixar_arquivo_por_link(
                url=link_download,
                output_folder=output_folder,
            )

            return caminho_arquivo

        except FileNotFoundError as erro:
            ultima_excecao = erro

            print(
                f"⏳ E-mail ainda não encontrado. "
                f"Nova tentativa em {polling_interval_seconds}s..."
            )

            time.sleep(polling_interval_seconds)

    raise TimeoutError(
        "Tempo limite atingido aguardando o e-mail do Banco 2."
    ) from ultima_excecao
