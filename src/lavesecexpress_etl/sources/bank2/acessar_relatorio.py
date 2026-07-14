"""
Módulo: acessar_relatorio.py

Responsabilidade
----------------
Navegar no portal do Banco 2 até a tela de Relatórios → Lista de recebimentos
usando Selenium.

Contexto
--------
Este módulo faz parte da integração do Banco 2. Ele deve ser executado após
o login no Banco 2 e antes das etapas de configuração de filtros, datas e
exportação do relatório.

Papel no fluxo do Banco 2
--------------------------
- selenium_session.py:
    cria e configura a sessão do navegador.

- login.py:
    autentica o usuário no portal do Banco 2.

- acessar_relatorio.py:
    acessa o menu Relatórios → Lista de recebimentos e trata eventual seleção
    de unidade.

- configurar filtros/datas:
    etapa posterior responsável por definir o período do relatório.

- exportação/download:
    etapa posterior responsável por solicitar e capturar o relatório.

Principais componentes
----------------------
- bank2_abrir_menu_relatorios:
    abre o menu Relatórios, acessa Lista de recebimentos, seleciona a unidade
    quando necessário e aguarda a tela de filtros carregar.

Observações
-----------
Este módulo não realiza login, não configura datas e não exporta arquivos.
Ele apenas posiciona o driver autenticado na tela correta do Banco 2.
"""

# import os
# import sys
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException


# ============================================================
# Helper — clique com retry em caso de StaleElementReferenceException
# ============================================================
def _clicar_com_retry_stale(driver, locator, label, timeout=15, tentativas=3, espera_entre_tentativas=0.4):
    """
    Localiza e clica em um elemento, tentando novamente do zero (nova busca +
    novo clique) se o elemento ficar "stale" entre a localização e o clique.

    Isso é necessário em telas React que re-renderizam trechos do DOM (às
    vezes com animações de fade) logo após a navegação, o que pode invalidar
    a referência do elemento entre localizá-lo e clicar nele.
    """
    ultimo_erro = None

    for tentativa in range(1, tentativas + 1):
        try:
            elemento = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable(locator)
            )
            elemento.click()
            return
        except StaleElementReferenceException as erro:
            ultimo_erro = erro
            print(f"⚠️ Elemento '{label}' ficou obsoleto (tentativa {tentativa}/{tentativas}). Tentando novamente...")
            time.sleep(espera_entre_tentativas)

    raise ultimo_erro


# ============================================================
# Ajuste de PATH para permitir imports "src.*" no debug local
# ============================================================
# ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
# if ROOT not in sys.path:
#     sys.path.append(ROOT)


# ============================================================
# 1️⃣ Função principal deste módulo
# ============================================================
def bank2_abrir_menu_relatorios(driver):

    """
    Acessa a tela de Lista de recebimentos do Banco 2.

    A função aguarda a home do Banco 2 carregar após o login, abre o menu
    lateral de Relatórios, clica em Lista de recebimentos e trata a seleção
    de unidade quando a tela intermediária aparece.

    Parameters
    ----------
    driver
        Instância Selenium WebDriver já autenticada no portal do Banco 2.

    Returns
    -------
    bool
        Retorna True quando a tela de filtros da Lista de recebimentos é
        carregada com sucesso.

    Raises
    ------
    TimeoutException
        Pode ocorrer caso algum elemento esperado da interface não seja
        encontrado dentro do tempo limite.

    Notes
    -----
    - A função assume que o login já foi concluído.
    - A seleção da unidade TASSARA E TASSARA é tratada quando exibida.
    - Os elementos são localizados principalmente por XPath baseado em textos
      visíveis da interface.
    """

    # NOVO: Aguarda a URL /home estabilizar antes de clicar no menu
    try:
        WebDriverWait(driver, 30).until(
            EC.url_contains("/home")
        )
        print("🏠 URL /home detectada. Aguardando renderização...")
        time.sleep(2)  # pequeno respiro para o React construir o menu
    except:
        print("⚠️ Aviso: não foi possível confirmar /home antes do menu. Tentando mesmo assim.")

    # 🔽 DAQUI PARA BAIXO É EXATAMENTE O SEU SCRIPT ORIGINAL 🔽

    print("📁 Acessando menu lateral 'Relatórios'...")
    _clicar_com_retry_stale(
        driver,
        (By.XPATH, "//p[@role='menuitem' and contains(text(), 'Relatórios')]/ancestor::button"),
        label="Relatórios",
    )
    time.sleep(0.7)

    print("📄 Clicando em 'Lista de recebimentos'...")
    _clicar_com_retry_stale(
        driver,
        (By.XPATH, "//p[contains(text(), 'Lista de recebimentos')]"),
        label="Lista de recebimentos",
    )
    time.sleep(1.8)

    print("🔍 Verificando se há seleção de unidade...")
    try:
        unidade_tassara = WebDriverWait(driver, 4).until(
            EC.presence_of_element_located(
                (By.XPATH, "//p[contains(text(), 'TASSARA E TASSARA')]")
            )
        )
        if unidade_tassara:
            print("🏢 Unidade 'TASSARA E TASSARA' detectada. Selecionando...")
            botao_continuar = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//div[contains(@class,'jade-modal__footer-actions-desktop')]//button[.//span[text()='Continuar']]",
                    )
                )
            )
            driver.execute_script("arguments[0].click();", botao_continuar)
            print("✅ Unidade confirmada e botão 'Continuar' clicado.")
    except Exception:
        print("ℹ️ Nenhuma seleção de unidade necessária.")

    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located(
            (By.XPATH, "//div[contains(@class,'jade-content-navigator-content__title')]//p")
        )
    )
    print("✅ Tela de filtros carregada com sucesso.")
    return True
