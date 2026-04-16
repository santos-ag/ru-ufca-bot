# Arquitetura - RU UFCA Bot

> Bot de Telegram para consulta de cardápios do Restaurante Universitário da UFCA

**Status:** Em Produção  
**Última atualização:** 16/04/2026

---

## Stack

| Componente | Tecnologia                                   |
|------------|----------------------------------------------|
| Linguagem | Python 3.10+ (Docker), 3.14 (dev local)      |
| Bot | python-telegram-bot 22.6                     |
| PDF | pdfplumber 0.10.3                            |
| Web Scraping | requests 2.31.0 + beautifulsoup4 4.12.2  |
| Scheduler | APScheduler 3.10.4                           |
| Persistência | JSON (data/menu_cache.json, data/users.json) |
| Deploy | Docker + Oracle Cloud                        |

---

## Estrutura

```
src/
├── main.py              # Entry point
├── bot/
│   ├── handlers.py      # /start, /almoco, /janta, /semana, /parar, /help + upload PDF
│   ├── scheduler.py     # Notificações 10:30 e 16:30
│   ├── formatter.py     # Mensagens formatadas com emojis
│   └── auto_updater.py  # Atualização automática semanal (NOVO)
├── cache/
│   └── menu_cache.py    # MenuCache + UserManager
└── scraper/
    ├── pdf_parser.py               # Extração bruta de texto/tabelas do PDF (pdfplumber)
    ├── table_menu_extractor.py     # Extrator principal — lê tabelas, sanitiza e organiza por data
    ├── menu_extractor.py           # Extrator fallback — baseado em texto puro
    ├── menu_url_scraper.py         # Scraper web de URLs do site UFCA (NOVO)
    └── pdf_downloader.py           # Download de PDFs de URLs externas (NOVO)
```

---

## Comandos

| Comando | Descrição |
|---------|-----------|
| `/start` | Inscreve usuário e envia boas-vindas |
| `/almoco` | Cardápio do almoço de hoje |
| `/janta` | Cardápio da janta de hoje |
| `/semana` | Cardápio da semana completa |
| `/parar` | Remove das notificações |
| `/help` | Lista de comandos |
| Enviar PDF | Admin envia PDF → processa automaticamente |

---

## Atualização Automática (NEW)

### Fluxo
A cada **segunda-feira às 09:00**, o bot executa automaticamente:

```
1. MenuUrlScraper
   └─→ Scrape página: https://www.ufca.edu.br/assuntos-estudantis/refeitorio-universitario/cardapios/
   └─→ Extrai URLs de botões com classe "ui teal button"
   └─→ Retorna lista ordenada por data (mais recente primeiro)

2. PDFDownloader
   └─→ Download do PDF mais recente
   └─→ Validação: Content-Type = application/pdf
   └─→ Limite de tamanho: 50 MB

3. Parsing
   └─→ TableMenuExtractor (método preferido, se houver tabelas)
   └─→ MenuExtractor (fallback, texto puro)
   └─→ Organiza cardápios por data

4. Persistência
   └─→ Salva no cache (data/menu_cache.json)
   └─→ Logs de sucesso/erro

5. Notificação
   └─→ Nenhuma notificação enviada (silencioso)
   └─→ Logs informam status da operação
```

### Tratamento de Erros

| Erro | Ação |
|------|------|
| **Site indisponível** | Log ERROR, tenta novamente na próxima segunda |
| **HTML mudou de estrutura** | Log ERROR, continua aguardando atualização manual |
| **PDF download falha** | Log ERROR, tenta novamente na próxima segunda |
| **PDF corrompido/inválido** | Log ERROR, fallback para MenuExtractor (texto) |
| **Parse falha** | Log ERROR, não salva dados parciais |

---

## Formato de Dados

**Cache (`data/menu_cache.json`):**
```json
{
  "2026-03-14": {
    "almoco": {"prato_principal": "...", "acompanhamentos": [...], ...},
    "janta": {"prato_principal": "...", "acompanhamentos": [...], ...}
  }
}
```

**Usuários (`data/users.json`):**
```json
{"chat_ids": [123456789], "admin_ids": [8786785676]}
```

---

## Deploy

- **VM:** Oracle Cloud
- **Container:** Docker 

**Ciclo de atualização:**

Atualização via pull + rebuild do container. A atualização de cardápios agora é **100% automática** toda segunda-feira às 09:00.

---

## Testes

- **~130+ testes passando** (incluindo novos testes de scraping)
- **Cobertura:** ~90%+

### Novos Testes
- `test_menu_url_scraper.py` - Scraper web
- `test_pdf_downloader.py` - Download de PDFs
- `test_auto_updater.py` - Orquestrador completo

---

## Variáveis de Ambiente

```
TELEGRAM_BOT_TOKEN=...
ADMIN_CHAT_ID=...
TIMEZONE=America/Fortaleza
LUNCH_NOTIFICATION_TIME=10:30
DINNER_NOTIFICATION_TIME=16:30
```

---

## Metodologia

- **DDD (Domain-Driven Design):** Estrutura clara de domínios (scraper, cache, bot)
- **TDD (Test-Driven Development):** Testes cobrindo todos os cenários
- **Async/Await:** Jobs assincronizados não bloqueiam o bot
- **Value Objects:** MenuPdfLink como representação imutável
