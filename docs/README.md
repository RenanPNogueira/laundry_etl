# Overview — Lav & Sec Express ETL

## O que é o projeto

O Lav & Sec Express ETL é um processo de integração de dados desenvolvido em Python. Ele reúne informações operacionais da lavanderia e movimentações financeiras de diferentes fontes em um banco PostgreSQL único.

O resultado é organizado para análise no Power BI.

## O que o projeto resolve

Antes da consolidação, os dados ficam distribuídos entre:

- Sistema de gestão da lavanderia;
- Extratos de conta corrente;
- Relatórios de recebimentos;
- Faturas de cartão;
- Arquivos bancários obtidos manualmente.

O ETL automatiza ou organiza a coleta dessas fontes, preserva os dados originais e produz tabelas padronizadas para análise financeira e operacional.

## Fontes integradas

| Fonte | Forma de entrada | Nível de automação |
|---|---|---|
| Sistema da Lavanderia | API REST | Automático |
| Banco 1 — conta corrente | Selenium e arquivo Excel | Automático, com possível token manual |
| Banco 2 — recebimentos | Selenium e e-mail | Automático, dependente do recebimento do relatório |
| Banco 1 — faturas de cartão | PDFs em pasta local | Híbrido |
| Banco 3 — conta corrente | Arquivo em pasta local | Manual |

## Fluxo geral

```text
Iniciar o orquestrador
        ↓
Validar configurações e PostgreSQL
        ↓
Definir carga foundation ou incremental
        ↓
Executar os pipelines de ingestão
        ↓
Armazenar dados brutos na RAW
        ↓
Transformar RAW → Silver → Rules → Gold
        ↓
Disponibilizar os dados para o Power BI
```

## Camadas de dados

| Camada | Papel |
|---|---|
| `raw` | Preserva os registros extraídos em JSONB e controla duplicidade |
| `silver` | Estrutura e tipa os dados brutos |
| `rules` | Mantém regras auxiliares de categorização |
| `gold` | Produz dimensões e fatos para análise |

## Estrutura do repositório

```text
data/        arquivos locais de suporte e temporários, não publicados no Git
docs/        documentação geral, técnica e visual
migrations/  alterações pontuais e históricas na estrutura do PostgreSQL
scripts/     ferramentas manuais de diagnóstico e manutenção
src/         código-fonte do pacote Python
```

## Documentos

- [Documentação técnica completa](TECHNICAL_DOCUMENTATION.md): instalação, configuração, execução, arquitetura e troubleshooting.
- [Fluxo do processo](PROCESS_FLOW.html): representação visual e não técnica do funcionamento do ETL.
- [README da raiz](../README.md): entrada rápida do repositório.

## Segurança e dados locais

- O arquivo `.env` possui credenciais reais e permanece fora do Git.
- O `.env.example` contém apenas o modelo das configurações.
- Arquivos financeiros em `data/` são ignorados pelo Git.
- Regras com informações sensíveis de negócio também são ignoradas conforme o `.gitignore`.

## Instalação e operação

Para instalar, configurar ou executar o projeto, consulte a [documentação técnica completa](TECHNICAL_DOCUMENTATION.md).
