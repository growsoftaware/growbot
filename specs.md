---

## Guia rápido de como eu recomendo construir o bot (local)

### Recomendo Python (primeiro), depois Go se precisar performance
**Por quê Python primeiro:**
- parsing/regex + limpeza de texto é muito rápido de iterar
- fácil criar uma pipeline: “regras + LLM + validação + export CSV”
- você consegue testar com vários blocos históricos e ajustar em horas

**Go faz sentido** quando:
- você quer binário único, distribuição fácil, throughput alto
- mas a iteração de regras e tooling costuma ser mais lenta

### Arquitetura prática (local)
1) **Pré-processador (determinístico)**
   - separa sessões (rodapés driver/data)
   - detecta entregas por 🏎️
   - monta `parse_mensagem_dia` por entrega

2) **LLM só para o “difícil”**
   - extrair produtos/quantidades de frases humanas (“cara traz…”)
   - sugerir normalizações novas (`suggested_rule_updates`)

3) **Validador**
   - checa ENUM do driver, data, id com 3 dígitos
   - se quebrar: reprocessa com prompt de “correção” (ou marca `null` + observação)

4) **Camada de “aprendizado” (rápida e segura)**
   - salva `produto_aliases_to_add` em um `aliases.json`
   - você revisa/aceita (manual) e isso vira regra fixa pro próximo dia
   - isso deixa o bot mais rápido e consistente sem “alucinar regras”

5) **Export**
   - JSON → CSV (ou direto pro Postgres)

Se você colar 1 bloco “real” (ex: só o trecho de um dia/driver), eu consigo também te devolver um **exemplo de saída JSON** já seguindo esse system prompt — e com uma lista inicial bem boa de `aliases.json` pra acelerar o “aprendizado” a partir dos seus termos.
