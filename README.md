# Tech Challenge – Books Data Platform

Pipeline completo para captura, processamento e disponibilização dos dados de livros do site [books.toscrape.com](https://books.toscrape.com/), pensado para apoiar times de Ciência de Dados e Machine Learning.

## Visão Geral

- **Scraping robusto**: coleta todos os livros, categorias e metadados relevantes (preço, rating, estoque, descrição, imagem, UPC).
- **Armazenamento estruturado**: dados normalizados em CSV e disponibilizados em SQLite para consumo eficiente.
- **API pública FastAPI**: endpoints RESTful versionados com documentação automática Swagger.
- **Insights prontos**: estatísticas globais e por categoria para facilitar explorações rápidas.
- **Arquitetura escalável**: componentes desacoplados prontos para evoluir com novas fontes e modelos de recomendação.
- **Pronto para ML**: endpoints de features, dataset rotulado e logging de predições para alimentar experimentos.

## Estrutura do Projeto

```
api-techchallenge-fiap-1/
├── api/
│   ├── __init__.py
│   ├── config.py          # Configuração e carregamento de variáveis de ambiente
│   ├── database.py        # Bootstrap da base SQLite a partir do CSV
│   ├── main.py            # Aplicação FastAPI e definição dos endpoints
│   ├── repositories.py    # Camada de acesso ao banco (queries SQL)
│   └── schemas.py         # Modelos Pydantic expostos pela API
├── data/
│   └── .gitkeep           # Diretório reservado para CSV/SQLite gerados
├── docs/
│   └── architecture.md    # Plano arquitetural e cenário de uso futuro
├── scripts/
│   ├── scrape_books.py    # Web scraping completo do catálogo
│   └── build_database.py  # Criação/atualização da base SQLite
├── tests/
│   ├── conftest.py        # Fixtures utilitárias
│   └── test_api.py        # Testes de integração dos endpoints principais
├── .gitignore
├── Dockerfile
├── README.md
├── render.yaml            # Manifesto de deploy para Render.com
└── requirements.txt
```

## Pré-requisitos

- Python 3.11+ (recomendado 3.12)
- Pip e virtualenv (opcional, porém recomendado)
- Conexão HTTP para executar o scraping

## Configuração do Ambiente

```powershell
# Windows PowerShell
data\books_raw.csv # (será criado pelo scraper)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

Configure variáveis opcionais no arquivo `.env` (crie a partir de `.env.example`, se desejar):

```
BOOKS_CSV_FILENAME=books_raw.csv
BOOKS_DB_FILENAME=books.db
BOOKS_REBUILD_DB_ON_STARTUP=false
```

## 1. Coleta dos Dados (Web Scraping)

```powershell
python scripts/scrape_books.py --output data/books_raw.csv
```

O script percorre todas as categorias e páginas do site, gerando um CSV com os campos:
`id, title, price, currency, rating, availability, category, product_page_url, image_url, description, upc, stock`.

### Opções úteis

- `--sleep`: tempo em segundos entre requisições (default 0.1)
- `--timeout`: timeout de cada request (default 30)
- `--base-url`: permite usar um espelho/local mock
- `-v` / `-vv`: níveis de log INFO/DEBUG

## 2. Construção do Banco SQLite

```powershell
python scripts/build_database.py --force
```

O comando lê `data/books_raw.csv` e gera `data/books.db`. Utilize `--csv`/`--db` para caminhos personalizados.

## 3. Execução da API Localmente

```powershell
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

- Documentação Swagger: `http://localhost:8000/api/v1/docs`
- Documentação ReDoc: `http://localhost:8000/api/v1/redoc`

## Endpoints Principais

| Método | Rota | Descrição |
| ------ | ---- | --------- |
| GET | `/api/v1/health` | Verifica status e acesso ao dataset |
| GET | `/api/v1/books` | Lista paginada com filtros (`category`, `min_rating`, `max_rating`) |
| GET | `/api/v1/books/{id}` | Retorna detalhes completos de um livro |
| GET | `/api/v1/books/search?title=...&category=...` | Busca por título parcial e/ou categoria |
| GET | `/api/v1/categories` | Lista todas as categorias disponíveis |
| GET | `/api/v1/stats/overview` | Estatísticas gerais (total, preço médio, etc.) |
| GET | `/api/v1/stats/categories` | Estatísticas agregadas por categoria |
| GET | `/api/v1/books/top-rated?limit=10` | Livros com melhor avaliação |
| GET | `/api/v1/books/price-range?min=...&max=...` | Filtra por faixa de preço |
| GET | `/api/v1/ml/features` | Vetores de features prontos para engenharia de atributos |
| GET | `/api/v1/ml/training-data` | Dataset supervisionado incluindo rótulos de rating |
| POST | `/api/v1/ml/predictions` | Persistência de resultados gerados por modelos externos |

### Exemplo de chamada

```bash
curl http://localhost:8000/api/v1/books?limit=5
```

```json
{
  "total": 1000,
  "limit": 5,
  "offset": 0,
  "items": [
    {
      "id": 1,
      "title": "A Light in the Attic",
      "price": 51.77,
      "currency": "GBP",
      "rating": 3,
      "availability": "In stock (22 available)",
      "category": "Poetry",
      "product_page_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
      "image_url": "https://books.toscrape.com/media/cache/5e/7f/5e7f75801f783b7ab5b2ab96e9a85f04.jpg",
      "description": "It's hard to imagine a world without A Light in the Attic...",
      "upc": "a897fe39b1053632",
      "stock": 22
    }
  ]
}
```

## Testes Automatizados

```powershell
pytest -q
```

Os testes cobrem as rotas principais e garantem que o pipeline (CSV → SQLite → API) esteja operacional.

## Containerização

```powershell
docker build -t books-api .
docker run -p 8000:8000 --env PORT=8000 books-api
```

> Certifique-se de executar o scraper e copiar `data/books_raw.csv` para o container antes ou durante o build.

## Deploy em Produção (Render.com)

1. Faça fork deste repositório e habilite o serviço Web no Render.
2. Configure variáveis de ambiente (opcional) e defina o build e start commands:
   - **Build**: `pip install -r requirements.txt && python scripts/build_database.py --force`
   - **Start**: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
3. Garanta que `data/books_raw.csv` esteja versionado ou seja gerado em um job de build agendado.
4. Após o deploy, compartilhe a URL pública (ex.: `https://books-api.onrender.com/api/v1/docs`).

Arquivo `render.yaml` incluso para deploy automatizado via Infrastructure as Code.

## Plano Arquitetural

- Ver `docs/architecture.md` para diagrama, cenário de uso por cientistas de dados e estratégias futuras (streaming, lakehouse, features para ML, etc.).
- O pipeline contempla ingestão → tratamento → API → consumo, com pontos claros para reprocessamento e versionamento.

## Próximos Passos / Extensões

1. Agendar o scraping periodicamente (GitHub Actions + cron).
2. Persistir histórico e variação de preço em um Data Lake.
3. Expor endpoints analíticos adicionais (ex.: ranking por categoria, sugestões personalizadas).
4. Conectar a pipelines de ML (feature store, treinamento e deploy de recomendadores).

## Vídeo de Apresentação

Sugestão de roteiro (3–12 minutos):

1. Contextualização do problema e requisitos.
2. Visão geral do pipeline (usar o diagrama em `docs/architecture.md`).
3. Execução rápida do scraper + build do banco localmente.
4. Demonstração da API em produção (Swagger ou `curl`).
5. Destaque das boas práticas (estrutura modular, testes, versionamento).

---

Projeto desenvolvido como parte do Tech Challenge FIAP – fase de Machine Learning Engineering.
