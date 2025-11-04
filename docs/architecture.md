# Plano Arquitetural – Tech Challenge Books API

## Visão de Alto Nível

```
┌──────────┐     ┌────────────┐     ┌───────────┐     ┌──────────────┐
│  Source  │     │ Ingestion  │     │ Storage   │     │ Serving/API  │
│ (Books   ├────►│ Scraper    ├────►│ CSV +     ├────►│ FastAPI      │
│  to Scrape)│   │ (scripts/  │     │ SQLite    │     │ (/api/v1 &   │
└──────────┘     │ scrape_    │     │ (data/)   │     │  /ml/*)      │
                  │ books.py) │     └────┬──────┘     │ Uvicorn      │
                  └────┬──────┘          │             └────┬─────────┘
                       │                 │                  ▼
                       ▼                 │           ┌─────────────┐
                ┌─────────────┐          │           │ Consumers   │
                │ Data Quality│◄─────────┘           │ (Data Sci,  │
                │ & Transform │                      │ ML Pipelines│
                └─────────────┘                      │ Apps, Dash) │
                                                     └─────────────┘
```

- **Ingestão**: `scripts/scrape_books.py` executa o web scraping categorizado, normalizando campos e gerando `data/books_raw.csv`.
- **Qualidade / Transformação**: validações básicas (campos obrigatórios, casting de tipos) no momento de construir o banco.
- **Armazenamento Operacional**: `scripts/build_database.py` gera `data/books.db` (SQLite) pronto para consultas.
- **Serviço de Dados**: `FastAPI` oferece endpoints REST versionados para consumo por cientistas de dados, pipelines de ML e aplicações externas.

## Componentes

| Componente | Tecnologias | Função |
| ---------- | ----------- | ------ |
| Scraping | `requests`, `BeautifulSoup` | Captura dados do site, lida com paginação e normaliza metadados |
| Data Lake Local | CSV | Fonte bruta versionável, fácil reprocessamento |
| Banco Operacional | SQLite | Persistência leve, consultas rápidas e empacotamento simples |
| API | FastAPI, Pydantic, Uvicorn | Exposição pública com documentação automática, coleção `/api/v1/*` e rotas ML `/api/v1/ml/*` |
| Observabilidade | Logs estruturados (stdout) | Acompanhar processo de scraping e healthcheck da API |

## Escalabilidade & Evolução

- **Escalabilidade Horizontal**: API stateless; múltiplas réplicas podem ser executadas atrás de um load balancer. SQLite pode ser substituído por Postgres sem alterar contratos.
- **Versionamento de Dados**: CSV pode ser versionado (Git LFS) ou armazenado em um bucket S3; pipeline de build sempre gera banco atualizado.
- **Automação**: Jobs agendados (ex.: GitHub Actions cron) executam o scraper e recompõem o banco regularmente.
- **Observabilidade**: healthcheck (`/api/v1/health`) expõe status do dataset. Logs de scraping e API podem ser enviados para Stackdriver/Datadog em deploys gerenciados.

## Cenário de Uso para Cientistas de Dados

1. **Exploração**: cientistas consomem `/api/v1/books` com filtros, ou exportam CSV/SQLite diretamente.
2. **Feature Engineering**: agregados por categoria e ratings via endpoints `/stats` agilizam protótipos.
3. **Integração ML**: dados alimentam pipelines de recomendação (ex.: matrix factorization). A separação CSV/SQLite permite inserir etapa de limpeza adicional antes do treino.

## Integração com Modelos de ML

- **Treino Offline**: job semanal baixa CSV/SQLite, gera features e treina modelo (ex.: LightFM, embeddings BERT) versionado no MLflow.
- **Serviço Online**: API oferece `/api/v1/ml/features`, `/api/v1/ml/training-data` e `/api/v1/ml/predictions`, além de permitir extensões como `/api/v1/recommendations?user_id=...` para consumir modelos deployados.
- **Feature Store**: migração gradual para Hopsworks/Feast com as mesmas entidades (livros, categorias, preços).

## Riscos e Mitigações

| Risco | Mitigação |
| ----- | --------- |
| Mudança de layout/HTML do site | Testes de scraping, monitoramento de erros, fallback manual |
| Volume crescente | Mudar para banco relacional gerenciado (Postgres) + cache (Redis) |
| Indisponibilidade durante scraping | Rate limiting configurável (`--sleep`), retries automáticos |
| Qualidade dos dados | Validações em `database.py`, logs detalhados de registros inválidos |

## Próximas Extensões

1. **Incremental Updates**: armazenar timestamps e atualizar apenas deltas.
2. **Streaming**: publicar eventos (Kafka) para consumo em tempo real por outros sistemas.
3. **Segurança**: adicionar API Keys/Autenticação quando a API for exposta publicamente.
4. **Governança**: catálogo de dados (ex.: DataHub) descrevendo campos e linhagem.
