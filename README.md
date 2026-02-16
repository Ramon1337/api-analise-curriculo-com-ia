# 📄 Resume AI Backend

API para **análise e ajuste de currículos com Inteligência Artificial**, construída com [FastAPI](https://fastapi.tiangolo.com/) e integrada ao [n8n](https://n8n.io/) como orquestrador de workflows de IA.

O sistema recebe um currículo (PDF ou texto), envia para um fluxo no n8n que utiliza LLMs para processar o conteúdo, e devolve:

- **Análise detalhada** com pontos fortes, fracos, sugestões e nota (0–10)
- **Currículo reescrito** em PDF com layout profissional

---

## 🏗️ Arquitetura

```
Frontend (React) → FastAPI Backend → n8n Webhook → LLM (AI Agent)
                       ↓
                  ReportLab (PDF)
```

| Camada                | Tecnologia        | Papel                                            |
| --------------------- | ----------------- | ------------------------------------------------ |
| **API**               | FastAPI + Uvicorn | Recebe uploads, valida, roteia                   |
| **Orquestração IA**   | n8n (webhook)     | Envia texto para LLM, processa resposta          |
| **Extração de texto** | PyPDF2            | Extrai conteúdo de PDFs                          |
| **Geração de PDF**    | ReportLab         | Gera currículo reescrito com layout profissional |
| **Validação**         | Pydantic          | Schemas de request/response                      |

---

## 🚀 Funcionalidades

| Recurso             | Descrição                                                            |
| ------------------- | -------------------------------------------------------------------- |
| Upload de currículo | PDF ou texto puro (.txt)                                             |
| Análise com IA      | Retorna análise detalhada + sugestões + nota (0–10) em JSON          |
| Ajuste com IA       | Retorna currículo reescrito como PDF com layout profissional         |
| Integração n8n      | Envia/recebe dados via webhook para orquestração de LLMs             |
| Geração de PDF      | Layout executivo com seções, bullets e duas colunas para habilidades |
| CORS                | Habilitado e configurável via `.env`                                 |
| Logs estruturados   | Formato `timestamp \| level \| logger \| message`                    |

---

## 📁 Estrutura do Projeto

```
resume-ai-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # Ponto de entrada (FastAPI app factory)
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py            # Configurações via .env (Pydantic Settings)
│   ├── routes/
│   │   ├── __init__.py
│   │   └── resume.py            # Endpoint POST /resume/analyze
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── resume_schema.py     # Schemas Pydantic (request/response)
│   └── services/
│       ├── __init__.py
│       ├── n8n_client.py        # Cliente HTTP para webhook do n8n
│       ├── pdf_service.py       # Geração de PDF com layout profissional
│       └── resume_parser.py     # Extração de texto de PDF/TXT
├── requirements.txt
├── .env                         # Variáveis de ambiente (não versionado)
└── README.md
```

---

## ⚙️ Instalação e Execução

### Pré-requisitos

- Python 3.11+
- n8n rodando com o workflow de análise configurado

### 1. Clonar o repositório

```bash
git clone https://github.com/Ramon1337/analise-curriculo-com-ia.git
cd analise-curriculo-com-ia
```

### 2. Criar e ativar o ambiente virtual

```bash
python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Linux/macOS
source venv/bin/activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
# URL do webhook do n8n
N8N_WEBHOOK_URL=http://localhost:5678/webhook/resume

# Timeout para resposta do n8n (segundos)
TIMEOUT_SECONDS=120

# Tamanho máximo de upload (MB)
MAX_FILE_SIZE_MB=5

# Origens permitidas (CORS)
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# JWT (uso futuro)
SECRET_KEY=sua-chave-secreta-aqui
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 5. Iniciar o servidor

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

O servidor estará disponível em:

- **API:** http://localhost:8000
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## 📡 Endpoints

### `GET /health`

Health check da API.

**Resposta:**

```json
{ "status": "ok" }
```

---

### `POST /resume/analyze`

Endpoint principal — analisa ou ajusta um currículo.

**Content-Type:** `multipart/form-data`

| Parâmetro | Tipo   | Obrigatório | Descrição                                                          |
| --------- | ------ | :---------: | ------------------------------------------------------------------ |
| `file`    | `File` |     ✅      | Arquivo do currículo (PDF ou .txt)                                 |
| `adjust`  | `bool` |     ❌      | `false` = apenas análise (padrão) · `true` = retorna PDF reescrito |

#### Modo Análise (`adjust=false`)

**Resposta:** `application/json`

```json
{
  "analysis": "1) Pontos fortes\n- Experiência com IA e automação...\n\n2) Pontos fracos\n- Falta de métricas...\n\n3) Sugestões práticas...\n\n4) Avaliação geral...",
  "suggestions": "Corrigir formatação, incluir métricas de impacto, adicionar GitHub...",
  "score": 7
}
```

| Campo         | Tipo              | Descrição                                                    |
| ------------- | ----------------- | ------------------------------------------------------------ |
| `analysis`    | `string`          | Texto completo da análise (pontos fortes, fracos, sugestões) |
| `suggestions` | `string`          | Sugestões de melhoria em texto livre                         |
| `score`       | `integer \| null` | Nota geral do currículo (0 a 10)                             |

#### Modo Ajuste (`adjust=true`)

**Resposta:** `application/pdf`

Retorna o currículo reescrito como um arquivo PDF com layout profissional contendo:

- Nome e dados de contato no topo
- Seções com títulos em caixa alta e linha separadora
- Bullets estilizados em azul marinho
- Habilidades em layout de duas colunas (quando aplicável)

#### Erros

| Status | Descrição                                      |
| ------ | ---------------------------------------------- |
| `400`  | Arquivo inválido ou formato não suportado      |
| `413`  | Arquivo excede o limite de tamanho configurado |
| `500`  | Erro de conexão/timeout com o n8n              |

---

## 🔗 Integração com n8n

O backend envia o currículo via POST para o webhook do n8n no formato:

```json
{
  "resume_text": "texto extraído do currículo...",
  "adjust": false
}
```

### Resposta esperada do n8n

**Modo análise** (`adjust=false`):

```json
[
  {
    "output": "1) Pontos fortes\n- ...\n2) Pontos fracos\n- ...\n3) Sugestões..."
  }
]
```

**Modo ajuste** (`adjust=true`):

```json
[
  {
    "analysis": "1) Pontos fortes...",
    "rewritten_resume": "Nome Completo\nemail@exemplo.com | (11) 99999-9999\n\nResumo Profissional\n..."
  }
]
```

O backend aceita ambos os formatos automaticamente (array ou objeto, com campo `output` ou campos separados).

---

## 🔧 Variáveis de Ambiente

| Variável                      | Padrão                                 | Descrição                               |
| ----------------------------- | -------------------------------------- | --------------------------------------- |
| `N8N_WEBHOOK_URL`             | `http://localhost:5678/webhook/resume` | URL do webhook do n8n                   |
| `TIMEOUT_SECONDS`             | `120`                                  | Timeout da requisição ao n8n (segundos) |
| `MAX_FILE_SIZE_MB`            | `5`                                    | Tamanho máximo de upload em MB          |
| `CORS_ORIGINS`                | `["*"]`                                | Origens permitidas para CORS            |
| `SECRET_KEY`                  | `change-me-in-production`              | Chave secreta para JWT (uso futuro)     |
| `ALGORITHM`                   | `HS256`                                | Algoritmo JWT                           |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30`                                   | Expiração do token JWT (minutos)        |

---

## 🧪 Exemplos de Uso

### cURL

```bash
# Análise
curl -X POST http://localhost:8000/resume/analyze \
  -F "file=@curriculo.pdf" \
  -F "adjust=false"

# Ajuste (recebe PDF)
curl -X POST http://localhost:8000/resume/analyze \
  -F "file=@curriculo.pdf" \
  -F "adjust=true" \
  -o curriculo_ajustado.pdf
```

### PowerShell

```powershell
# Análise
Invoke-RestMethod -Uri http://localhost:8000/resume/analyze `
  -Method Post `
  -Form @{ file = Get-Item .\curriculo.pdf; adjust = "false" }

# Ajuste
Invoke-WebRequest -Uri http://localhost:8000/resume/analyze `
  -Method Post `
  -Form @{ file = Get-Item .\curriculo.pdf; adjust = "true" } `
  -OutFile curriculo_ajustado.pdf
```

### Python

```python
import requests

# Análise
with open("curriculo.pdf", "rb") as f:
    r = requests.post(
        "http://localhost:8000/resume/analyze",
        files={"file": f},
        data={"adjust": "false"},
    )
print(r.json())

# Ajuste
with open("curriculo.pdf", "rb") as f:
    r = requests.post(
        "http://localhost:8000/resume/analyze",
        files={"file": f},
        data={"adjust": "true"},
    )
with open("curriculo_ajustado.pdf", "wb") as out:
    out.write(r.content)
```

---

## 🔐 Segurança

- CORS configurável via `.env`
- Estrutura preparada para autenticação JWT (chaves já expostas no `Settings`)
- Validação de tamanho de arquivo
- Limpeza automática de arquivos PDF temporários após envio

---

## 📦 Dependências

| Pacote                | Uso                                   |
| --------------------- | ------------------------------------- |
| **fastapi**           | Framework web assíncrono              |
| **uvicorn**           | Servidor ASGI                         |
| **python-multipart**  | Suporte a upload de arquivos          |
| **requests**          | Cliente HTTP para n8n                 |
| **reportlab**         | Geração de PDF                        |
| **pydantic**          | Validação de dados                    |
| **pydantic-settings** | Configurações via `.env`              |
| **python-dotenv**     | Carregamento de variáveis de ambiente |
| **PyPDF2**            | Extração de texto de PDFs             |

---

## 📝 Licença

Este projeto é de uso pessoal/educacional.

---

**Desenvolvido por [Ramon Godinho](https://github.com/Ramon1337)**
