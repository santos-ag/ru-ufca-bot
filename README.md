# Cardápio UFCA

Bot de Telegram para consulta de cardápios do Restaurante Universitário da UFCA.

> 💡 **Acesse o bot em produção:** [https://t.me/ru_ufca_bot](https://t.me/ru_ufca_bot)

## 📋 Sobre o Projeto

Este bot permite que estudantes da UFCA consultem o cardápio do RU de forma rápida e prática, além de receber notificações automáticas nos horários das refeições.

### Funcionalidades

- 🍽️ Consulta de cardápio do almoço e janta
- 📅 Visualização do cardápio semanal completo
- 🔔 Notificações automáticas nos horários das refeições
- 📄 Processamento automático de PDFs com cardápios
- 👤 Sistema de inscrição/desinscrição de notificações
- ⭐ Sistema de pratos favoritos com botões inline
- 🔄 Atualização automática semanal via web scraping
- 🚀 Atualização de cardápio na inicialização do bot

### Comandos do Bot

| Comando | Descrição |
|---------|-----------|
| `/start` | Inscreve usuário e envia boas-vindas |
| `/almoco` | Cardápio do almoço de hoje |
| `/janta` | Cardápio da janta de hoje |
| `/semana` | Cardápio da semana completa |
| `/parar` | Remove das notificações |
| `/favoritos` | Lista seus pratos favoritos |
| `/atualizar` | Força busca de cardápio (admin) |
| `/help` | Lista de comandos |
| Enviar PDF | Admin envia PDF → processa automaticamente |

## 🏗️ Arquitetura

Este projeto segue:
- **Metodologia:** Test-Driven Development (TDD)
- **Cobertura de testes:** 80-90%
- **Linguagem:** Python 3.10+

Consulte [ARCHITECTURE.md](./ARCHITECTURE.md) para detalhes completos das decisões arquiteturais.

## 🚀 Setup do Projeto

### Pré-requisitos

- Python 3.10 ou superior
- pip

### Instalação

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/ru-ufca-bot.git
cd ru-ufca-bot
```

2. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Para desenvolvimento
```

4. Configure as variáveis de ambiente:
```bash
cp .env.example .env
# Edite .env com suas credenciais
```

5. Execute os testes:
```bash
pytest
```

## 🧪 Desenvolvimento com TDD

Este projeto segue a metodologia TDD (Test-Driven Development):

### Ciclo TDD

```
1. 🔴 RED: Escrever teste que falha
2. 🟢 GREEN: Implementar código para passar o teste
3. 🔵 REFACTOR: Melhorar código mantendo testes passando
```

### Comandos úteis

```bash
# Rodar todos os testes
pytest

# Rodar com cobertura
pytest --cov=src --cov-report=html

# Rodar apenas testes unitários
pytest -m unit

# Rodar em modo verbose
pytest -v
```

## 📁 Estrutura do Projeto

```
ru-ufca-bot/
├── .opencode/             # Configuração do OpenCode
│   └── agents/            # Sub-agents especializados
│       ├── tester.md      # Gera testes automatizados
│       ├── reviewer.md    # Revisão crítica de código
│       └── refactorer.md  # Refatoração de código
├── src/                    # Código fonte
│   ├── cache/             # Gerenciamento de cache
│   ├── scraper/           # Parsing de PDFs
│   ├── bot/               # Handlers e scheduler
│   └── main.py            # Entry point
├── tests/                  # Testes (TDD)
│   ├── fixtures/          # Dados de teste
│   └── test_*.py          # Arquivos de teste
├── data/                   # Dados persistidos
├── requirements.txt        # Dependências
├── requirements-dev.txt    # Dependências de desenvolvimento
└── ARCHITECTURE.md         # Documentação de arquitetura
```

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 👤 Autor

**Gustavo Alexandre**

## 🤝 Contribuindo

Contribuições são bem-vindas! Sinta-se livre para abrir issues e pull requests.

---
