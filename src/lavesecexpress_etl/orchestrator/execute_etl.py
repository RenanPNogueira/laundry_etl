"""
Módulo: execute_etl.py

Responsabilidade
----------------
Executar o orquestrador principal do ETL da lavanderia.

Contexto
--------
Este módulo é o ponto de entrada principal do projeto. Ele coordena a execução
dos pipelines de ingestão RAW e, ao final, dispara o pipeline de transformação
das camadas Silver, Rules e Gold.
"""

from lavesecexpress_etl.core.database.connection import get_engine
from lavesecexpress_etl.core.database.load_strategy import get_pipeline_mode, get_raw_schema_status
from lavesecexpress_etl.core.database.create_database import create_database_if_not_exists
from lavesecexpress_etl.persistence.raw_structure import ensure_raw_structure
from lavesecexpress_etl.persistence.database_prerequisites import ensure_database_prerequisites

from lavesecexpress_etl.config.settings import DB_CONFIG, validate_settings

from lavesecexpress_etl.pipeline.laundry_system_pipeline import run_laundry_system_pipeline
from lavesecexpress_etl.pipeline.bank1_contacorrente import run_bank1_pipeline
from lavesecexpress_etl.pipeline.bank2_recebimentos import run_bank2_pipeline
from lavesecexpress_etl.pipeline.bank1_faturacartao import run_bank1_faturas_pipeline
from lavesecexpress_etl.pipeline.bank3_contacorrente import run_bank3_pipeline
from lavesecexpress_etl.pipeline.data_transformation import run_pipeline


PIPELINE_OPTIONS = {
    "laundry_system": "Sistema da Lavanderia",
    "bank1_contacorrente": "Banco 1 — Conta Corrente",
    "bank2": "Banco 2 — Recebimentos",
    "bank1_faturacartao": "Banco 1 — Faturas de Cartão",
    "bank3_contacorrente": "Banco 3 — Conta Corrente",
}


PIPELINE_STATUS_DISPLAY = {
    "success": ("✅", "concluído"),
    "failed": ("❌", "falhou"),
    "skipped": ("⏭", "sem arquivo novo"),
    "not_selected": ("⏭", "não selecionado"),
}


def print_execution_summary(pipeline_results, transformation_result):
    """Imprime o resultado consolidado das extrações e transformações."""

    print("\n========== RESUMO DA EXECUÇÃO ==========")

    for pipeline, label in PIPELINE_OPTIONS.items():
        result = pipeline_results[pipeline]
        icon, status_label = PIPELINE_STATUS_DISPLAY[result["status"]]
        line = f"{label:<34} {icon} {status_label}"

        if result.get("detail") and result["status"] == "failed":
            line += f" — {result['detail']}"

        print(line)

    transformation_icon, transformation_label = PIPELINE_STATUS_DISPLAY[
        transformation_result["status"]
    ]
    transformation_line = (
        f"{'Transformações Silver/Rules/Gold':<34} "
        f"{transformation_icon} {transformation_label}"
    )

    if (
        transformation_result.get("detail")
        and transformation_result["status"] == "failed"
    ):
        transformation_line += f" — {transformation_result['detail']}"

    print(transformation_line)
    print("=========================================\n")


def execution_has_failures(execution_result):
    """Indica se alguma extração ou a transformação terminou com erro."""

    pipeline_failed = any(
        result["status"] == "failed"
        for result in execution_result["pipelines"].values()
    )
    transformation_failed = (
        execution_result["transformation"]["status"] == "failed"
    )
    return pipeline_failed or transformation_failed


def select_pipelines_with_timeout(timeout_seconds=30):
    """Exibe um seletor visual e retorna os pipelines marcados pelo usuário.

    Todas as opções começam selecionadas. Quando o tempo se esgota, a seleção
    atual é confirmada automaticamente. Se a interface gráfica não estiver
    disponível, todos os pipelines são selecionados para não bloquear tarefas
    agendadas executadas sem uma sessão gráfica.

    Returns
    -------
    list[str] | None
        Lista de pipelines selecionados. Retorna ``None`` quando o usuário
        cancela ou fecha a janela.
    """

    try:
        import tkinter as tk

        root = tk.Tk()
    except Exception:
        print(
            "[ORQUESTRADOR] Interface de seleção indisponível. "
            "Todos os pipelines serão executados automaticamente."
        )
        return list(PIPELINE_OPTIONS.keys())

    root.title("Lav & Sec Express ETL")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    window_width = 520
    window_height = 430
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    position_x = (screen_width - window_width) // 2
    position_y = (screen_height - window_height) // 2
    root.geometry(
        f"{window_width}x{window_height}+{position_x}+{position_y}"
    )

    selected_result = {"pipelines": None}
    variables = {
        pipeline: tk.BooleanVar(value=True)
        for pipeline in PIPELINE_OPTIONS
    }

    title = tk.Label(
        root,
        text="Selecione as fontes para executar",
        font=("Segoe UI", 14, "bold"),
    )
    title.pack(pady=(22, 6))

    subtitle = tk.Label(
        root,
        text="Todas as fontes estão selecionadas por padrão.",
        font=("Segoe UI", 9),
    )
    subtitle.pack(pady=(0, 14))

    options_frame = tk.Frame(root)
    options_frame.pack(fill="x", padx=54)

    for pipeline, label in PIPELINE_OPTIONS.items():
        checkbox = tk.Checkbutton(
            options_frame,
            text=label,
            variable=variables[pipeline],
            anchor="w",
            font=("Segoe UI", 10),
        )
        checkbox.pack(fill="x", pady=3)

    countdown_text = tk.StringVar()
    countdown_label = tk.Label(
        root,
        textvariable=countdown_text,
        font=("Segoe UI", 10, "bold"),
        fg="#1f5f99",
    )
    countdown_label.pack(pady=(16, 8))

    def set_all(selected):
        for variable in variables.values():
            variable.set(selected)

    def finish_selection():
        selected_result["pipelines"] = [
            pipeline
            for pipeline, variable in variables.items()
            if variable.get()
        ]
        root.destroy()

    def cancel_selection():
        selected_result["pipelines"] = None
        root.destroy()

    def update_countdown(remaining):
        if remaining <= 0:
            finish_selection()
            return

        countdown_text.set(
            f"Execução automática em {remaining} segundo(s)"
        )
        root.after(1000, update_countdown, remaining - 1)

    selection_buttons = tk.Frame(root)
    selection_buttons.pack(pady=(0, 10))

    tk.Button(
        selection_buttons,
        text="Selecionar todas",
        command=lambda: set_all(True),
        width=16,
    ).pack(side="left", padx=5)

    tk.Button(
        selection_buttons,
        text="Desmarcar todas",
        command=lambda: set_all(False),
        width=16,
    ).pack(side="left", padx=5)

    action_buttons = tk.Frame(root)
    action_buttons.pack(pady=(0, 16))

    tk.Button(
        action_buttons,
        text="Cancelar",
        command=cancel_selection,
        width=14,
    ).pack(side="left", padx=6)

    tk.Button(
        action_buttons,
        text="Executar ETL",
        command=finish_selection,
        width=14,
        bg="#1f6f43",
        fg="white",
    ).pack(side="left", padx=6)

    root.protocol("WM_DELETE_WINDOW", cancel_selection)
    root.after(0, update_countdown, max(0, int(timeout_seconds)))
    root.mainloop()

    return selected_result["pipelines"]


def run_orchestrator(mode=None, pipelines_to_run=None):
    """
    Executa o orquestrador principal do ETL.

    Parameters
    ----------
    mode : str | None, default=None
        Modo de execução repassado aos pipelines RAW.

        Valores aceitos:
        - "incremental";
        - "foundation";
        - None.

        Quando None, o modo é definido automaticamente com base no estado
        do schema raw, usando get_pipeline_mode(engine).

    pipelines_to_run : list[str] | None, default=None
        Lista opcional com os nomes dos pipelines RAW que devem ser executados.
        Quando None, todos os pipelines registrados em all_pipelines são
        executados.

    Returns
    -------
    dict
        Resultado consolidado das extrações e da transformação. Pipelines
        individuais podem concluir, falhar, ser ignorados ou não selecionados.
    """

    print("\n========== ORQUESTRADOR START ==========")

    # ============================================================
    # VALIDAÇÃO DE CONFIGURAÇÃO (.env / variáveis de ambiente)
    # ============================================================
    print("\nValidando variáveis de ambiente obrigatórias...")
    validate_settings()

    # ============================================================
    # CONEXÃO CENTRALIZADA COM O BANCO
    # ============================================================
    print("\nValidando existência do database alvo...")
    create_database_if_not_exists(**DB_CONFIG)

    engine = get_engine(**DB_CONFIG)

    print("\nValidando pré-requisitos do database...")
    ensure_database_prerequisites(engine)

    print("\nValidando estrutura RAW...")
    ensure_raw_structure(engine)

    # ============================================================
    # DEFINIÇÃO AUTOMÁTICA DO MODO DE EXECUÇÃO
    # ============================================================
    if mode is None:
        status_raw = get_raw_schema_status(engine)
        mode = get_pipeline_mode(engine)

        print("\nDiagnóstico do schema RAW:")
        print(f"Schema existe? {status_raw['schema_exists']}")
        print(f"Tabelas encontradas: {status_raw['tables']}")
        print(f"Total de tabelas: {status_raw['total_tables']}")
        print(f"Tabelas com dados: {status_raw['tables_with_data']}")
        print(f"Modo recomendado: {mode.upper()}")

    else:
        print(f"\nModo informado manualmente: {mode.upper()}")

    if mode not in ["incremental", "foundation"]:
        raise ValueError(
            "Modo de execução inválido. "
            "Use 'incremental', 'foundation' ou None para modo automático."
        )

    # ============================================================
    # REGISTRO DOS PIPELINES RAW DISPONÍVEIS
    # ============================================================
    all_pipelines = {
        "laundry_system": run_laundry_system_pipeline,
        "bank1_contacorrente": run_bank1_pipeline,
        "bank2": run_bank2_pipeline,
        "bank1_faturacartao": run_bank1_faturas_pipeline,
        "bank3_contacorrente": run_bank3_pipeline,
    }

    if pipelines_to_run is None:
        pipelines_to_run = list(all_pipelines.keys())

    unknown_pipelines = [
        nome for nome in pipelines_to_run if nome not in all_pipelines
    ]
    if unknown_pipelines:
        raise ValueError(
            "Pipelines inexistentes: " + ", ".join(unknown_pipelines)
        )

    pipeline_results = {
        nome: {"status": "not_selected", "detail": None}
        for nome in all_pipelines
    }

    print("\nPipelines selecionados:")
    for nome in pipelines_to_run:
        print(f"- {nome}")

    # ============================================================
    # EXECUÇÃO DOS PIPELINES RAW
    # ============================================================
    for nome in pipelines_to_run:
        print(f"\n🚀 Executando pipeline: {nome.upper()}")
        print(f"Modo: {mode.upper()}")

        try:
            pipeline_result = all_pipelines[nome](engine, mode)

            if (
                isinstance(pipeline_result, dict)
                and pipeline_result.get("status") == "skipped"
            ):
                pipeline_results[nome] = {
                    "status": "skipped",
                    "detail": pipeline_result.get("detail"),
                }
                print(f"⏭ Pipeline {nome.upper()} sem arquivo novo")
            else:
                pipeline_results[nome] = {
                    "status": "success",
                    "detail": None,
                }
                print(f"✅ Pipeline {nome.upper()} finalizado")

        except Exception as exc:
            error_detail = str(exc).strip() or type(exc).__name__
            pipeline_results[nome] = {
                "status": "failed",
                "detail": error_detail,
            }
            print(f"❌ Pipeline {nome.upper()} falhou: {error_detail}")
            print("➡️ O orquestrador seguirá para a próxima fonte.")

    print("\n========== ORQUESTRADOR RAW END ==========\n")

    # ============================================================
    # TRANSFORMAÇÃO PÓS-RAW
    # Silver → Rules → Gold
    # ============================================================
    print("\n========== TRANSFORMATION START ==========")

    try:
        run_pipeline()
        transformation_result = {"status": "success", "detail": None}
        print("\n========== TRANSFORMATION END ==========")

    except Exception as exc:
        error_detail = str(exc).strip() or type(exc).__name__
        transformation_result = {
            "status": "failed",
            "detail": error_detail,
        }
        print(f"❌ Transformação Silver/Rules/Gold falhou: {error_detail}")

    print("\n========== ORQUESTRADOR END ==========\n")

    execution_result = {
        "pipelines": pipeline_results,
        "transformation": transformation_result,
    }
    print_execution_summary(pipeline_results, transformation_result)
    return execution_result


if __name__ == "__main__":
    selected_pipelines = select_pipelines_with_timeout(timeout_seconds=30)

    if selected_pipelines is None:
        print("[ORQUESTRADOR] Execução cancelada pelo usuário.")
    elif not selected_pipelines:
        print("[ORQUESTRADOR] Nenhuma fonte selecionada. ETL não iniciado.")
    else:
        execution_result = run_orchestrator(
            pipelines_to_run=selected_pipelines
        )
        if execution_has_failures(execution_result):
            raise SystemExit(1)
