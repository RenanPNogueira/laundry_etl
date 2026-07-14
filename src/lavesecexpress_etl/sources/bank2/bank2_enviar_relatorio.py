"""
Módulo: bank2_enviar_relatorio.py

Responsabilidade
----------------
Solicitar e capturar o relatório de recebimentos do Banco 2 em formato CSV.

Contexto
--------
Este módulo faz parte da integração do Banco 2. Ele é executado após o
login, acesso à tela Lista de recebimentos e definição do intervalo de
datas do relatório.

Papel no fluxo do Banco 2
--------------------------
- login.py:
    autentica o usuário no Banco 2.

- acessar_relatorio.py:
    acessa Relatórios → Lista de recebimentos.

- bank2_definir_ajustar_datas.py:
    seleciona e aplica o intervalo de datas.

- bank2_enviar_relatorio.py:
    seleciona o formato CSV, clica em Enviar relatório, aguarda confirmação
    visual e monitora a pasta de downloads até capturar o arquivo.

Principais componentes
----------------------
- bank2_selecionar_formato_csv:
    seleciona o formato do relatório, por padrão CSV.

- bank2_click_enviar_relatorio:
    clica no botão Enviar relatório.

- bank2_aguardar_toast:
    aguarda mensagem de confirmação do envio do relatório.

- bank2_aguardar_download:
    monitora a pasta de downloads, identifica o arquivo do Banco 2, renomeia
    e move para a pasta temporária do pipeline.

Observações
-----------
Este módulo não fecha o navegador. Ele foi desenhado para uso em fluxos com
múltiplas extrações na mesma sessão Selenium.
"""



import os
import time
import shutil
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def bank2_selecionar_formato_csv(driver, formato="csv"):
    print("📄 Selecionando formato CSV...")

    WebDriverWait(driver, 30).until(
        EC.url_contains("/relatorios/enviar-relatorio")
    )

    xpath_formato = f"//label[@for='text/{formato}']"

    opcao = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, xpath_formato))
    )

    driver.execute_script("arguments[0].click();", opcao)
    print(f"✅ Formato {formato.upper()} selecionado.")


def bank2_click_enviar_relatorio(driver):
    print("📤 Clicando em 'Enviar relatório'...")

    botao = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//span[contains(text(),'Enviar relatório')]/ancestor::button")
        )
    )

    driver.execute_script("arguments[0].click();", botao)


def bank2_aguardar_toast(driver):
    print("⏳ Aguardando toast de confirmação...")

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (By.XPATH, "//p[contains(text(),'relatório vai ser enviado')]")
            )
        )
        print("📨 Toast detectado: relatório enviado.")
    except:
        print("⚠️ Toast não apareceu — mas o clique foi realizado.")


def bank2_aguardar_download(pasta_downloads, pasta_temp, timeout=600):
    """
    Aguarda manualmente até que o arquivo do Banco 2 apareça na pasta de downloads.
    Move e renomeia com convenção:
        bank2-recebimentos-YYYY-MM-DD_HH-MM-SS.csv
    """
    import os
    import time
    import shutil

    print(f"📥 Aguardando download manual por até {timeout//60} minutos...")

    inicio = time.time()
    arquivo_encontrado = None

    while time.time() - inicio < timeout:

        for nome in os.listdir(pasta_downloads):
            if nome.startswith("relatorio-recebimentos-") and nome.endswith(".csv"):

                origem = os.path.join(pasta_downloads, nome)

                timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
                novo_nome = f"bank2_recebimentos_{timestamp}.csv"
                destino = os.path.join(pasta_temp, novo_nome)

                shutil.move(origem, destino)

                print(f"✅ Download detectado e movido para: {destino}")
                return destino

        time.sleep(2)

    print("⚠ Nenhum arquivo detectado dentro do tempo limite.")
    return None
