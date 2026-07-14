"""
Módulo: login.py

Responsabilidade
----------------
Realizar o login no Internet Banking do Banco 1 usando uma sessão Selenium
previamente criada.

Contexto
--------
Este módulo faz parte da integração do Banco 1. Ele é utilizado após a
criação do driver Selenium e antes das etapas de navegação até extratos,
configuração de datas e exportação de arquivos.

Papel no fluxo do Banco 1
--------------------------
- selenium_session.py:
    cria e configura a sessão do navegador.

- login.py:
    acessa o Banco 1, preenche usuário, senha e aguarda validação manual
    do token.

- navegar_menu.py:
    acessa o menu de extratos após a autenticação.

- configurar_datas.py:
    configura o período específico do extrato.

- exportação/download:
    gera e baixa o arquivo de extrato.

Principais componentes
----------------------
- bank1_acessar_site:
    abre o site do Banco 1 e acessa o Internet Banking.

- bank1_preencher_login:
    preenche usuário e senha por meio do teclado virtual.

- bank1_aguardar_token:
    aguarda a validação manual do token.

- bank1_login:
    executa o fluxo completo de autenticação.

Observações
-----------
Este módulo não lê variáveis de ambiente. Usuário, senha e URL devem ser
recebidos como parâmetros, geralmente enviados pelo orquestrador ou pipeline.
"""

import os
import sys
# Ajuste de PATH
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if ROOT not in sys.path:
    sys.path.append(ROOT)



from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException
import time

# ============================================================
# 1. ACESSAR SITE
# ============================================================

def bank1_acessar_site(driver, login_url):
    print("\n🌐 [DEBUG] Acessando site do Banco 1...")

    driver.get(login_url)
    time.sleep(2)

    print("🔍 [DEBUG] Procurando botão 'Internet Banking'...")
    botao = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Internet Banking')]"))
    )
    botao.click()

    time.sleep(2)
    abas = driver.window_handles
    driver.switch_to.window(abas[-1])

    print(f"🔁 [DEBUG] Nova guia ativa: {driver.current_url}")

    return driver


# ============================================================
# 2. PREENCHER LOGIN E SENHA
# ============================================================

def bank1_preencher_login(driver, usuario, senha_bank1):
    print("\n⌨️ [DEBUG] Preenchendo usuário e senha...")

    # Preencher usuário
    campo_usuario = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.ID, "formLogin:login:campoTexto"))
    )
    campo_usuario.send_keys(usuario)
    print("✅ [DEBUG] Usuário preenchido.")

    # Preencher senha via teclado virtual
    print("🔐 [DEBUG] Preenchendo senha via teclado virtual...")

    botoes = WebDriverWait(driver, 15).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, "botao-painel-intervalado-login"))
    )

    mapa_teclado = {}
    for botao in botoes:
        texto = botao.text.upper().strip()
        chars = texto.replace(" ", "").split("OU")
        for char in chars:
            mapa_teclado.setdefault(char, []).append(botao)

    for letra in senha_bank1.upper():
        if letra not in mapa_teclado:
            raise ValueError(f"❌ [DEBUG] Caractere '{letra}' não encontrado no teclado virtual.")
        mapa_teclado[letra][0].click()
        time.sleep(0.3)

    print("✅ [DEBUG] Senha preenchida.")

    # Clicar em entrar
    botao_entrar = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.ID, "formLogin:btn-logar:btAcaoAjax"))
    )
    botao_entrar.click()
    print("➡️ [DEBUG] Clique no botão 'Entrar'.")

    time.sleep(2)
    return driver


# ============================================================
# 3. AGUARDAR TOKEN MANUAL
# ============================================================

def bank1_aguardar_token(driver, timeout_geral=300):
    print("\n🕹️ [DEBUG] Aguardando validação do token (manual)...")

    tempo_inicio = time.time()
    url_detectada = None

    while True:
        tempo_decorrido = time.time() - tempo_inicio
        if tempo_decorrido > timeout_geral:
            raise TimeoutError("⏰ Tempo limite excedido aguardando token.")

        try:
            url_atual = driver.current_url

            if "confirmacaoToken.faces" in url_atual:
                if url_detectada != "confirmacaoToken.faces":
                    print("🔐 [DEBUG] Tela de token detectada.")
                    print("👉 Preencha o token manualmente e clique em 'OK'.")
                    url_detectada = "confirmacaoToken.faces"
                time.sleep(2)

            elif "posicao.faces" in url_atual:
                print("✅ [DEBUG] Token validado. Login concluído!")
                break

            else:
                print(f"⚠️ [DEBUG] URL inesperada: {url_atual}")
                time.sleep(2)

        except UnexpectedAlertPresentException:
            try:
                alerta = driver.switch_to.alert
                print(f"⚠️ [DEBUG] Alerta detectado: {alerta.text}")
                alerta.accept()
                driver.switch_to.default_content()
            except:
                pass
            time.sleep(2)

        except Exception as e:
            print(f"⚠️ [DEBUG] Erro monitorando token: {e}")
            time.sleep(2)


# ============================================================
# 4. FUNÇÃO PRINCIPAL (MODULAR)
# ============================================================

def bank1_login(driver, usuario, senha, login_url):
    """
    Executa o fluxo completo de login no Banco 1.

    A função utiliza uma sessão Selenium já criada, acessa o Internet Banking,
    preenche usuário e senha e aguarda a validação manual do token até que a
    sessão esteja autenticada.

    Parameters
    ----------
    driver
        Instância Selenium WebDriver já inicializada.

    usuario : str
        Usuário utilizado para autenticação no Banco 1.

    senha : str
        Senha utilizada no teclado virtual do Banco 1.

    login_url : str
        URL do Internet Banking do Banco 1.

    Returns
    -------
    WebDriver
        O mesmo driver recebido, após autenticação concluída.

    Raises
    ------
    TimeoutError
        Quando o token manual não é validado dentro do tempo limite.

    ValueError
        Quando algum caractere da senha não é encontrado no teclado virtual.

    Notes
    -----
    - O token é preenchido manualmente pelo usuário.
    - A função monitora a URL para identificar quando o login foi concluído.
    - O driver deve ser criado antes desta função ser chamada.
    """

    print("\n🚀 [DEBUG] Iniciando login modular do Banco 1...")

    bank1_acessar_site(driver, login_url)
    bank1_preencher_login(driver, usuario, senha)
    bank1_aguardar_token(driver)

    print("✅ [DEBUG] Login do Banco 1 finalizado e sessão autenticada.")

    return driver
