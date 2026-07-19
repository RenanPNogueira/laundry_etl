"""
Módulo: settings.py

Responsabilidade
----------------
Centralizar configurações de ambiente, credenciais, parâmetros de conexão e
caminhos locais usados pelo ETL da lavanderia.

Contexto
--------
Este módulo faz parte do pacote lavesecexpress_etl e é consumido por
orquestradores, pipelines e integrações. Ele lê variáveis de ambiente para
evitar credenciais hardcoded no código.

Origem das variáveis
---------------------
As variáveis são lidas primeiro de um arquivo ".env" na raiz do projeto
(via python-dotenv) e, se não encontradas ali, do ambiente do sistema
operacional (comportamento anterior, mantido como fallback). Isso permite
migrar gradualmente das variáveis de ambiente do Windows para o .env sem
quebrar a execução no meio do caminho.

Configurações disponíveis
-------------------------
- BASE_PATH:
    caminho base de suporte do projeto.

- DB_CONFIG:
    parâmetros de conexão com o PostgreSQL.

- LAUNDRY_SYSTEM_CONFIG:
    credenciais e identificadores do sistema da lavanderia.

- BANK1_CONFIG:
    credenciais, pasta de downloads e pasta local de faturas do Banco 1.

- BANK2_CONFIG:
    credenciais e pasta de downloads do Banco 2.

- BANK3_CONFIG:
    pasta local dos arquivos de conta corrente do Banco 3.

- temp_folder:
    pasta temporária usada por pipelines que baixam ou processam arquivos.

Validação
---------
- validate_settings():
    verifica se todas as variáveis obrigatórias foram carregadas (do .env
    ou do sistema operacional) e levanta um erro claro, citando os nomes
    das variáveis ausentes, caso alguma falte. Deve ser chamada no início
    do orquestrador, antes de qualquer pipeline ser executado.

Observações
-----------
Credenciais sensíveis devem ser mantidas em variáveis de ambiente (.env ou
sistema operacional), nunca hardcoded neste arquivo. Caminhos locais fixos
devem ser revisados em eventual versão pública ou ambiente multiusuário.
"""


import os
from pathlib import Path

from dotenv import load_dotenv

# ------------- CARREGAMENTO DO .env -------------
# Procura o arquivo .env na raiz do projeto (3 níveis acima deste arquivo:
# config/ -> lavesecexpress_etl/ -> src/ -> raiz). Se o arquivo não existir,
# load_dotenv() simplesmente não faz nada e o os.getenv() abaixo cai no
# fallback do ambiente do sistema operacional, preservando o comportamento
# atual. Por padrão, load_dotenv() NÃO sobrescreve variáveis já definidas
# no sistema operacional.
_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(dotenv_path=_ENV_PATH)

# ------------- BASE PATH (OBRIGATÓRIO)

BASE_PATH = os.getenv("SUPPORT_DEFAULT_PATH")

# ------------ DATABASE
DB_CONFIG = {
    "host": os.getenv("PG_HOST"),
    "port": int(os.getenv("PG_PORT", 5432)),
    "user": os.getenv("PG_USER"),
    "password": os.getenv("PG_PASSWORD"),
    "db_name": os.getenv("PG_LSXP_DATABASE"),
}

# -------------- SISTEMA DA LAVANDERIA
LAUNDRY_SYSTEM_CONFIG = {
    "api_key": os.getenv("LAUNDRY_SYSTEM_API_KEY"),
    "cnpj": os.getenv("LAUNDRY_SYSTEM_BUSINESS_ID"),
    "base_url": os.getenv("LAUNDRY_SYSTEM_BASE_URL"),
}

# -------------- BANCO 1
BANK1_CONFIG = {
    "usuario": os.getenv("USER_ID"),
    "senha": os.getenv("BANK1_PASSWORD"),
    "pasta_downloads": os.getenv("DOWNLOAD_PATH"),
    "pasta_faturas": os.getenv(
        "BANK1_FATURAS_FOLDER",
        r"C:\Development\lavesecexpress\lavesecexpress_etl\data\support\bank1_cartoes",
    ),
    "login_url": os.getenv("BANK1_LOGIN_URL"),
}

# ------------------ BANCO 2
BANK2_CONFIG = {
    "usuario": os.getenv("USER_ID"),
    "senha": os.getenv("BANK2_PASSWORD"),
    "pasta_downloads": os.getenv("DOWNLOAD_PATH"),
    "login_url": os.getenv("BANK2_LOGIN_URL"),
}


# ------------------ EMAIL / GMAIL - RELATÓRIOS BANCO 2
BANK2_EMAIL_CONFIG = {
    "imap_server": os.getenv("BANK2_IMAP_SERVER"),
    "imap_port": int(os.getenv("BANK2_IMAP_PORT")) if os.getenv("BANK2_IMAP_PORT") else None,
    "email_user": os.getenv("BUSINESS_MAIL"),
    "email_password": os.getenv("BUSINESS_MAIL_PSWD"),
    "sender": os.getenv("BANK2_EMAIL_SENDER", "no_reply@stone.com.br"),
    "subject": os.getenv("BANK2_EMAIL_SUBJECT", "Seu relatório chegou!"),
}

BANK2_REPORT_DESTINATION_EMAIL = os.getenv(
    "BANK2_REPORT_DESTINATION_EMAIL",
    "lavanderia@gmail.com",
)

BANK3_CONFIG = {
    "pasta_arquivos": os.getenv(
        "BANK3_ARQUIVOS_FOLDER",
        r"C:\Development\lavesecexpress\lavesecexpress_etl\data\support\bank3_contacorrente",
    ),
}

temp_folder = os.getenv(
    "TEMP_FOLDER",
    r"C:\Development\lavesecexpress\lavesecexpress_etl\data\temp",
)

TEMP_DOWNLOAD_FOLDER = (
    Path(os.getenv("TEMP_DOWNLOAD_FOLDER"))
    if os.getenv("TEMP_DOWNLOAD_FOLDER")
    else None
)

# ------------- VALIDAÇÃO DE VARIÁVEIS OBRIGATÓRIAS -------------

REQUIRED_ENV_VARS = [
    "SUPPORT_DEFAULT_PATH",
    "PG_HOST",
    "PG_USER",
    "PG_PASSWORD",
    "PG_LSXP_DATABASE",
    "LAUNDRY_SYSTEM_API_KEY",
    "LAUNDRY_SYSTEM_BUSINESS_ID",
    "LAUNDRY_SYSTEM_BASE_URL",
    "USER_ID",
    "BANK1_PASSWORD",
    "BANK1_LOGIN_URL",
    "BANK2_PASSWORD",
    "BANK2_LOGIN_URL",
    "DOWNLOAD_PATH",
    "BANK2_IMAP_SERVER",
    "BANK2_IMAP_PORT",
    "BUSINESS_MAIL",
    "BUSINESS_MAIL_PSWD",
]


def validate_settings() -> None:
    """
    Valida se todas as variáveis de ambiente obrigatórias foram carregadas.

    A verificação considera tanto o arquivo ".env" quanto o ambiente do
    sistema operacional, já que ambos alimentam os.getenv(). Não expõe
    nenhum valor sensível na mensagem de erro — apenas os nomes das
    variáveis que estão faltando.

    Deve ser chamada no início do orquestrador (execute_etl.py), antes de
    criar qualquer conexão com o banco ou executar qualquer pipeline.

    Raises
    ------
    RuntimeError
        Quando uma ou mais variáveis obrigatórias não foram encontradas
        nem no .env nem no ambiente do sistema operacional.
    """

    faltando = [nome for nome in REQUIRED_ENV_VARS if not os.getenv(nome)]

    if faltando:
        raise RuntimeError(
            "Configuração incompleta. As seguintes variáveis de ambiente "
            "obrigatórias não foram encontradas (nem no .env, nem no "
            f"sistema operacional): {', '.join(faltando)}. Copie "
            "'.env.example' para '.env' na raiz do projeto e preencha os "
            "valores faltantes."
        )
