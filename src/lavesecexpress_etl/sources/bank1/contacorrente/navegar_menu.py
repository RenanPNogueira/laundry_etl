"""
Módulo: navegar_menu.py

Responsabilidade
----------------
Navegar no Internet Banking do Banco 1 até a tela de Extratos de Conta
Corrente usando Selenium.

Contexto
--------
Este módulo faz parte da integração do Banco 1. Ele é executado após a
criação da sessão Selenium e após a autenticação do usuário no Internet
Banking.

Papel no fluxo do Banco 1
--------------------------
- selenium_session.py:
    cria e configura a sessão do navegador.

- login.py:
    autentica o usuário no Banco 1.

- navegar_menu.py:
    acessa Menu lateral → Extratos → Conta Corrente.

- configurar_datas.py:
    configura o período específico do extrato.

- exportação/download:
    gera e baixa o arquivo de extrato.

Principais componentes
----------------------
- bank1_navegar_menu_extratos:
    abre o menu de Extratos e acessa a opção Conta Corrente.

Observações
-----------
Este módulo não realiza login, não configura datas e não exporta arquivos.
Ele apenas posiciona o driver autenticado na tela correta para as próximas
etapas da extração.
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
import time

# ============================================================
# FUNÇÃO MODULAR: NAVEGACÃO MENU → EXTRATOS → CONTA CORRENTE
# ============================================================

def bank1_navegar_menu_extratos(driver):

    """
    Navega até a tela de Extratos de Conta Corrente do Banco 1.

    A função utiliza uma sessão Selenium já autenticada, abre o menu lateral
    de Extratos e acessa a opção Conta Corrente.

    Parameters
    ----------
    driver
        Instância Selenium WebDriver já autenticada no Internet Banking do
        Banco 1.

    Returns
    -------
    None
        A função não retorna valor. Apenas interage com a página.

    Raises
    ------
    Exception
        Relança qualquer erro ocorrido durante a localização ou clique dos
        elementos da tela.

    Notes
    -----
    - A função usa espera explícita de 15 segundos.
    - Os elementos são localizados por XPath com base no texto da interface.
    - Antes dos cliques, os elementos são trazidos para a área visível da tela
      usando scrollIntoView.
    """

    print("\n📂 [DEBUG] Iniciando navegação no menu de Extratos...")

    try:
        wait = WebDriverWait(driver, 15)

        # 1. Abrir menu "Extratos"
        print("🔍 [DEBUG] Buscando item 'Extratos' no menu lateral...")
        extratos_menu = wait.until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//a[contains(@class, 'collapsible-header') and contains(text(), 'Extratos')]"
            ))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", extratos_menu)
        extratos_menu.click()
        print("📂 [DEBUG] Clique no menu 'Extratos' realizado.")
        time.sleep(1)

        # 2. Clicar na opção "Conta Corrente"
        print("📄 [DEBUG] Clicando na opção 'Conta Corrente'...")
        conta_corrente = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Conta corrente')]"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", conta_corrente)
        conta_corrente.click()
        time.sleep(2)

        print("✅ [DEBUG] Navegação até 'Conta Corrente' concluída com sucesso.")

    except Exception as e:
        print(f"❌ [DEBUG] Erro ao navegar até 'Conta Corrente': {e}")
        raise
