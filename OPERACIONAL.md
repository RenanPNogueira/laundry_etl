# ETL da Lavanderia — Guia Operacional

## Sumário

1. [O que é esse projeto](#1-o-que-é-esse-projeto)
2. [Pré-requisitos](#2-pré-requisitos)
3. [Variáveis de ambiente](#3-variáveis-de-ambiente)
4. [Como executar](#4-como-executar)
5. [Pipelines disponíveis](#5-pipelines-disponíveis)
6. [Modos de execução: foundation vs incremental](#6-modos-de-execução-foundation-vs-incremental)
7. [Arquitetura de dados](#7-arquitetura-de-dados)
8. [O que fazer quando algo falha](#8-o-que-fazer-quando-algo-falha)

---

## 1. O que é esse projeto

ETL de uma lavanderia de autoatendimento. O projeto extrai dados de múltiplas fontes, consolida tudo num banco PostgreSQL e estrutura as informações em camadas analíticas prontas para dashboards e análises financeiras/operacionais.

**Fontes de dados:**

| Fonte | O que extrai | Automação |
|---|---|---|
| Sistema da Lavanderia | Vendas, ciclos, clientes, máquinas, lavanderias | Totalmente automático (API REST) |
| Banco 1 | Extrato de conta corrente | Automático (Selenium) |
| Banco 1 | Faturas de cartão de crédito | **Híbrido** — PDFs devem ser colocados manualmente na pasta |
| Banco 2 | Relatório de recebimentos | Automático (Selenium + e-mail Gmail) |
| Banco 3 | Extrato de conta corrente | **Manual** — arquivos devem ser baixados e colocados na pasta |

---

## 2. Pré-requisitos

- Python 3.10+
- PostgreSQL rodando e acessível
- Google Chrome instalado (para as automações Selenium)
- Conta Gmail configurada para receber relatórios do Banco 2
- Pacote `lavesecexpress_etl` instalado no ambiente Python (o antigo `rn_data_core` agora é o módulo interno `lavesecexpress_etl.core`)
- Variáveis de ambiente configuradas (ver seção 3)

**Antes de rodar pela primeira vez:**

Para as fontes manuais/híbridas, verifique se as pastas de entrada existem e têm os arquivos corretos:

- Faturas Banco 1 (PDFs): `data/support/bank1_cartoes/` (caminho relativo à raiz do projeto)
- Conta corrente Banco 3 (arquivos do banco): `data/support/bank3_contacorrente/` (caminho relativo à raiz do projeto)

---

## 3. Variáveis de ambiente

Configure todas as variáveis abaixo antes de executar (copie `.env.example` para `.env` na raiz do projeto e preencha os valores).

### Banco de dados (PostgreSQL)

| Variável | Descrição | Exemplo |
|---|---|---|
| `PG_HOST` | Host do banco | `localhost` |
| `PG_PORT` | Porta | `5432` |
| `PG_USER` | Usuário | `postgres` |
| `PG_PASSWORD` | Senha | `minhasenha` |
| `PG_LSXP_DATABASE` | Nome do banco de dados | `lavesecexpress` |

### Sistema de Lavanderia

| Variável | Descrição |
|---|---|
| `LAUNDRY_SYSTEM_API_KEY` | Chave de autenticação da API do sistema de lavanderia |
| `LAUNDRY_SYSTEM_BUSINESS_ID` | CNPJ da empresa cadastrado no sistema de lavanderia |
| `LAUNDRY_SYSTEM_BASE_URL` | Endpoint base da API do sistema de lavanderia |

### Banco 1 e Banco 2 (credenciais compartilhadas)

| Variável | Descrição |
|---|---|
| `USER_ID` | Usuário de login (usado no Banco 1 e Banco 2) |
| `BANK1_PASSWORD` | Senha do Banco 1 |
| `BANK2_PASSWORD` | Senha do Banco 2 |
| `DOWNLOAD_PATH` | Pasta de downloads padrão do Chrome |

### Banco 2 — recebimento por e-mail

| Variável | Descrição | Padrão |
|---|---|---|
| `BANK2_IMAP_SERVER` | Servidor IMAP do Gmail | — |
| `BANK2_IMAP_PORT` | Porta IMAP | — |
| `BUSINESS_MAIL` | E-mail que recebe o relatório do Banco 2 | — |
| `BUSINESS_MAIL_PSWD` | Senha do aplicativo Gmail (não a senha normal) | — |
| `BANK2_EMAIL_SENDER` | Remetente esperado dos e-mails do Banco 2 | `no_reply@banco2.com.br` |
| `BANK2_EMAIL_SUBJECT` | Assunto esperado dos e-mails do Banco 2 | `Seu relatório chegou!` |
| `BANK2_REPORT_DESTINATION_EMAIL` | E-mail destino informado no portal do Banco 2 | `lavanderia@gmail.com` |
| `BANK2_LOGIN_URL` | URL de login/home do Banco 2 | `<definido-no-env>` |

> **Atenção:** Para o Gmail, `BUSINESS_MAIL_PSWD` deve ser uma **Senha de App** gerada em Conta Google → Segurança → Senhas de app. A senha normal da conta não funciona com IMAP.

### Caminhos de suporte

| Variável | Descrição |
|---|---|
| `SUPPORT_DEFAULT_PATH` | Caminho base do projeto de suporte |
| `BANK1_FATURAS_FOLDER` | Pasta local das faturas de cartão (PDFs) |
| `BANK3_ARQUIVOS_FOLDER` | Pasta local dos extratos do Banco 3 |
| `TEMP_FOLDER` | Pasta temporária usada pelos Bancos 1/2 durante a extração |
| `TEMP_DOWNLOAD_FOLDER` | Pasta temporária usada durante os downloads |

---

## 4. Como executar

### Execução completa (todos os pipelines)

```python
from lavesecexpress_etl.orchestrator.execute_etl import run_orchestrator

run_orchestrator()
```

Quando `mode=None`, o orquestrador detecta automaticamente se deve rodar em modo `foundation` (banco vazio) ou `incremental` (banco com dados).

### Execução com modo explícito

```python
# Carga histórica inicial
run_orchestrator(mode="foundation")

# Atualização incremental
run_orchestrator(mode="incremental")
```

### Executar apenas pipelines específicos

```python
# Apenas o sistema da lavanderia e o Banco 2
run_orchestrator(pipelines_to_run=["laundry_system", "bank2"])

# Apenas a transformação (Silver → Rules → Gold), sem extração
from lavesecexpress_etl.pipeline.data_transformation import run_pipeline
run_pipeline()
```

**Nomes dos pipelines disponíveis:**

| Nome | Descrição |
|---|---|
| `laundry_system` | Sistema da Lavanderia (vendas, ciclos, clientes, máquinas) |
| `bank1_contacorrente` | Extrato conta corrente Banco 1 |
| `bank2` | Relatório de recebimentos Banco 2 |
| `bank1_faturacartao` | Faturas de cartão de crédito (PDFs) |
| `bank3_contacorrente` | Extrato conta corrente Banco 3 |

---

## 5. Pipelines disponíveis

### Sistema da Lavanderia — Totalmente automático

Extrai via API REST. Não requer interação manual.

**Entidades extraídas:** vendas, ciclos, clientes, máquinas, lavanderias.

**Janela de extração (incremental):** busca a partir do maior timestamp registrado na `raw.laundry_system`, com janelas de até 30 dias por chamada.

### Banco 1 — Conta Corrente (Selenium)

Automação via Chrome. O script faz login, navega até Extratos → Conta Corrente, configura o período e exporta o arquivo Excel.

> **Atenção:** O login do Banco 1 pode solicitar um **token manual** (verificação em duas etapas). Se isso acontecer, o Selenium aguarda — você precisa inserir o token no navegador aberto pelo script antes que o timeout expire.

**Janela de extração (incremental):** busca a partir da maior data encontrada em `raw.bank1`.

### Banco 1 — Faturas de Cartão (Híbrido)

O script lê PDFs de uma pasta local. **Os PDFs devem ser baixados manualmente** do portal do Banco 1 e colocados na pasta configurada antes de executar.

**Pasta de entrada:** `data/support/bank1_cartoes/` (relativo à raiz do projeto)

Este pipeline não usa datas — processa todos os PDFs presentes na pasta a cada execução.

### Banco 2 — Recebimentos (Selenium + E-mail)

Automação via Chrome. O script faz login no Banco 2, acessa Lista de Recebimentos, configura o período, seleciona formato CSV e solicita o envio para o e-mail da lavanderia. Em seguida, monitora a caixa de entrada via IMAP e baixa o CSV quando o e-mail chegar.

**Fallback:** se o download por e-mail falhar, o script tenta capturar o arquivo diretamente da pasta de downloads do Chrome.

**Janela de extração (incremental):** parte da maior `data_de_vencimento` em `raw.bank2`, com 60 dias de margem para trás e 90 dias para frente.

### Banco 3 — Conta Corrente (Manual)

Não há automação Selenium para o Banco 3. Os arquivos de extrato devem ser **baixados manualmente** no site do banco e colocados na pasta configurada antes de executar.

**Pasta de entrada:** `data/support/bank3_contacorrente/` (relativo à raiz do projeto)

---

## 6. Modos de execução: foundation vs incremental

| | Foundation | Incremental |
|---|---|---|
| **Quando usar** | Primeira execução, banco vazio ou reconstrução total | Execuções rotineiras |
| **Janela de dados** | Data histórica inicial de cada fonte até 31/12/2025 | A partir do último registro no banco até hoje |
| **Detecção automática** | Quando o schema `raw` está vazio | Quando o schema `raw` já tem dados |
| **Sistema da Lavanderia** | Timestamps históricos desde o início | Timestamps a partir do último registro |
| **Banco 1 / Banco 2** | Banco 1: desde 14/12/2023; Banco 2: desde 27/03/2024 | A partir da maior data da RAW |

> **Atenção:** O `BASELINE_END_DATE` atualmente está fixado em `31/12/2025`. Se precisar rodar o foundation para capturar dados de 2026 em diante, atualize essa data em `shared/selenium_dates.py`.

---

## 7. Arquitetura de dados

O banco PostgreSQL é organizado em quatro schemas:

```
raw       →  dados brutos em JSONB (uma linha por registro original)
silver    →  dados normalizados em colunas tipadas (TRUNCATE + INSERT a cada carga)
rules     →  tabelas auxiliares de categorização (regex, overrides manuais, categorias)
gold      →  dimensões e fatos prontos para análise (TRUNCATE + INSERT a cada carga)
```

### Tabelas por schema

**raw:** `laundry_system`, `bank1`, `bank1_cartao`, `bank2`, `bank3`

**silver:** `laundry_system_vendas`, `laundry_system_ciclos`, `laundry_system_clientes`, `laundry_system_maquinas`, `laundry_system_lavanderias`, `bank1`, `bank1_cartoes`, `bank2`, `bank3`

**rules:** `ajustes_manuais_transacoes`, `regexpadrao_detalhes_transacoes`, `padronizacao_categorias_transacoes`

**gold:**
- Dimensões: `d_bancos`, `d_lavanderias`, `d_clientes`, `d_maquinas`, `d_metodopagamento`, `d_falhas`, `d_voucher`, `d_cupom`
- Fatos: `f_vendas`, `f_ciclos`, `f_contacorrente`, `f_faturacartao`

### Regras de categorização

As transações financeiras (conta corrente e fatura de cartão) são categorizadas em duas etapas:

1. **Regex automático** — padrões definidos em `persistence/regex_bank1_rules.py`, aplicados por prioridade ao texto da transação.
2. **Override manual** — ajustes pontuais por `cd_transacao` (hash MD5 da transação), definidos em `persistence/gold_overridedata.py`.

Para adicionar ou alterar uma categoria, edite o arquivo Python correspondente e reexecute o ETL.

---

## 8. O que fazer quando algo falha

### Erro de conexão com o banco

Verifique as variáveis `PG_*` e confirme que o PostgreSQL está acessível no host/porta configurados.

### Selenium não abre o browser / falha no login

- Verifique se o Chrome está instalado e atualizado.
- Confirme se `USER_ID`, `BANK1_PASSWORD` ou `BANK2_PASSWORD` estão corretos.
- Se o Banco 1 pedir token 2FA, aguarde o navegador abrir e insira o código manualmente.

### Banco 2 — e-mail não chega

- Verifique se `BUSINESS_MAIL` e `BUSINESS_MAIL_PSWD` estão corretos (usar Senha de App, não a senha normal).
- Confirme que `BANK2_IMAP_SERVER` e `BANK2_IMAP_PORT` estão certos (`imap.gmail.com` / `993`).
- O script aguarda até 10 minutos (600 segundos) pelo e-mail. Se ultrapassar, ativa o fallback de download manual.

### Banco 1 Faturas — nenhum dado extraído

- Verifique se há arquivos PDF na pasta `bank1_cartoes`.
- Confirme que os PDFs são exportados diretamente do portal do Banco 1 (o parser é específico para esse formato).

### Banco 3 — nenhum arquivo encontrado

- Verifique se os arquivos de extrato estão na pasta `bank3_contacorrente`.
- O pipeline acusa erro e encerra se a pasta estiver vazia ou inexistente.

### Transformação falha (Silver / Rules / Gold)

A transformação usa estratégia TRUNCATE + INSERT. Se uma etapa falhar, a tabela fica vazia até a próxima execução bem-sucedida. O erro é impresso no console com o nome da tabela afetada. Verifique se os dados na camada RAW estão íntegros antes de reexecutar apenas a transformação:

```python
from lavesecexpress_etl.pipeline.data_transformation import run_pipeline
run_pipeline()
```

### Executar um único pipeline para reprocessar

```python
from lavesecexpress_etl.core.database.connection import get_engine
from lavesecexpress_etl.config.settings import DB_CONFIG
from lavesecexpress_etl.pipeline.bank2_recebimentos import run_bank2_pipeline

engine = get_engine(**DB_CONFIG)
run_bank2_pipeline(engine, mode="incremental")
```

Substitua `run_bank2_pipeline` pelo pipeline desejado e o `mode` conforme necessário.
