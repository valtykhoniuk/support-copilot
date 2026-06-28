# LoRA-router — бонус: intent из №4 → routes в copilot

Связка двух проектов: adapter из `finetune-vs-prompt` помогает agent выбирать **kb** vs **refund**.

```
Вопрос клиента
      │
      ├─ TKT-#### в тексте?  ──yes──► ticket  (regex, как было)
      │
      └─ USE_LORA_ROUTER=true?
            │
            yes ──► Llama + LoRA adapter ──► intent
            │              refund ──► refund route
            │              billing/bug/how-to/other ──► kb (RAG)
            │
            no ──► keywords ("refund", "money back") ──► refund | kb
```

---

## Шаг 1 — проверь adapter (Mac)

Adapter должен лежать здесь (после Colab):

```
finetune-vs-prompt/models/foxschool-intent-lora/
├── adapter_config.json
└── adapter_model.safetensors
```

Проверка:

```bash
ls ../finetune-vs-prompt/models/foxschool-intent-lora/adapter_config.json
```

---

## Шаг 2 — установи LoRA-зависимости (один раз)

```bash
cd support-copilot
source support-copilot/bin/activate   # или .venv
pip install -r requirements-lora.txt
huggingface-cli login                 # если Llama ещё не в кэше
```

---

## Шаг 3 — включи в `.env`

```env
USE_LORA_ROUTER=true
# LORA_ADAPTER_DIR=../finetune-vs-prompt/models/foxschool-intent-lora  # опционально
```

По умолчанию путь к adapter — соседняя папка `finetune-vs-prompt`.

---

## Шаг 4 — быстрый тест router (без API)

```bash
cd support-copilot
python -c "
from app.router import route_with_meta
for q in [
    'What is ticket TKT-1002?',
    'Can I get a refund 4 days after payment?',
    'I was charged twice for Beginner plan',
    'How much does Beginner plan cost?',
]:
    route, meta = route_with_meta(q)
    print(f'{route:6} {meta} | {q[:50]}')
"
```

Ожидаемо (с LoRA):

| Вопрос | route | intent |
|--------|-------|--------|
| TKT-1002 | ticket | regex |
| refund 4 days | refund | refund |
| charged twice | kb | billing |
| Beginner price | kb | billing |

---

## Шаг 5 — agent evals (полный прогон)

**Без LoRA** (CI по умолчанию — keywords):

```bash
USE_LORA_ROUTER=false python evals/agent_evals.py
```

**С LoRA** (первый запуск долгий — грузит Llama ~2 GB):

```bash
USE_LORA_ROUTER=true python evals/agent_evals.py
```

Цель: **10/10** как раньше. Regex для ticket и PII guardrails не трогали.

---

## Шаг 6 — через API

```bash
uvicorn app.main:app --reload
```

```bash
curl -s -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Can I get my money back after 5 days?"}' | python -m json.tool
```

В ответе появятся поля:

```json
{
  "route": "refund",
  "router": "lora",
  "intent": "refund",
  ...
}
```

---

## Файлы

| Файл | Зачем |
|------|-------|
| `app/intent_classifier.py` | загрузка Llama + adapter, `predict_intent()` |
| `app/router.py` | `route_with_meta()` — regex → LoRA → keywords |
| `app/agent.py` | добавляет `router` и `intent` в ответ |

---

## На собесе (одна фраза)

> Fine-tuned LoRA adapter from intent-classification experiment (86% on 5 labels) integrated as optional router in support-copilot — refund vs KB paths; ticket IDs still regex.

---

## Если что-то не работает

| Проблема | Решение |
|----------|---------|
| adapter not found | проверь путь, `LORA_ADAPTER_DIR` в `.env` |
| медленно первый запрос | нормально — грузится Llama |
| agent evals упали | `USE_LORA_ROUTER=false` для CI; LoRA только локально |
| нет GPU на Mac | работает на MPS/CPU, просто медленнее |
