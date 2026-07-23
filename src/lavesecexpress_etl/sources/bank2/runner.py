"""
Módulo: runner.py

Responsabilidade
----------------
Orquestrar a extração completa do relatório de recebimentos do Banco 2.

Contexto
--------
Este módulo faz parte da integração do Banco 2.
Ele coordena a sessão Selenium, login, acesso ao relatório, configuração de
datas, envio do relatório e captura do arquivo CSV.

Papel no fluxo do Banco 2
--------------------------
- shared.selenium_session:
    cria a sessão Chrome usada pela automação.

- login.py:
    autentica na plataforma do Banco 2.

- acessar_relatorio.py:
    acessa Relatórios → Lista de recebimentos.

- bank2_definir_ajustar_datas.py:
    abre o seletor, seleciona intervalo de datas, aplica filtro e trata
    particularidades do calendário.

- configurar_email_destino.py:
    configura a opção "Outro e-mail" e preenche o destinatário do relatório.

- bank2_enviar_relatorio.py:
    seleciona CSV, clica em Enviar relatório, aguarda confirmação visual e
    mantém fallback de captura manual pela pasta de downloads.

- download_email.py:
    aguarda o e-mail do Banco 2 chegar no Gmail, extrai o link de download e
    baixa o CSV para a pasta temporária.

- runner.py:
    coordena todas as etapas acima para cada janela de data recebida.

Observações
-----------
Este módulo não transforma nem persiste o arquivo baixado.
Este módulo não lê variáveis de ambiente e não importa settings.py.
As configurações sensíveis devem ser recebidas por parâmetro a partir da ponta
final do processo, como execute_etl.py ou outro orquestrador.
"""

import time
from datetime import datetime, timedelta
from pathlib import Path

# ============================================================
# IMPORTS DA INTEGRAÇÃO BANCO 2
# ============================================================

from lavesecexpress_etl.sources.bank2.login import bank2_login
from lavesecexpress_etl.sources.bank2.acessar_relatorio import bank2_abrir_menu_relatorios

from lavesecexpress_etl.sources.bank2.bank2_definir_ajustar_datas import (
    bank2_abrir_seletor_datas,
    bank2_inputar_intervalo_datas,
    bank2_inputar_intervalo_datas_duplo_inicio,
    bank2_clicar_filtrar,
)

from lavesecexpress_etl.sources.bank2.bank2_enviar_relatorio import (
    bank2_selecionar_formato_csv,
    bank2_click_enviar_relatorio,
    bank2_aguardar_toast,
    bank2_aguardar_download,
)

from lavesecexpress_etl.sources.bank2.configurar_email_destino import (
    configurar_email_destinatario_relatorio_bank2,
)

from lavesecexpress_etl.sources.bank2.download_email import (
    aguardar_e_baixar_relatorio_bank2,
)

from lavesecexpress_etl.shared.selenium_session import iniciar_sessao_chrome


# ============================================================
# RUNNER OFICIAL BANCO 2
# ============================================================

def run_bank2_extraction(
    usuario: str,
    senha: str,
    datas: dict,
    pasta_downloads: str,
    pasta_destino: str,
    login_url: str,
    email_config: dict | None = None,
    email_destino_relatorio: str | None = None,
    usar_download_email: bool = True,
) -> dict:
    """
    Executa a extração do relatório de recebimentos do Banco 2.

    A função cria uma sessão Selenium, autentica no Banco 2, acessa a tela de
    Lista de recebimentos, seleciona CSV e executa uma extração para cada
    janela presente em `datas["date_windows"]`.

    Para cada período:
    1. Seleciona o intervalo de datas.
    2. Aplica o filtro.
    3. Opcionalmente configura o envio para "Outro e-mail".
    4. Clica em "Enviar relatório".
    5. Aguarda confirmação visual.
    6. Tenta baixar o relatório pelo e-mail.
    7. Se falhar, usa fallback de download manual pela pasta de downloads.

    Parameters
    ----------
    usuario : str
        Usuário utilizado para autenticação no Banco 2.

    senha : str
        Senha utilizada para autenticação no Banco 2.

    datas : dict
        Dicionário contendo a chave `date_windows`, com uma lista de períodos.
        Cada período deve conter `start_date` e `end_date`.

    pasta_downloads : str
        Pasta usada pelo navegador para salvar os downloads.

    pasta_destino : str
        Pasta para onde o arquivo baixado será salvo/movido.

    login_url : str
        URL da página de login/home do Banco 2 (config BANK2_LOGIN_URL).

    email_config : dict | None
        Configuração usada pelo módulo de leitura de e-mail.
        Deve conter, quando usado:
        - imap_server
        - imap_port
        - email_user
        - email_password
        - sender
        - subject

    email_destino_relatorio : str | None
        E-mail que deve receber o relatório do Banco 2.
        Quando informado, o runner seleciona a opção "Outro e-mail" no portal.

    usar_download_email : bool
        Define se o runner deve tentar baixar o relatório pelo Gmail.
        Se False, usa apenas o fluxo antigo de download manual.

    Returns
    -------
    dict
        Dicionário com status da execução. Em caso de sucesso, contém o último
        arquivo extraído e a pasta de destino. Em caso de erro, contém a
        mensagem da exceção.

    Notes
    -----
    - O formato CSV é selecionado uma única vez antes do loop de períodos.
    - Cada item de `date_windows` gera uma tentativa de extração.
    - A função retorna apenas o último arquivo baixado.
    - O driver Selenium é encerrado no bloco finally.
    - Este runner não acessa variáveis de ambiente diretamente.
    """

    # O Banco 2 não exige CAPTCHA, token ou outra interação manual. Sua
    # sessão roda em segundo plano; os demais pipelines permanecem visíveis.
    driver = iniciar_sessao_chrome(pasta_downloads, headless=True)

    try:
        # ---------------------------------------------------------
        # LOGIN
        # ---------------------------------------------------------
        bank2_login(driver, usuario, senha, login_url)
        time.sleep(1)

        # ---------------------------------------------------------
        # MENU RELATÓRIOS
        # ---------------------------------------------------------
        bank2_abrir_menu_relatorios(driver)
        time.sleep(1)

        # ---------------------------------------------------------
        # SELECIONA CSV APENAS UMA VEZ
        # ---------------------------------------------------------
        bank2_selecionar_formato_csv(driver)
        time.sleep(0.5)

        ultimo_arquivo = None

        # ---------------------------------------------------------
        # LOOP DE EXTRAÇÕES
        # ---------------------------------------------------------
        for idx, periodo in enumerate(datas["date_windows"], start=1):

            data_inicio = periodo["start_date"]
            data_fim = periodo["end_date"]

            print(
                f"\n🔄 Extração {idx}/{len(datas['date_windows'])} "
                f"{data_inicio} → {data_fim}"
            )

            # -----------------------------------------------------
            # ABRE SELETOR DE DATAS
            # -----------------------------------------------------
            bank2_abrir_seletor_datas(driver)

            # -----------------------------------------------------
            # REGRA ORIGINAL DE DUPLO CLIQUE
            # -----------------------------------------------------
            hoje = datetime.today().date()

            try:
                data_inicio_date = data_inicio.date()
            except AttributeError:
                data_inicio_date = data_inicio

            is_mes_atual = (
                data_inicio_date.year == hoje.year
                and data_inicio_date.month == hoje.month
            )

            is_dia_01 = data_inicio_date.day == 1

            if idx == 1:
                if is_mes_atual and not is_dia_01:
                    bank2_inputar_intervalo_datas_duplo_inicio(
                        driver,
                        data_inicio,
                        data_fim,
                    )
                else:
                    bank2_inputar_intervalo_datas(
                        driver,
                        data_inicio,
                        data_fim,
                    )
            else:
                bank2_inputar_intervalo_datas_duplo_inicio(
                    driver,
                    data_inicio,
                    data_fim,
                )

            # -----------------------------------------------------
            # APLICA FILTRO
            # -----------------------------------------------------
            bank2_clicar_filtrar(driver)

            # -----------------------------------------------------
            # CONFIGURA DESTINATÁRIO DO RELATÓRIO
            # -----------------------------------------------------
            if email_destino_relatorio:
                configurar_email_destinatario_relatorio_bank2(
                    driver=driver,
                    email_destino=email_destino_relatorio,
                )

            # -----------------------------------------------------
            # ENVIA RELATÓRIO
            # -----------------------------------------------------
            momento_envio_relatorio = datetime.now().astimezone()

            bank2_click_enviar_relatorio(driver)
            bank2_aguardar_toast(driver)

            # -----------------------------------------------------
            # CAPTURA RELATÓRIO
            # -----------------------------------------------------
            if usar_download_email and email_config:
                try:
                    ultimo_arquivo = aguardar_e_baixar_relatorio_bank2(
                        email_config=email_config,
                        output_folder=Path(pasta_destino),
                        received_after=(
                            momento_envio_relatorio - timedelta(seconds=5)
                        ),
                        timeout_seconds=600,
                        polling_interval_seconds=15,
                    )

                except Exception as erro_email:
                    print("⚠️ Falha ao baixar relatório pelo e-mail.")
                    print(f"Erro: {erro_email}")
                    print("📥 Usando fallback de download manual...")

                    ultimo_arquivo = bank2_aguardar_download(
                        pasta_downloads=pasta_downloads,
                        pasta_temp=pasta_destino,
                    )
            else:
                ultimo_arquivo = bank2_aguardar_download(
                    pasta_downloads=pasta_downloads,
                    pasta_temp=pasta_destino,
                )

            print(f"📥 Arquivo processado: {ultimo_arquivo}")

            # -----------------------------------------------------
            # PAUSA ENTRE EXTRAÇÕES
            # -----------------------------------------------------
            if idx < len(datas["date_windows"]):
                print("⏳ Aguardando 6 segundos antes da próxima extração...")
                time.sleep(6)

        return {
            "status": "success",
            "arquivo_extraido": str(ultimo_arquivo) if ultimo_arquivo else None,
            "pasta_destino": pasta_destino,
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"{type(e).__name__}: {str(e)}",
        }

    finally:
        try:
            driver.quit()
        except Exception:
            pass
