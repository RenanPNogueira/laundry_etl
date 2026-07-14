"""
Módulo: login.py

Responsabilidade
----------------
Realizar o login na plataforma do Banco 2 usando uma sessão Selenium
previamente criada.

Contexto
--------
Este módulo faz parte da integração do Banco 2. Ele deve ser executado após
a criação do driver Selenium e antes das etapas de acesso ao relatório,
configuração de filtros e exportação de arquivos.

Papel no fluxo do Banco 2
--------------------------
- shared.selenium_session:
    cria e configura a sessão do navegador.

- login.py:
    acessa a página de login do Banco 2, preenche usuário e senha, trata
    banner eventual e aguarda autenticação via app.

- acessar_relatorio.py:
    navega até Relatórios → Lista de recebimentos após o login.

- configuração/exportação:
    etapas posteriores responsáveis por filtros, datas e download do relatório.

Principais componentes
----------------------
- bank2_fechar_banner:
    fecha o banner/modal “Acesso com CPF”, caso ele apareça.

- bank2_preencher_login:
    acessa a tela de login e preenche usuário e senha.

- bank2_executar_login:
    clica em Entrar e aguarda autenticação via app.

- bank2_login:
    executa o fluxo completo de login.

Observações
-----------
Este módulo não cria o navegador e não lê variáveis de ambiente. Usuário e
senha devem ser enviados como parâmetros pelo orquestrador ou pipeline.
"""

import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


#=============
# 🔧 Função nova — Fecha o banner "Acesso com CPF" (sem quebrar o fluxo)
#=============
def bank2_fechar_banner(driver, timeout=7):
    """
    Fecha o banner 'Acesso com CPF' caso ele apareça.
    Tenta tanto o botão 'Entendi' quanto o X.
    Tenta várias vezes dentro de um intervalo.
    """
    end_time = time.time() + timeout

    while time.time() < end_time:
        try:
            modal = driver.find_element(By.CSS_SELECTOR, "div.jade-modal")
        except:
            time.sleep(0.3)
            continue  # ainda não apareceu

        print("⚠️ Banner detectado! Tentando fechar...")

        # 1) botão Entendi
        try:
            botao_entendi = modal.find_element(
                By.XPATH, ".//button[contains(., 'Entendi')]"
            )
            botao_entendi.click()
            print("✅ Banner fechado com 'Entendi'.")
            time.sleep(0.4)
            return
        except:
            pass

        # 2) botão X
        try:
            botao_x = modal.find_element(
                By.CSS_SELECTOR, "div.jade-modal__close button"
            )
            botao_x.click()
            print("✅ Banner fechado com 'X'.")
            time.sleep(0.4)
            return
        except:
            pass

        time.sleep(0.3)

    # Não apareceu → segue o fluxo normal
    print("ℹ️ Nenhum banner detectado dentro do timeout.")


#===
# 1️⃣ Preencher usuário e senha (fiel ao script original)
#===
def bank2_preencher_login(driver, usuario_bank2, senha_bank2, login_url):
    """
    Acessa a tela de login do Banco 2 e preenche usuário e senha.
    """
    url_login = login_url
    print(f"🌐 Acessando página de login: {url_login}")

    try:
        driver.get(url_login)

        # >>>>> ADICIONADO AQUI: tentar fechar o banner <<<<<
        bank2_fechar_banner(driver)

        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.ID, "username")))
        print("✅ Página de login carregada com sucesso.")

        print("⌨️ Preenchendo usuário...")
        campo_usuario = driver.find_element(By.ID, "username")
        driver.execute_script("arguments[0].value = '';", campo_usuario)
        campo_usuario.send_keys(usuario_bank2)

        print("🔐 Preenchendo senha...")
        campo_senha = driver.find_element(By.ID, "password")
        driver.execute_script("arguments[0].value = '';", campo_senha)
        campo_senha.send_keys(senha_bank2)

        print("✅ Credenciais preenchidas com sucesso.")

    except Exception as e:
        print("❌ Erro ao preencher login e senha:", e)
        raise


#===
# 2️⃣ Clicar em "Entrar" e aguardar autenticação via app
#===
def bank2_executar_login(driver, login_url, timeout=120):
    """
    Clica em 'Entrar' e aguarda o redirecionamento após autenticação no app.
    """
    url_home = login_url
    print("➡️ Tentando clicar no botão 'Entrar'...")

    try:
        botao_entrar = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[@type='submit' and contains(@class, 'jade-button')]")
            )
        )
        # NOVO — banner pode surgir DEPOIS do preenchimento
        bank2_fechar_banner(driver)
        botao_entrar.click()
        print("✅ Botão 'Entrar' clicado com sucesso.")
    except Exception as e:
        print("❌ Erro ao clicar no botão 'Entrar':", e)
        raise

    print("📲 Aguardando autenticação via app do Banco 2...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        if driver.current_url == url_home:
            print("✅ Login autorizado e página inicial carregada.")
            return
        time.sleep(1)

    raise TimeoutError("⛔ Tempo limite excedido aguardando autenticação via app.")


#===
# 3️⃣ Função orquestradora de login (pública)
#===
def bank2_login(driver, usuario_bank2, senha_bank2, login_url):

    """
    Executa o fluxo completo de login na plataforma do Banco 2.

    A função utiliza uma sessão Selenium já criada, acessa a página de login,
    preenche usuário e senha, trata possíveis banners e aguarda a autenticação
    via app do Banco 2.

    Parameters
    ----------
    driver
        Instância Selenium WebDriver já inicializada.

    usuario_bank2 : str
        Usuário utilizado para autenticação na plataforma do Banco 2.

    senha_bank2 : str
        Senha utilizada para autenticação na plataforma do Banco 2.

    login_url : str
        URL da página de login/home do Banco 2 (config BANK2_LOGIN_URL).

    Returns
    -------
    WebDriver
        O mesmo driver recebido, após autenticação concluída.

    Raises
    ------
    TimeoutError
        Quando a autenticação via app não é concluída dentro do tempo limite.

    Notes
    -----
    - O navegador deve ser criado antes desta função ser chamada.
    - A autenticação final depende de aprovação manual via app do Banco 2.
    - A função não acessa relatórios nem realiza downloads.
    """

    print("\n🌐 Iniciando login no Banco 2...")

    bank2_preencher_login(driver, usuario_bank2, senha_bank2, login_url)
    bank2_executar_login(driver, login_url)

    print("✅ Sessão do Banco 2 autenticada e pronta para uso.")
    return driver
