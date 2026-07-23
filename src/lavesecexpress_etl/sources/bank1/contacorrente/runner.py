"""
Módulo: runner.py

Responsabilidade
----------------
Orquestrar a extração completa do extrato de Conta Corrente do Banco 1.

Contexto
--------
Este módulo faz parte da integração do Banco 1. Ele reúne as etapas Selenium
necessárias para autenticar no internet banking, navegar até a tela de
extratos, configurar períodos, exportar arquivos Excel e retornar os
caminhos dos arquivos baixados.

Papel no fluxo do Banco 1
--------------------------
- shared.selenium_session:
    cria a sessão Chrome usada pela automação.

- login.py:
    autentica no Banco 1, incluindo usuário, senha e token manual.

- navegar_menu.py:
    acessa Extratos → Conta Corrente.

- configurar_datas.py:
    seleciona o período "Específico" e preenche data inicial e final.

- bank1_export.py:
    executa Buscar, Exportar Excel e aguarda o download do arquivo.

- runner.py:
    coordena todas as etapas acima para cada janela de data recebida.

Principais componentes
----------------------
- run_bank1_extraction:
    executa a extração do Banco 1 para uma ou mais janelas de datas.

Observações
-----------
Este módulo mantém a extração em nível operacional. Ele não transforma o
arquivo baixado e não persiste dados no banco. Essas etapas devem ocorrer em
camadas posteriores do pipeline.
"""

from datetime import datetime, date

from lavesecexpress_etl.sources.bank1.contacorrente.login import bank1_login
from lavesecexpress_etl.sources.bank1.contacorrente.navegar_menu import bank1_navegar_menu_extratos
from lavesecexpress_etl.sources.bank1.contacorrente.configurar_datas import bank1_configurar_periodo

from lavesecexpress_etl.sources.bank1.contacorrente.bank1_export import (
    bank1_click_buscar,
    bank1_abrir_menu_exportacao,
    bank1_click_exportar_excel,
    bank1_aguardar_download,
)

from lavesecexpress_etl.shared.selenium_session import iniciar_sessao_chrome


def run_bank1_extraction(
    usuario: str,
    senha: str,
    datas: dict,
    pasta_downloads: str,
    pasta_destino: str,
    login_url: str,
) -> list[dict]:

    """
        Executa a extração do extrato de Conta Corrente do Banco 1.

        A função cria uma sessão Selenium, realiza login no Banco 1, navega até a
        tela de extratos e executa a exportação de arquivos Excel para cada janela
        de datas informada em `datas["date_windows"]`.

        Parameters
        ----------
        usuario : str
            Usuário utilizado para autenticação no Banco 1.

        senha : str
            Senha utilizada para autenticação no Banco 1.

        datas : dict
            Dicionário contendo a chave `date_windows`, com uma lista de períodos.
            Cada período deve conter `start_date` e `end_date`.

        pasta_downloads : str
            Pasta usada pelo navegador para salvar os downloads.

        pasta_destino : str
            Pasta para onde os arquivos baixados serão movidos após a detecção.

        login_url : str
            URL do Internet Banking do Banco 1 (config BANK1_LOGIN_URL).

        Returns
        -------
        list[dict]
            Lista de resultados por período extraído. Cada item contém:
            - index;
            - inicio;
            - fim;
            - arquivo.

        Raises
        ------
        RuntimeError
            Quando credenciais ou pastas obrigatórias não são informadas.

        Notes
        -----
        - O login é feito uma única vez por execução.
        - O mesmo driver é reutilizado para todas as janelas.
        - O driver é encerrado no bloco finally.
        - A função não transforma nem persiste os arquivos baixados.
    """

    if not usuario or not senha:
        raise RuntimeError("Credenciais do Banco 1 não informadas.")

    if not pasta_downloads:
        raise RuntimeError("'pasta_downloads' não informado.")

    if not pasta_destino:
        raise RuntimeError("'pasta_destino' não informado.")

    periodos = datas.get("date_windows", [])

    if not periodos:
        print("⚠️ Nenhum período informado. Nada a extrair.")
        return []

    driver = iniciar_sessao_chrome(pasta_downloads)

    try:
        # ---------------------------------------------------------
        # LOGIN
        # ---------------------------------------------------------
        bank1_login(driver, usuario, senha, login_url)

        # ---------------------------------------------------------
        # NAVEGAÇÃO
        # ---------------------------------------------------------
        bank1_navegar_menu_extratos(driver)

        resultados = []

        # ---------------------------------------------------------
        # LOOP DE EXTRAÇÕES
        # ---------------------------------------------------------
        for idx, periodo in enumerate(periodos, start=1):

            di = periodo["start_date"]
            df = periodo["end_date"]

            # Garantia de datetime (igual original)
            if isinstance(di, date) and not isinstance(di, datetime):
                di = datetime(di.year, di.month, di.day)

            if isinstance(df, date) and not isinstance(df, datetime):
                df = datetime(df.year, df.month, df.day)

            print(
                f"\n📆 Extração {idx}/{len(periodos)} — "
                f"{di.date()} até {df.date()}"
            )

            # Configura período
            bank1_configurar_periodo(driver, di, df)

            # Buscar
            bank1_click_buscar(driver)

            # Exportar Excel
            bank1_abrir_menu_exportacao(driver)
            bank1_click_exportar_excel(driver)

            # Download
            caminho = bank1_aguardar_download(
                pasta_downloads,
                pasta_destino,
            )

            resultados.append(
                {
                    "index": idx,
                    "inicio": di.date(),
                    "fim": df.date(),
                    "arquivo": caminho,
                }
            )

        print("\n🎉 Extrações do Banco 1 concluídas com sucesso.\n")

        return resultados

    finally:
        try:
            driver.quit()
        except:
            pass
