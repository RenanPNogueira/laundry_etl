# Lav & Sec Express ETL

ETL em Python que consolida dados operacionais da lavanderia e integrações financeiras em PostgreSQL, organizados nas camadas `raw → silver → rules → gold` para consumo no Power BI.

## Documentação

- [Overview do projeto](docs/README.md)
- [Documentação técnica completa](docs/TECHNICAL_DOCUMENTATION.md)
- [Fluxo do processo](docs/PROCESS_FLOW.html)

## Instalação rápida

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Copie `.env.example` para `.env` e preencha as configurações locais. O `.env` contém dados sensíveis e não deve ser versionado.

## Execução

```powershell
python -m lavesecexpress_etl.orchestrator.execute_etl
```

Consulte a [documentação técnica](docs/TECHNICAL_DOCUMENTATION.md) antes da primeira execução.
