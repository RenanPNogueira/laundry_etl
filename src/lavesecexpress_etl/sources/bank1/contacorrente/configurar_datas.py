"""
Módulo: configurar_datas.py

Responsabilidade
----------------
Configurar o período de consulta do extrato de Conta Corrente do Banco 1
usando automação Selenium.

Contexto
--------
Este módulo faz parte da integração do Banco 1. Ele é utilizado após a
criação da sessão Selenium, autenticação no internet banking e navegação até
o menu de extratos de conta corrente.

Papel no fluxo do Banco 1
--------------------------
- selenium_session.py:
    cria a sessão do navegador.

- login.py:
    autentica o usuário no Banco 1.

- navegar_menu.py:
    acessa o menu de extratos de conta corrente.

- configurar_datas.py:
    seleciona o período "Específico" e preenche data inicial e data final.

- exportação/download:
    etapa posterior responsável por gerar e baixar o arquivo de extrato.

Principais componentes
----------------------
- bank1_configurar_periodo:
    seleciona o período específico e preenche os campos de data inicial e final.

Observações
-----------
Este módulo não realiza login, navegação inicial ou download. Ele apenas
configura o filtro de datas na tela de extrato já carregada.
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

# ======================================================
# Função: selecionar período e preencher as datas
# ======================================================

def bank1_configurar_periodo(driver, data_inicio, data_fim):

    """
    Configura o período "Específico" no extrato de Conta Corrente do Banco 1.

    A função interage com a tela de extrato via Selenium, abre o dropdown de
    períodos, seleciona a opção "Específico" e preenche os campos de data
    inicial e final no formato dd/mm/YYYY.

    Parameters
    ----------
    driver
        Instância Selenium WebDriver já autenticada e posicionada na tela de
        Extratos → Conta Corrente.

    data_inicio : datetime.date | datetime.datetime
        Data inicial que será preenchida no filtro do extrato.

    data_fim : datetime.date | datetime.datetime
        Data final que será preenchida no filtro do extrato.

    Returns
    -------
    None
        A função não retorna valor. Apenas interage com a página.

    Raises
    ------
    Exception
        Relança qualquer erro ocorrido durante a interação com os elementos da
        tela.

    Notes
    -----
    - A função usa espera explícita de 15 segundos.
    - Cliques normais possuem fallback para clique via JavaScript.
    - As datas são preenchidas no formato brasileiro dd/mm/YYYY.
    """

    print("\n🗓️ [DEBUG] Iniciando configuração de período 'Específico'...")

    wait = WebDriverWait(driver, 15)

    try:
        #===
        # 0) GARANTIR QUE O DROPDOWN ESTEJA FECHADO ANTES DE ABRIR
        #===
        try:
            driver.find_element(By.TAG_NAME, "body").click()
            time.sleep(0.5)
        except:
            pass

        #===
        # 1) SCROLL PARA O TOPO (dropdown às vezes fica fora da view)
        #===
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.3)

        #===
        # 2) ABRIR DROPDOWN
        #===
        print("🗂️ [DEBUG] Abrindo lista de períodos...")
        dropdown = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "input.select-dropdown.dropdown-trigger")
            )
        )

        # Se o dropdown estiver obstruído → forçar clique via JS
        try:
            dropdown.click()
        except:
            driver.execute_script("arguments[0].click();", dropdown)

        time.sleep(1)

        #===
        # 3) SELECIONAR "ESPECÍFICO"
        #===
        print("🔘 [DEBUG] Selecionando opção 'Específico'...")
        opcao_especifico = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//li[.//span[text()='Específico']]")
            )
        )

        try:
            opcao_especifico.click()
        except:
            driver.execute_script("arguments[0].click();", opcao_especifico)

        time.sleep(0.8)

        #===
        # 4) PREENCHER AS DATAS
        #===
        di_str = data_inicio.strftime("%d/%m/%Y")
        df_str = data_fim.strftime("%d/%m/%Y")
        print(f"✍️ [DEBUG] Preenchendo datas: {di_str} até {df_str}")

        campo_inicio = wait.until(
            EC.presence_of_element_located(
                (By.ID, "permissao:form-extrato:dataInicial:campoCalendario")
            )
        )
        campo_inicio.clear()
        campo_inicio.send_keys(di_str)

        campo_fim = wait.until(
            EC.presence_of_element_located(
                (By.ID, "permissao:form-extrato:dataFinal:campoCalendario")
            )
        )
        campo_fim.clear()
        campo_fim.send_keys(df_str)

        print("✅ [DEBUG] Período 'Específico' configurado com sucesso.")
        time.sleep(1)

    except Exception as e:
        print(f"❌ [DEBUG] Erro ao configurar o período 'Específico': {e}")
        raise
