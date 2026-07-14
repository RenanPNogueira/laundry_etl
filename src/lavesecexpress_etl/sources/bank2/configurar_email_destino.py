from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def configurar_email_destinatario_relatorio_bank2(
    driver,
    email_destino: str,
    timeout: int = 20,
) -> None:
    """
    Configura o relatório do Banco 2 para ser enviado para 'Outro e-mail'.

    Fluxo:
    1. Seleciona a opção 'Outro e-mail'.
    2. Aguarda o campo de e-mail aparecer.
    3. Preenche o e-mail de destino.
    4. Aguarda o botão 'Enviar relatório' ficar habilitado.

    Parameters
    ----------
    driver
        Instância ativa do Selenium WebDriver.

    email_destino : str
        E-mail que deve receber o relatório.

    timeout : int
        Tempo máximo de espera pelos elementos.
    """

    if not email_destino:
        raise ValueError("O e-mail destino do relatório do Banco 2 não foi informado.")

    wait = WebDriverWait(driver, timeout)

    print("📧 Configurando envio do relatório para outro e-mail...")

    # ------------------------------------------------------------
    # 1. Seleciona a opção "Outro e-mail"
    # ------------------------------------------------------------
    opcao_outro_email = wait.until(
        EC.element_to_be_clickable(
            (
                By.CSS_SELECTOR,
                "label[for='other-email']",
            )
        )
    )

    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'center'});",
        opcao_outro_email,
    )

    driver.execute_script(
        "arguments[0].click();",
        opcao_outro_email,
    )

    print("✅ Opção 'Outro e-mail' selecionada.")

    # ------------------------------------------------------------
    # 2. Confirma que o radio foi selecionado
    # ------------------------------------------------------------
    radio_outro_email = wait.until(
        EC.presence_of_element_located(
            (
                By.CSS_SELECTOR,
                "input#other-email[name='recipient-email']",
            )
        )
    )

    if not radio_outro_email.is_selected():
        driver.execute_script(
            "arguments[0].click();",
            radio_outro_email,
        )

    print("✅ Radio 'Outro e-mail' confirmado.")

    # ------------------------------------------------------------
    # 3. Aguarda o campo de e-mail aparecer
    # ------------------------------------------------------------
    campo_email = wait.until(
        EC.visibility_of_element_located(
            (
                By.CSS_SELECTOR,
                "input[placeholder='destinatario@email.com']",
            )
        )
    )

    # ------------------------------------------------------------
    # 4. Preenche o e-mail destino
    # ------------------------------------------------------------
    valor_atual = campo_email.get_attribute("value") or ""

    if valor_atual.strip().lower() != email_destino.strip().lower():
        campo_email.clear()
        campo_email.send_keys(email_destino)
        print(f"✅ E-mail destino preenchido: {email_destino}")
    else:
        print("✅ E-mail destino já estava preenchido corretamente.")

    # ------------------------------------------------------------
    # 5. Aguarda o botão 'Enviar relatório' ficar habilitado
    # ------------------------------------------------------------
    botao_enviar = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//button[contains(normalize-space(.), 'Enviar relatório')]",
            )
        )
    )

    print("✅ Botão 'Enviar relatório' disponível para envio.")
