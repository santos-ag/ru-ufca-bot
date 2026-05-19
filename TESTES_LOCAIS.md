# Testes Locais

## Setup

```bash
# Criar ambiente virtual (se não existir)
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Para desenvolvimento

# Rodar testes
pytest
```

## Testar Bot Localmente

```bash
# Copiar arquivo de exemplo
cp .env.example .env

# Editar .env com seu token de bot
# (obtenha em @BotFather)

# Rodar o bot
python -m src.main
```

## Deploy para Produção

```bash
# No servidor de produção:
cd ru-ufca-bot
git pull
docker compose up -d --build
```

## CI/CD

O projeto possui pipeline GitHub Actions que builda e publica a imagem Docker automaticamente:

- **GHCR:** `ghcr.io/gustavoalexandre17/ru-ufca-bot:latest`
- **Docker Hub:** `alexanderthebig2/ru-ufca-bot:latest`

Disparado em push para `main` e tags `v*`.

## Fluxo Simples

1. Faz as alterações localmente
2. Rode `pytest` para verificar se tudo passa
3. Teste manualmente (envie comandos no Telegram se quiser)
4. Commit e push: `git add . && git commit -m "mensagem" && git push`
5. Deploy: `ssh user@seu-servidor "cd ru-ufca-bot && git pull && docker compose up -d --build"`
