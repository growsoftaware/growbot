# Changelog: Telegram Bot v1.1

**Data**: 07/01/2026
**Branch**: `feature/telegram-bot`

## O que foi implementado

### Telegram Bot v1.1
Bot funcional para processar exports do WhatsApp via Telegram.

#### Funcionalidades

1. **Upload de arquivos** (.txt ou .zip)
   - Detecta tipo automaticamente (saidas/recargas/estoque)
   - Salva em `exports/` com timestamp

2. **Seleção de Driver/Data**
   - Mostra drivers com quantidade de dias novos (✨) e existentes (🔄)
   - Datas formatadas: `DD-Mmm (Ddd)` ex: `02-Jan (Qui)`
   - Quantidade de deliveries com emoji 🏎️

3. **Dois modos de processamento**
   - **👁️ Ver 1 por 1**: Valida cada bloco manualmente
   - **⚡ Auto**: Auto-confirma blocos OK, só para em dúvidas

4. **Detecção de dúvidas**
   - Nenhum item detectado
   - Quantidade > 50 (suspeita)
   - Produto com ≤ 2 caracteres
   - Issues do parser

5. **Salvamento**
   - Salva em `blocos_raw` (texto original)
   - Salva em `movimentos` (itens parseados)
   - Suporta reimportação (deleta dados antigos)

6. **Comandos**
   - `/start` - Boas-vindas
   - `/status` - Arquivos salvos
   - `/saldo` - Saldo por driver
   - `/cancelar` - Cancelar operação

#### Arquivos criados/modificados

| Arquivo | Ação |
|---------|------|
| `telegram_bot.py` | CRIADO - Bot principal (~1800 linhas) |
| `parser.py` | MODIFICADO - Fix ano na virada 31/12 |
| `requirements.txt` | MODIFICADO - python-telegram-bot>=21.0 |
| `.env.example` | MODIFICADO - Tokens do Telegram |
| `CLAUDE.md` | MODIFICADO - Documentação do bot |

#### Bugs corrigidos

1. **Ano errado na virada**: 31/12 mostrava 2026 ao invés de 2025
   - Fix em `detectar_data()` no parser.py

2. **Callback expirado**: Bot crashava em cliques antigos
   - Fix: try-except no `query.answer()`

3. **Múltiplas instâncias**: Conflito de polling
   - Sempre matar processos antes de reiniciar

## Próximo passo

**Agente Conversacional** - Transformar o bot de menu-driven para conversacional com Claude.

Ver: `docs/roadmap_agente_conversacional.md`
