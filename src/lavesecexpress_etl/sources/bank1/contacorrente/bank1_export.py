"""
Módulo: bank1_export.py

Responsabilidade
----------------
Executar a busca, exportação e organização do arquivo Excel do extrato de
Conta Corrente do Banco 1 usando Selenium.

Contexto
--------
Este módulo faz parte da integração do Banco 1. Ele é utilizado após a
criação da sessão Selenium, autenticação no internet banking, navegação até
Extratos → Conta Corrente e configuração do período de consulta.

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

- bank1_export.py:
    clica em Buscar, aciona a exportação em Excel, aguarda o download,
    renomeia o arquivo e move para a pasta temporária do pipeline.

Principais componentes
----------------------
- bank1_click_buscar:
    executa a busca do extrato na tela.

- bank1_abrir_menu_exportacao:
    abre o menu de exportação por hover.

- bank1_click_exportar_excel:
    aciona a exportação do arquivo Excel.

- bank1_aguardar_download:
    monitora a pasta de downloads, identifica o arquivo .xls do extrato,
    renomeia e move para a pasta temporária.

- bank1_exportar_relatorio:
    função agrupadora usada para teste isolado.

Observações
-----------
Este módulo não realiza login, navegação inicial ou configuração de datas.
Ele atua apenas na etapa final de exportação do extrato.
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
from selenium.webdriver.common.action_chains import ActionChains
import time
from datetime import datetime
import shutil

# ==================================================================================
# Função modular: exportar relatório Excel do extrato de conta corrente
# ==================================================================================

# ============================================================
# 1️⃣ CLICAR NO BOTÃO "BUSCAR"
# ============================================================
def bank1_click_buscar(driver):
    print("🔎 [Banco 1] Clicando no botão 'Buscar'...")

    botao_buscar = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='Buscar']]"))
    )
    driver.execute_script("arguments[0].click();", botao_buscar)

    print("✔ [Banco 1] Botão 'Buscar' clicado.")
    time.sleep(2)


# ============================================================
# 2️⃣ ABRIR MENU DE EXPORTAÇÃO (HOVER)
# ============================================================
def bank1_abrir_menu_exportacao(driver):
    print("📂 [Banco 1] Abrindo menu de exportação...")

    botao_principal = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located(
            (By.XPATH, "//i[text()='local_printshop']/parent::a")
        )
    )

    driver.execute_script("arguments[0].scrollIntoView(true);", botao_principal)
    ActionChains(driver).move_to_element(botao_principal).perform()

    print("✔ [Banco 1] Menu de exportação exibido.")
    time.sleep(0.5)


# ============================================================
# 3️⃣ CLICAR EM "EXPORTAR EXCEL"
# ============================================================
def bank1_click_exportar_excel(driver):
    print("📤 [Banco 1] Clicando em 'Exportar Excel'...")

    botao_excel = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//a[@title='EXCEL' and .//i[text()='grid_on']]")
        )
    )

    driver.execute_script("arguments[0].click();", botao_excel)
    print("✔ [Banco 1] Exportação Excel acionada.")

    time.sleep(1)


# ============================================================
# 4️⃣ AGUARDAR DOWNLOAD + RENOMEAR + MOVER
# ============================================================
def bank1_aguardar_download(pasta_downloads, pasta_temp):

    """
    Aguarda o download do extrato de Conta Corrente do Banco 1 e organiza o arquivo.

    A função monitora a pasta de downloads até encontrar um arquivo Excel
    cujo nome contenha "extratoContaCorrente" e termine com ".xls".
    Quando encontrado, o arquivo é renomeado com timestamp e movido para a
    pasta temporária informada.

    Parameters
    ----------
    pasta_downloads : str
        Pasta onde o navegador salva os arquivos baixados.

    pasta_temp : str
        Pasta temporária do pipeline para onde o arquivo será movido.

    Returns
    -------
    str | None
        Caminho final do arquivo movido, quando encontrado.
        Retorna None se o arquivo não for detectado dentro do timeout.

    Notes
    -----
    - O timeout atual é de 300 segundos.
    - O padrão esperado no nome original é "extratoContaCorrente".
    - O arquivo final recebe o prefixo "bank1_contacorrente".
    """

    print(f"📥 [Banco 1] Aguardando download em: {pasta_downloads}")

    inicio = time.time()
    arquivo_final = None

    while time.time() - inicio < 300:  # 5 minutos
        arquivos = os.listdir(pasta_downloads)

        candidatos = [
            a for a in arquivos
            if "extratoContaCorrente" in a and a.lower().endswith(".xls")
        ]

        if candidatos:
            original = os.path.join(pasta_downloads, candidatos[0])

            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            novo_nome = f"bank1_contacorrente_{timestamp}.xls"
            destino = os.path.join(pasta_temp, novo_nome)

            shutil.move(original, destino)

            print(f"📁 [Banco 1] Arquivo detectado e movido para: {destino}")
            arquivo_final = destino
            break

        time.sleep(1)

    if not arquivo_final:
        print("⚠ [Banco 1] Timeout — nenhum arquivo baixado.")
        return None

    print("✔ [Banco 1] Download processado com sucesso.")
    return arquivo_final


# ============================================================
# 5️⃣ FUNÇÃO AGRUPADORA (para testes isolados)
# ============================================================
def bank1_exportar_relatorio(driver, pasta_downloads, pasta_temp):
    """
    Função que executa TODAS as etapas juntas,
    apenas para uso no DEBUG isolado.

    NO ORQUESTRADOR, cada função é chamada separadamente.
    """

    bank1_click_buscar(driver)
    bank1_abrir_menu_exportacao(driver)
    bank1_click_exportar_excel(driver)

    caminho = bank1_aguardar_download(pasta_downloads, pasta_temp)
    return caminho
