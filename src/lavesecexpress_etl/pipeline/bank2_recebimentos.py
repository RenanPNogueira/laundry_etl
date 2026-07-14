"""
Módulo: bank2_recebimentos.py

Responsabilidade
----------------
Executar o pipeline de extração e carga RAW do relatório de recebimentos do
Banco 2.

Contexto
--------
Este módulo faz parte da camada de pipelines do pacote lavesecexpress_etl.
Ele coordena a definição de datas, extração via Selenium, leitura do arquivo
CSV baixado e persistência dos dados brutos na tabela raw.bank2.

Fluxo executado
---------------
1. Define as janelas de datas usando shared.selenium_dates.
2. Executa a extração Selenium com sources.bank2.runner.
3. Configura o envio do relatório para o e-mail da lavanderia.
4. Baixa o relatório recebido por e-mail via integração Gmail.
5. Lê os arquivos baixados na pasta temporária usando transformation_flow.run.
6. Persiste o DataFrame em raw.bank2 usando payload JSONB.
7. Limpa a pasta temporária após a carga.

Observações
-----------
Este pipeline não transforma dados para Silver e não carrega a camada Gold.
Ele atua apenas na ingestão RAW do relatório de recebimentos do Banco 2.

As configurações são importadas do settings.py nesta camada de pipeline e
repassadas como parâmetros para os módulos internos da integração do Banco 2.
"""

from lavesecexpress_etl.core.database.persistence import persist_dataframe_as_payload
from lavesecexpress_etl.core.transformation.transformation_flow import run
from lavesecexpress_etl.core.transformation.delete_folder_files import delete_folder_files

from lavesecexpress_etl.config.settings import (
    BANK2_CONFIG,
    BANK2_EMAIL_CONFIG,
    BANK2_REPORT_DESTINATION_EMAIL,
    temp_folder,
)

from lavesecexpress_etl.shared.selenium_dates import set_extraction_dates
from lavesecexpress_etl.sources.bank2.runner import run_bank2_extraction


def run_bank2_pipeline(engine, mode="incremental"):
    """
    Executa o pipeline de extração e carga RAW dos recebimentos do Banco 2.

    Parameters
    ----------
    engine
        SQLAlchemy Engine conectado ao banco PostgreSQL.

    mode : str, default="incremental"
        Modo de execução da extração. Valores esperados:
        - "incremental";
        - "foundation".

    Returns
    -------
    None
        A função não retorna valor. Ela executa a extração, leitura do arquivo
        e persistência dos dados brutos em raw.bank2.

    Notes
    -----
    - As credenciais e pasta de download do Banco 2 vêm de BANK2_CONFIG.
    - As configurações do Gmail vêm de BANK2_EMAIL_CONFIG.
    - O e-mail destino do relatório vem de BANK2_REPORT_DESTINATION_EMAIL.
    - As datas vêm de set_extraction_dates.
    - O arquivo baixado é lido a partir de temp_folder.
    - A persistência usa payload JSONB e hashid via lavesecexpress_etl.core.
    - A pasta temporária é limpa ao final da carga.
    """

    print(f"\n========== BANK2 PIPELINE START | MODE: {mode.upper()} ==========")

    # -----------------------------------
    # 1 - DEFINE DATAS
    # -----------------------------------
    datas = set_extraction_dates(mode, engine)
    datas_bank2 = datas["bank2"]

    # -----------------------------------
    # 2 - EXTRACT (SELENIUM + EMAIL)
    # -----------------------------------
    resultado_extracao = run_bank2_extraction(
        usuario=BANK2_CONFIG["usuario"],
        senha=BANK2_CONFIG["senha"],
        datas=datas_bank2,
        pasta_downloads=BANK2_CONFIG["pasta_downloads"],
        pasta_destino=temp_folder,
        login_url=BANK2_CONFIG["login_url"],
        email_config=BANK2_EMAIL_CONFIG,
        email_destino_relatorio=BANK2_REPORT_DESTINATION_EMAIL,
        usar_download_email=True,
    )

    if resultado_extracao.get("status") != "success":
        raise RuntimeError(
            "[BANK2] Falha na extração do Banco 2. "
            f"Detalhe: {resultado_extracao.get('message')}"
        )

    print("[BANK2] Extração concluída.")
    print(f"[BANK2] Último arquivo extraído: {resultado_extracao.get('arquivo_extraido')}")

    # -----------------------------------
    # 3 - LEITURA
    # -----------------------------------
    data = run(
        temp_folder,
        lambda _: "bank2_recebimentos",
    )

    df = data["bank2_recebimentos"]

    # -----------------------------------
    # 4 - LOAD (RAW)
    # -----------------------------------
    inserted = persist_dataframe_as_payload(
        engine=engine,
        schema="raw",
        table="bank2",
        dataframe=df,
    )

    # -----------------------------------
    # 5 - LIMPEZA DA PASTA TEMPORÁRIA
    # -----------------------------------
    delete_folder_files(temp_folder)

    print(f"[BANK2] {inserted} registros inseridos na raw.bank2.")
    print("========== BANK2 PIPELINE END ==========\n")
