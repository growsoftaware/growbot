# Plano: Telegram Bot como Agente Conversacional

## Objetivo
Transformar o bot Telegram de "menu-driven" para **agente conversacional** que entende contexto e responde em linguagem natural, igual conversar com Claude.

## Exemplo de Interação Desejada

```
User: *envia arquivo*

Bot: "Recebi o export! Encontrei:
• RODRIGO: 03/01 (29 🏎️), 02/01 (15 🏎️)
• KAROL: 03/01 (18 🏎️)
• FRANCIS: 02/01 (22 🏎️)

O que quer fazer?"

User: "processa só o rodrigo de hoje"

Bot: "Ok! RODRIGO 03/01 - 29 entregas.
Primeiro: 🏎️001 '40 corrida, Janeiro' - parece mensagem de sistema, não produto.
Pulo esse?"

User: "sim, pula"

Bot: "Pulei 🏎️001. Próximo: 🏎️002 '20g prensado, Av. Dimas 123'.
Detectei: prensado x1. Confirmo os próximos automaticamente?"

User: "confirma todos menos os que tiverem dúvida"

Bot: "Perfeito! Processando...
✅ 27 confirmados automaticamente
⚠️ 2 com dúvidas pra revisar

🏎️015: 'manda 50 do pren comercial' - 50 unidades parece muito. Confirma?"
```

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                     TELEGRAM BOT v2.0                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  User Message ──► Conversation Manager ──► Claude API        │
│       │                    │                    │            │
│       │                    ▼                    │            │
│       │          ┌─────────────────┐           │            │
│       │          │  user_states    │           │            │
│       │          │  - context      │           │            │
│       │          │  - history[]    │◄──────────┘            │
│       │          │  - file_data    │                        │
│       │          │  - pending_action│                       │
│       │          └─────────────────┘                        │
│       │                    │                                │
│       ▼                    ▼                                │
│  ┌─────────┐      ┌──────────────┐      ┌──────────┐       │
│  │ Parser  │      │ Action Router │      │ Database │       │
│  │(parser.py)│◄───│ (executa ação)│────►│ (db.py)  │       │
│  └─────────┘      └──────────────┘      └──────────┘       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Componentes Principais

### 1. Sistema de Contexto (`ConversationContext`)

```python
@dataclass
class ConversationContext:
    user_id: int
    history: List[dict]           # [{"role": "user/assistant", "content": "..."}]
    file_data: Optional[dict]     # Dados do arquivo atual
    selected_driver: Optional[str]
    selected_date: Optional[str]
    pending_blocks: List[dict]    # Blocos aguardando confirmação
    confirmed_blocks: List[dict]  # Blocos já confirmados
    last_action: Optional[str]    # Última ação executada
```

### 2. System Prompt do Agente

```markdown
Você é o GrowBot, assistente para processar entregas do WhatsApp.

CONTEXTO ATUAL:
- Arquivo: {file_info}
- Driver selecionado: {driver}
- Data selecionada: {date}
- Blocos pendentes: {pending_count}
- Blocos confirmados: {confirmed_count}

AÇÕES DISPONÍVEIS:
- SHOW_DRIVERS: Mostrar drivers disponíveis
- SELECT_DRIVER(nome): Selecionar driver
- SELECT_DATE(data): Selecionar data
- PROCESS_AUTO: Processar automaticamente
- PROCESS_ONE_BY_ONE: Processar um por um
- CONFIRM_BLOCK(id): Confirmar bloco
- SKIP_BLOCK(id): Pular bloco
- CONFIRM_ALL: Confirmar todos restantes
- SAVE: Salvar no banco
- CANCEL: Cancelar operação

RESPONDA em JSON:
{
  "message": "Texto para o usuário",
  "action": "NOME_DA_ACAO",
  "params": {}
}
```

### 3. Action Router

```python
async def execute_action(action: str, params: dict, context: ConversationContext) -> str:
    """Executa ação e retorna resultado."""

    match action:
        case "SHOW_DRIVERS":
            return format_drivers_summary(context.file_data)

        case "SELECT_DRIVER":
            context.selected_driver = params["driver"]
            return format_driver_dates(context)

        case "SELECT_DATE":
            context.selected_date = params["date"]
            return load_blocks_for_date(context)

        case "PROCESS_AUTO":
            return auto_process_blocks(context)

        case "CONFIRM_BLOCK":
            return confirm_single_block(context, params["id"])

        case "SAVE":
            return save_to_database(context)

        # ... etc
```

### 4. Fluxo Principal

```python
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message.text

    # 1. Carregar/criar contexto
    conv_context = get_or_create_context(user_id)

    # 2. Adicionar mensagem ao histórico
    conv_context.history.append({"role": "user", "content": message})

    # 3. Chamar Claude com contexto
    response = await call_claude_agent(
        message=message,
        context=conv_context,
        system_prompt=build_system_prompt(conv_context)
    )

    # 4. Parsear resposta (JSON com action)
    parsed = parse_agent_response(response)

    # 5. Executar ação se houver
    if parsed.action:
        action_result = await execute_action(
            parsed.action,
            parsed.params,
            conv_context
        )
        # Pode gerar nova chamada ao Claude se necessário

    # 6. Responder ao usuário
    await update.message.reply_text(parsed.message)

    # 7. Salvar histórico
    conv_context.history.append({"role": "assistant", "content": parsed.message})
```

## Arquivos a Modificar

| Arquivo | Mudanças |
|---------|----------|
| `telegram_bot.py` | Refatorar para modo conversacional |
| `llm.py` | Adicionar `chat_with_context()` |
| `system_prompt_agent.md` | **CRIAR** - Prompt do agente |

## Implementação Incremental

### Fase 1: Fundação (1-2h)
- [ ] Criar `ConversationContext` dataclass
- [ ] Criar `system_prompt_agent.md`
- [ ] Adicionar `chat_with_context()` em llm.py
- [ ] Refatorar `handle_text()` para usar Claude

### Fase 2: Actions Básicas (2-3h)
- [ ] Implementar Action Router
- [ ] Ações: SHOW_DRIVERS, SELECT_DRIVER, SELECT_DATE
- [ ] Integrar com parser existente
- [ ] Manter compatibilidade com fluxo atual (fallback)

### Fase 3: Processamento (2-3h)
- [ ] Ações: PROCESS_AUTO, PROCESS_ONE_BY_ONE
- [ ] Ações: CONFIRM_BLOCK, SKIP_BLOCK, CONFIRM_ALL
- [ ] Ação: SAVE (integrar com db.py)

### Fase 4: Polish (1-2h)
- [ ] Persistir contexto entre restarts (opcional: Redis/SQLite)
- [ ] Limitar histórico (últimas 20 mensagens)
- [ ] Tratamento de erros amigável
- [ ] Testes com casos reais

## System Prompt Detalhado

```markdown
# GrowBot Agent

Você é um assistente para processar entregas de delivery via WhatsApp.

## Seu Papel
- Ajudar o usuário a importar e validar entregas
- Entender comandos em linguagem natural
- Executar ações no sistema
- Reportar resultados de forma clara

## Contexto da Conversa
{context_json}

## Regras
1. Sempre responda em português brasileiro
2. Seja conciso mas informativo
3. Quando houver dúvida, pergunte antes de agir
4. Use emojis moderadamente (🏎️ para entregas, ✅ confirmado, ⚠️ dúvida)
5. Se o usuário pedir algo impossível, explique o porquê

## Formato de Resposta
Sempre responda em JSON válido:
{
  "message": "Texto amigável para o usuário",
  "action": "NOME_DA_ACAO ou null",
  "params": {"param1": "valor1"}
}

## Ações Disponíveis
- SHOW_SUMMARY: Mostra resumo do arquivo
- SELECT_DRIVER(driver): Seleciona driver (RODRIGO, KAROL, FRANCIS, ARTHUR, RAFA)
- SELECT_DATE(date): Seleciona data (formato DD/MM/YYYY)
- SHOW_BLOCK(id): Mostra detalhes de um bloco
- CONFIRM_BLOCK(id): Confirma um bloco
- SKIP_BLOCK(id): Pula um bloco
- CONFIRM_ALL: Confirma todos os blocos pendentes
- PROCESS_AUTO: Processa automaticamente (só para em dúvidas)
- SAVE: Salva no banco de dados
- CANCEL: Cancela operação atual
- QUERY_DB(sql): Consulta o banco (apenas SELECT)

## Exemplos

User: "mostra o que tem no arquivo"
Response: {"message": "No arquivo encontrei:\n• RODRIGO: 03/01 (29 🏎️)\n• KAROL: 03/01 (18 🏎️)\n\nQual driver quer processar?", "action": "SHOW_SUMMARY", "params": {}}

User: "rodrigo"
Response: {"message": "RODRIGO selecionado! Datas disponíveis:\n• 03/01 - 29 entregas (✨ novo)\n• 02/01 - 15 entregas (🔄 já importado)\n\nQual data?", "action": "SELECT_DRIVER", "params": {"driver": "RODRIGO"}}

User: "processa tudo automaticamente"
Response: {"message": "Processando RODRIGO 03/01...\n✅ 27 confirmados\n⚠️ 2 com dúvidas\n\nPrimeira dúvida - 🏎️015: '50 pren comercial'\nQuantidade 50 parece alta. Confirma?", "action": "PROCESS_AUTO", "params": {}}
```

## Decisões de Design

1. **Híbrido Menu + Conversa**: Mantém botões inline como atalhos, mas aceita texto livre
2. **Fallback Gracioso**: Se Claude não entender, oferece opções em botões
3. **Contexto Limitado**: Máximo 20 mensagens no histórico (economia de tokens)
4. **Ações Atômicas**: Cada ação faz uma coisa só, fácil de debugar

## Estimativa

- **Complexidade**: Média-Alta
- **Tempo**: 6-10 horas de desenvolvimento
- **Risco**: Baixo (mantém compatibilidade com fluxo atual)
- **Custo API**: ~$0.01-0.05 por conversa (Claude Sonnet)
