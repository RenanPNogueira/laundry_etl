"""
Módulo: selenium_session.py

Responsabilidade
----------------
Centralizar a criação de sessões Chrome para automações Selenium usadas no
ETL da lavanderia.

Contexto
--------
Este módulo faz parte da camada shared do pacote lavesecexpress_etl. Ele é
utilizado por integrações que dependem de navegação automatizada para acessar
sistemas externos, aplicar filtros, exportar relatórios e realizar downloads.

Principais componentes
----------------------
- get_chrome_major_version:
    Tenta detectar automaticamente a versão principal do Google Chrome
    instalada no Windows.

- iniciar_sessao_chrome:
    Inicializa uma sessão Chrome configurada para automações Selenium,
    incluindo pasta de download, preferências do navegador e comportamento
    de download automático.

Observações
-----------
Este módulo não executa extrações diretamente. Ele apenas cria e configura
o driver do navegador para que os módulos de integração possam utilizá-lo.

A detecção automática da versão do Chrome foi desenhada para ambiente Windows.
Em outros sistemas operacionais, a função pode retornar None e o driver será
inicializado pelo fallback padrão.
"""

import os
import time
import subprocess
import undetected_chromedriver as uc


#===
# 🔍 Detecta versão do Chrome automaticamente (Windows)
#===
def get_chrome_major_version():
    """
    Detecta a versão principal do Google Chrome instalada no Windows.

    A função consulta o Registro do Windows para obter a versão completa do
    Chrome e retorna apenas o número principal da versão. Esse valor pode ser
    usado pelo undetected_chromedriver para aumentar a compatibilidade entre
    o driver e o navegador instalado.

    Returns
    -------
    int | None
        Número principal da versão do Chrome, quando detectado.
        Retorna None quando a detecção falha.

    Notes
    -----
    Esta função depende de uma chave específica do Registro do Windows.
    Em ambientes fora do Windows, a detecção tende a falhar e o fallback será
    utilizado na inicialização do driver.
    """
    try:
        output = subprocess.check_output(
            'reg query "HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon" /v version',
            shell=True
        ).decode()

        version = output.split()[-1]
        major_version = int(version.split('.')[0])

        return major_version

    except Exception:
        print("⚠️ Não foi possível detectar versão do Chrome automaticamente.")
        return None


#===
# 🚀 Sessão Chrome STEALTH
#===
def iniciar_sessao_chrome(pasta_download: str):
    """
    Inicializa uma sessão Chrome configurada para automações Selenium.

    A função cria a pasta de download caso ela não exista, configura opções
    do navegador, tenta detectar automaticamente a versão do Chrome instalada
    e retorna um driver pronto para uso em processos de extração.

    Parameters
    ----------
    pasta_download : str
        Caminho da pasta onde os arquivos baixados pelo navegador deverão ser
        salvos.

    Returns
    -------
    WebDriver
        Instância do Chrome WebDriver configurada para uso nas automações.

    Notes
    -----
    - A função utiliza undetected_chromedriver.
    - A pasta de download é criada automaticamente se não existir.
    - A inicialização possui fallback caso a versão detectada do Chrome não
      funcione corretamente.
    - O driver retornado deve ser encerrado pelo processo chamador ao final da
      extração.
    """
    print("\n🚀 Iniciando sessão Selenium para Chrome (STEALTH)...")

    # Garante que a pasta de download exista
    if not os.path.isdir(pasta_download):
        os.makedirs(pasta_download, exist_ok=True)

    #===
    # 1) Configuração de opções do Chrome
    #===
    chrome_options = uc.ChromeOptions()

    prefs = {
        "download.default_directory": pasta_download,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    }

    chrome_options.add_experimental_option("prefs", prefs)

    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--no-default-browser-check")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--log-level=3")

    # User-Agent humano (opcional manter)
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    #===
    # 2) Detecta versão do Chrome
    #===
    version = get_chrome_major_version()
    print(f"🔍 Chrome version detectada: {version}")

    #===
    # 3) Inicializa driver (com fallback)
    #===
    try:
        if version:
            driver = uc.Chrome(
                options=chrome_options,
                headless=False,
                use_subprocess=True,
                version_main=version
            )
        else:
            driver = uc.Chrome(
                options=chrome_options,
                headless=False,
                use_subprocess=True
            )

    except Exception as e:
        print("⚠️ Falha ao iniciar com versão detectada. Tentando fallback...")
        driver = uc.Chrome(
            options=chrome_options,
            headless=False,
            use_subprocess=True
        )

    # Pequeno delay para estabilizar
    time.sleep(1.5)

    #===
    # 4) Força download sem pop-up
    #===
    try:
        driver.execute_cdp_cmd(
            "Page.setDownloadBehavior",
            {
                "behavior": "allow",
                "downloadPath": pasta_download,
            },
        )
    except Exception:
        try:
            driver.execute_cdp_cmd(
                "Browser.setDownloadBehavior",
                {
                    "behavior": "allow",
                    "downloadPath": pasta_download,
                },
            )
        except Exception:
            print("⚠️ Não foi possível aplicar comportamento de download via CDP.")

    #===
    # 5) Stealth patches no navegador
    #===
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });

                    window.chrome = {
                        runtime: {},
                    };

                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3],
                    });

                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['pt-BR', 'pt', 'en-US'],
                    });
                """
            },
        )
    except Exception:
        print("⚠️ Não foi possível aplicar patch de stealth completo.")

    print("🔒 Chrome inicializado em modo STEALTH.")
    print(f"📂 Pasta de downloads: {pasta_download}\n")

    return driver