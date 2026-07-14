# lavesecexpress_etl

ETL de uma lavanderia de autoatendimento: consolida o sistema de gestão da lavanderia e integrações bancárias (Banco 1, Banco 2, Banco 3) num banco PostgreSQL, em camadas `raw → silver → rules → gold`, prontas para análise em Power BI.

Para o guia completo de operação (variáveis de ambiente, como executar, o que fazer quando algo falha), veja [`OPERACIONAL.md`](./OPERACIONAL.md).

## Estrutura do projeto

```
src/lavesecexpress_etl/
    config/         configurações e variáveis de ambiente
    core/           fundação técnica reutilizável (conexão, persistência RAW, leitura/limpeza de arquivos)
    sources/        extração por fonte (sistema da lavanderia, Banco 1, Banco 2, Banco 3)
    pipeline/        orquestração da ingestão RAW e da transformação Silver/Rules/Gold, por fonte
    persistence/    DDLs e loaders das camadas silver/rules/gold
    orchestrator/   ponto de entrada principal do ETL
    shared/         utilitários usados por mais de uma fonte (sessão Selenium, cálculo de datas)
```

## Instalação

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

Copie `.env.example` para `.env` e preencha as variáveis (ver `OPERACIONAL.md`, seção 3).

## Execução

```python
from lavesecexpress_etl.orchestrator.execute_etl import run_orchestrator
run_orchestrator()
```
