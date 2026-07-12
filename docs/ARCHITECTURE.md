# Arquitetura - RU UFCA Bot

> Bot de Telegram para consulta de cardápios do Restaurante Universitário da UFCA

**Status:** Em Produção  
**Última atualização:** 19/05/2026

---

## Stack

| Componente | Tecnologia                                   |
|------------|----------------------------------------------|
| Linguagem | Python 3.10+ (Docker), 3.14 (dev local)      |
| Bot | python-telegram-bot 22.6                     |
| PDF | pdfplumber 0.10.3                            |
| Web Scraping | requests 2.31.0 + beautifulsoup4 4.12.2  |
| Scheduler | APScheduler 3.10.4                           |
| LLM | Gemini (google-generativeai) ou Groq              |
| Persistência | JSON (data/menu_cache.json, data/users.json) |
| Deploy | Docker + Digital Ocean                       |

---

## Estrutura

```
src/
├── main.py              # Entry point + post_init hook
├── bot/
│   ├── handlers.py      # /start, /almoco, /janta, /semana, /parar, /help, /atualizar, /favoritos
│   │                    # + upload PDF + favorite_callback (inline buttons)
│   ├── scheduler.py     # Notificações 10:30 e 16:30 com alertas de favoritos
│   ├── formatter.py     # Mensagens formatadas com emojis + inline keyboards
│   └── auto_updater.py  # Atualização automática semanal
├── cache/
│   └── menu_cache.py    # MenuCache + UserManager (com favoritos)
└── scraper/
    ├── pdf_parser.py               # Extração bruta de texto/tabelas do PDF (pdfplumber)
    ├── table_menu_extractor.py     # Extrator principal — lê tabelas, sanitiza e organiza por data
    ├── menu_extractor.py           # Extrator fallback — baseado em texto puro
    ├── menu_url_scraper.py         # Scraper web de URLs do site UFCA
    └── pdf_downloader.py           # Download de PDFs de URLs externas
```

---

## Comandos

| Comando | Descrição |
|---------|-----------|
| `/start` | Inscreve usuário e envia boas-vindas |
| `/almoco` | Cardápio do almoço de hoje (com botão de favoritar) |
| `/janta` | Cardápio da janta de hoje (com botão de favoritar) |
| `/semana` | Cardápio da semana completa (com botões para hoje) |
| `/parar` | Remove das notificações |
| `/favoritos` | Lista pratos favoritos do usuário |
| `/atualizar` | Força busca de cardápio via web (admin) |
| `/help` | Lista de comandos |
| Enviar PDF | Admin envia PDF → processa automaticamente |

---

## Sistema de Favoritos

### Fluxo

Todas as mensagens de cardápio (notificações, `/almoco`, `/janta`, `/semana`) incluem botões inline:

```
🍽️ ALMOÇO

🍗 Principal: Frango Grelhado
🍚 Acompanhamentos: Arroz, Feijão

[☆ Favoritar Frango Grelhado]
```

Ao clicar:
1. Botão muda para `[☆ Desfavoritar Frango Grelhado]`
2. Prato salvo em `users.json` → `favorites: {"12345": ["Frango Grelhado"]}`
3. Notificações futuras com esse prato recebem alerta: `🌟 ALERTA DE FAVORITO!`

### Persistência

```json
{
  "chat_ids": [123456789],
  "admin_ids": [8786785676],
  "favorites": {
    "123456789": ["Frango Grelhado", "Peixe Assado"]
  }
}
```

### API do UserManager

| Método | Descrição |
|--------|-----------|
| `add_favorite(chat_id, dish)` | Adiciona favorito (idempotente) |
| `remove_favorite(chat_id, dish)` | Remove favorito (idempotente) |
| `get_favorites(chat_id)` | Retorna lista de favoritos |
| `is_favorite(chat_id, dish)` | Verifica se prato é favorito |

---

## Atualização Automática

### Na Inicialização (post_init)

Ao subir, o bot executa `update_menu_from_web()` imediatamente via hook `post_init` do ApplicationBuilder. Isso garante que novos containers populam o cache sem esperar a segunda-feira.

### Semanal (Scheduler)

A cada **segunda-feira às 09:00**, o bot executa automaticamente:

```
1. MenuUrlScraper
   └─→ Scrape página: https://www.ufca.edu.br/assuntos-estudantis/refeitorio-universitario/cardapios/
   └─→ Extrai URLs de botões com classe "ui teal button"
   └─→ Retorna lista ordenada pela data de início do cardápio (extraída do título)

2. PDFDownloader
    └─→ Download do PDF mais recente
    └─→ Validação: Content-Type = application/pdf
    └─→ Limite de tamanho: 50 MB

3. Parsing
    └─→ TableMenuExtractor (método preferido, se houver tabelas)
    └─→ MenuExtractor (fallback, texto puro)
    └─→ LLM Cleaner (Gemini ou Groq) para estruturar e normalizar campos
    └─→ Organiza cardápios por data

4. Persistência
   └─→ Salva no cache (data/menu_cache.json)
   └─→ Logs de sucesso/erro
```

### Ordenação do Scraper (Correção)

O scraper ordena PDFs pela **data de início do cardápio extraída do título** (ex: "Cardápio 18/05/2026 a 22/05/2026" → 2026-05-18), e não pela data de atualização do CMS. Isso resolve o bug onde PDFs mais antigos no CMS tinham cardápios mais recentes.

Fallback: se o título não contém data, usa a data de atualização do CMS.

### Manual (Admin)

Comando `/atualizar` — admin força atualização imediata via web com feedback no Telegram.

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
{
  "chat_ids": [123456789],
  "admin_ids": [8786785676],
  "favorites": {
    "123456789": ["Frango Grelhado", "Peixe Assado"]
  }
}
```

---

## Deploy

- **VM:** Digital Ocean (anteriormente Oracle Cloud)
- **Container:** Docker
- **Registry:** GHCR + Docker Hub (`alexanderthebig2/ru-ufca-bot:latest`)

**Ciclo de atualização:**

Atualização via pull + rebuild do container. Cardápios são atualizados:
1. **Na inicialização** — busca automática via post_init
2. **Semanalmente** — toda segunda-feira às 09:00
3. **Manualmente** — admin usa `/atualizar`

---

## Testes

- **~165+ testes passando**
- **Cobertura:** ~87-89%

### Suítes de Teste

| Arquivo | Cobertura | Descrição |
|---------|-----------|-----------|
| `test_menu_url_scraper.py` | 86% | Scraper web + ordenação por título |
| `test_pdf_downloader.py` | 91% | Download de PDFs |
| `test_auto_updater.py` | 89% | Orquestrador completo |
| `test_menu_cache.py` | 87% | Cache + UserManager + favoritos |
| `test_formatter.py` | 100% | Formatação + inline keyboards |
| `test_handlers.py` | 92% | Todos os comandos + callbacks |
| `test_scheduler.py` | 86% | Notificações + alertas favoritos |
| `test_main.py` | 89% | Entry point + post_init |

---

## Variáveis de Ambiente

```
TELEGRAM_BOT_TOKEN=...
ADMIN_CHAT_ID=...
TIMEZONE=America/Fortaleza
LUNCH_NOTIFICATION_TIME=10:30
DINNER_NOTIFICATION_TIME=16:30
LLM_PROVIDER=gemini  # gemini ou groq
GOOGLE_API_KEY=...
GOOGLE_MODEL=gemini-2.0-flash
GROQ_API_KEY=...
GROQ_MODEL=llama-3.1-8b-instant
GROQ_DELAY_SECONDS=0.5
```

---

## Metodologia

- **DDD (Domain-Driven Design):** Estrutura clara de domínios (scraper, cache, bot)
- **TDD (Test-Driven Development):** Testes cobrindo todos os cenários
- **Async/Await:** Jobs assincronizados não bloqueiam o bot
- **Value Objects:** MenuPdfLink como representação imutável
- **Inline Keyboards:** Botões interativos para favoritos em todas as mensagens
