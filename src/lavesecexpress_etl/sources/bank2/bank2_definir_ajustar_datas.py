"""
Módulo: bank2_definir_ajustar_datas.py

Responsabilidade
----------------
Configurar o intervalo de datas no relatório de Lista de recebimentos do
Banco 2 usando Selenium.

Contexto
--------
Este módulo faz parte da integração do Banco 2. Ele é executado após o login
e após o acesso à tela Relatórios → Lista de recebimentos.

Papel no fluxo do Banco 2
--------------------------
- login.py:
    autentica o usuário no Banco 2.

- acessar_relatorio.py:
    acessa a tela de Lista de recebimentos.

- bank2_definir_ajustar_datas.py:
    abre o seletor de datas, navega entre meses, seleciona data inicial e
    final, limpa filtros anteriores quando necessário e confirma o filtro.

- exportação/download:
    etapa posterior responsável por solicitar e capturar o relatório.

Principais componentes
----------------------
- interpretar_mes_raw_para_datetime:
    interpreta o mês/ano exibido no calendário, incluindo correções para
    textos corrompidos como "marasso".

- normalizar_mes_raw:
    normaliza o texto bruto do mês antes da interpretação.

- esperar_mes_raw:
    lê o mês/ano visível no calendário usando aria-label.

- bank2_abrir_seletor_datas:
    abre o componente de seleção de datas.

- bank2_inputar_intervalo_datas:
    seleciona intervalo de datas no calendário.

- bank2_inputar_intervalo_datas_duplo_inicio:
    seleciona intervalo com duplo clique no dia inicial, usado em cenários
    onde o calendário do Banco 2 apresenta comportamento instável.

- bank2_clicar_filtrar:
    confirma o intervalo escolhido.

- bank2_clicar_limpar:
    limpa o intervalo anterior no seletor de datas.

Observações
-----------
Este módulo contém regras específicas da interface do Banco 2 e deve ser
mantido dentro da integração do Banco 2.
"""

import os
import time
import shutil
import unicodedata
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


# =============================================================
# 1️⃣ Função sistêmica — interpretar mês bugado do Banco 2 (COPIADA)
# =============================================================
def interpretar_mes_raw_para_datetime(mes_raw):
    """
    Recebe o texto do mês que aparece no Banco 2 (às vezes bugado, ex: 'marasso')
    e devolve um objeto datetime referente ao primeiro dia daquele mês/ano.

    Exemplo de mes_raw esperado: "março 2025", "marasso 2025", "abril 2024".
    """

    # Normaliza acentos / caracteres esquisitos
    mes_raw_norm = unicodedata.normalize("NFKD", mes_raw).encode("ascii", "ignore").decode("ascii")
    mes_raw_norm = mes_raw_norm.lower().strip()

    partes = mes_raw_norm.split()
    if len(partes) != 2:
        raise ValueError(f"Formato inesperado de mes_raw: {mes_raw}")

    nome_mes_raw, ano_str = partes
    ano = int(ano_str)

    # Mapa de possíveis corrupções → mês correto
    mapa_correcao = {
        "janeiro": "janeiro",
        "fevereiro": "fevereiro",
        "marco": "marco",       # normal
        "marcoo": "marco",      # exemplos de zoeira...
        "marc": "marco",
        "marasso": "marco",
        "abril": "abril",
        "maio": "maio",
        "junho": "junho",
        "julho": "julho",
        "agosto": "agosto",
        "setembro": "setembro",
        "outubro": "outubro",
        "novembro": "novembro",
        "dezembro": "dezembro",
    }

    nome_mes_limpo = mapa_correcao.get(nome_mes_raw, nome_mes_raw)

    meses = {
        "janeiro": 1,
        "fevereiro": 2,
        "marco": 3,
        "abril": 4,
        "maio": 5,
        "junho": 6,
        "julho": 7,
        "agosto": 8,
        "setembro": 9,
        "outubro": 10,
        "novembro": 11,
        "dezembro": 12,
    }

    if nome_mes_limpo not in meses:
        raise ValueError(f"Não foi possível mapear o mês: {mes_raw} (normalizado: {nome_mes_limpo})")

    return datetime(ano, meses[nome_mes_limpo], 1)


def normalizar_mes_raw(texto: str) -> str:
    """
    Normaliza o texto do calendário ANTES de enviar para interpretar_mes_raw_para_datetime.
    Remove caracteres inválidos e garante 'mes ano' limpo.
    """
    if not texto:
        return ""

    # import unicodedata

    # Remove acentos e sujeira
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    t = t.lower().strip()

    # Garantir formato "mes ano"
    partes = t.split()
    if len(partes) < 2:
        return t

    mes = partes[0]
    ano = partes[-1]  # às vezes vem duplicado, pegamos o último número

    return f"{mes} {ano}"


def esperar_mes_raw(driver, timeout=10):
    """
    Lê o mês/ano visível no calendário do Banco 2 usando aria-label,
    que funciona mesmo com o navegador minimizado.
    """
    XPATH_TABLE = "//table[@role='grid']"
    wait = WebDriverWait(driver, timeout)

    for _ in range(timeout * 4):
        try:
            tabela = wait.until(EC.presence_of_element_located((By.XPATH, XPATH_TABLE)))
            texto = tabela.get_attribute("aria-label")

            if texto and texto.strip():
                return texto.strip()

        except:
            pass

        time.sleep(0.25)

    raise Exception("mes_raw permaneceu vazio após timeout.")


# =============================================================
# 2️⃣ Selecionar intervalo de datas no Banco 2 (COPIADO / ADAPTADO)
# =============================================================
def bank2_abrir_seletor_datas(driver):
    """
    Abre o seletor de datas do Banco 2.
    """
    print("📆 Abrindo seletor de datas no Banco 2...")

    seletor_data = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//div[contains(@class,'jade-content-navigator-content__title')]")
        )
    )
    driver.execute_script("arguments[0].click();", seletor_data)

    print("📅 Seletor de datas aberto.")
    time.sleep(0.4)


def bank2_inputar_intervalo_datas(driver, data_inicio, data_fim):
    """
    Seleciona o intervalo de datas no calendário do Banco 2.
    NÃO abre o seletor — isso deve ser feito antes.
    """
    wait = WebDriverWait(driver, 20)

    # ======================================================
    # 1️⃣ Selecionar mês/ano de início (calendário esquerdo)
    # ======================================================
    while True:
        mes_raw = esperar_mes_raw(driver)
        mes_visivel_raw = normalizar_mes_raw(mes_raw)

        if not mes_visivel_raw:
            continue

        mes_visivel = interpretar_mes_raw_para_datetime(mes_visivel_raw)
        alvo = datetime(data_inicio.year, data_inicio.month, 1)

        if mes_visivel.year == alvo.year and mes_visivel.month == alvo.month:
            break

        if mes_visivel > alvo:
            btn_anterior = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[@aria-label='Mês anterior']")))
            driver.execute_script("arguments[0].click();", btn_anterior)
        else:
            btn_proximo = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[@aria-label='Próximo mês']")))
            driver.execute_script("arguments[0].click();", btn_proximo)

        time.sleep(0.4)

    # Selecionar dia de início
    xpath_inicio = f"//td[@data-day='{data_inicio.strftime('%Y-%m-%d')}']/button"
    elem_inicio = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_inicio)))
    driver.execute_script("arguments[0].click();", elem_inicio)
    time.sleep(0.6)

    # ======================================================
    # 2️⃣ Selecionar mês/ano de fim (calendário direito)
    # ======================================================
    while True:
        mes_raw = esperar_mes_raw(driver)
        mes_visivel_raw = normalizar_mes_raw(mes_raw)

        if not mes_visivel_raw:
            continue

        mes_visivel = interpretar_mes_raw_para_datetime(mes_visivel_raw)
        alvo = datetime(data_fim.year, data_fim.month, 1)   # <-- AQUI ESTAVA O BUG

        if mes_visivel.year == alvo.year and mes_visivel.month == alvo.month:
            break

        btn_proximo = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[@aria-label='Próximo mês']")))
        driver.execute_script("arguments[0].click();", btn_proximo)
        time.sleep(0.4)

    xpath_fim = f"//td[@data-day='{data_fim.strftime('%Y-%m-%d')}']/button"
    elem_fim = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_fim)))
    driver.execute_script("arguments[0].click();", elem_fim)
    time.sleep(0.6)

    print("✅ Intervalo de datas selecionado com sucesso.")


def bank2_inputar_intervalo_datas_duplo_inicio(driver, data_inicio, data_fim):
    """
    Seleciona intervalo de datas no calendário do Banco 2 fazendo
    DUAS VEZES o clique no dia de início.
    Necessário a partir da segunda extração devido ao bug do site.
    NÃO abre o seletor — isso deve ser feito antes.
    """

    print("📆 Iniciando seleção de intervalo com duplo clique no início...")

    wait = WebDriverWait(driver, 20)

    # ======================================================
    # 1️⃣ Selecionar mês/ano de início (calendário esquerdo)
    # ======================================================
    while True:
        mes_raw = esperar_mes_raw(driver)
        mes_visivel_raw = normalizar_mes_raw(mes_raw)

        if not mes_visivel_raw:
            continue  # tenta de novo

        mes_visivel = interpretar_mes_raw_para_datetime(mes_visivel_raw)
        alvo = datetime(data_inicio.year, data_inicio.month, 1)

        if mes_visivel.year == alvo.year and mes_visivel.month == alvo.month:
            break

        if mes_visivel > alvo:
            btn_anterior = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[@aria-label='Mês anterior']")))
            driver.execute_script("arguments[0].click();", btn_anterior)
        else:
            btn_proximo = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[@aria-label='Próximo mês']")))
            driver.execute_script("arguments[0].click();", btn_proximo)

        time.sleep(0.4)

    # 🌟 DUAS VEZES O CLIQUE NO DIA DE INÍCIO
    xpath_inicio = f"//td[@data-day='{data_inicio.strftime('%Y-%m-%d')}']/button"
    elem_inicio = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_inicio)))

    driver.execute_script("arguments[0].click();", elem_inicio)
    time.sleep(0.3)
    driver.execute_script("arguments[0].click();", elem_inicio)
    time.sleep(0.5)

    # ======================================================
    # 2️⃣ Selecionar mês/ano de fim (calendário direito)
    # ======================================================
    while True:
        mes_raw = esperar_mes_raw(driver)
        mes_visivel_raw = normalizar_mes_raw(mes_raw)

        if not mes_visivel_raw:
            continue  # tenta de novo

        mes_visivel = interpretar_mes_raw_para_datetime(mes_visivel_raw)
        alvo = datetime(data_fim.year, data_fim.month, 1)   # <-- AQUI ESTAVA O BUG

        if mes_visivel.year == alvo.year and mes_visivel.month == alvo.month:
            break

        btn_proximo = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[@aria-label='Próximo mês']")))
        driver.execute_script("arguments[0].click();", btn_proximo)
        time.sleep(0.4)

    xpath_fim = f"//td[@data-day='{data_fim.strftime('%Y-%m-%d')}']/button"
    elem_fim = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_fim)))
    driver.execute_script("arguments[0].click();", elem_fim)
    time.sleep(0.5)

    print("✅ Intervalo de datas (duplo clique no início) selecionado com sucesso.")


def bank2_clicar_filtrar(driver):
    """
    Clica no botão 'Filtrar' no componente de seleção de datas do Banco 2.
    Essa ação confirma o intervalo de datas escolhido.
    """

    print("🔎 Procurando botão 'Filtrar'...")

    wait = WebDriverWait(driver, 20)

    try:
        # Botão principal de ação com o texto 'Filtrar'
        botao_filtrar = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[.//span[text()='Filtrar']]")
            )
        )

        driver.execute_script("arguments[0].click();", botao_filtrar)
        print("🚀 Botão 'Filtrar' clicado com sucesso.")
        time.sleep(0.5)

    except TimeoutException:
        raise TimeoutException("⛔ Não foi possível encontrar o botão 'Filtrar' no Banco 2.")


def bank2_clicar_limpar(driver):
    """
    Clica no botão 'Limpar' dentro do seletor de datas do Banco 2.
    Necessário quando estamos realizando mais de uma extração no mesmo fluxo.
    """

    print("🧼 Procurando botão 'Limpar' no seletor de datas...")

    wait = WebDriverWait(driver, 20)

    try:
        # O botão possui a label exata 'Limpar'
        botao_limpar = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[.//span[text()='Limpar']]")
            )
        )

        driver.execute_script("arguments[0].click();", botao_limpar)
        print("🧽 Botão 'Limpar' clicado com sucesso.")
        time.sleep(0.4)

    except TimeoutException:
        raise TimeoutException("⛔ Não foi possível encontrar o botão 'Limpar' no Banco 2.")
