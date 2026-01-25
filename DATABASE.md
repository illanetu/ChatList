# Схема базы данных ChatList

## Общая информация

База данных: **SQLite**  
Файл БД: `chatlist.db` (создается автоматически при первом запуске)

## Таблицы

### 1. Таблица `prompts` (Промты)

Хранит сохраненные пользовательские запросы (промты).

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Уникальный идентификатор промта |
| `date` | TEXT | NOT NULL | Дата и время создания (формат: ISO 8601, например: '2024-01-15 10:30:00') |
| `prompt` | TEXT | NOT NULL | Текст промта (запроса к нейросети) |
| `tags` | TEXT | NULL | Теги для категоризации (разделитель: запятая, например: 'работа,важное') |

**Индексы:**
- `idx_prompts_date` на поле `date` (для быстрой сортировки)
- `idx_prompts_tags` на поле `tags` (для поиска по тегам)

**Пример данных:**
```sql
INSERT INTO prompts (date, prompt, tags) VALUES 
('2024-01-15 10:30:00', 'Объясни квантовую физику простыми словами', 'наука,образование'),
('2024-01-15 11:00:00', 'Напиши код на Python для работы с API', 'программирование');
```

---

### 2. Таблица `models` (Нейросети)

Хранит информацию о доступных моделях нейросетей и их API-конфигурации.

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Уникальный идентификатор модели |
| `name` | TEXT | NOT NULL UNIQUE | Название модели (например: 'GPT-4', 'DeepSeek Chat') |
| `api_url` | TEXT | NOT NULL | URL API для отправки запросов (например: 'https://api.openai.com/v1/chat/completions') |
| `api_id` | TEXT | NOT NULL | Идентификатор переменной окружения с API-ключом (например: 'OPENAI_API_KEY') |
| `is_active` | INTEGER | NOT NULL DEFAULT 1 | Флаг активности (1 - активна, 0 - неактивна) |

**Индексы:**
- `idx_models_active` на поле `is_active` (для быстрого получения активных моделей)

**Примечание:** Сами API-ключи хранятся в файле `.env`, а не в базе данных. В таблице хранится только имя переменной окружения (`api_id`), по которой будет искаться ключ.

**Пример данных:**
```sql
INSERT INTO models (name, api_url, api_id, is_active) VALUES 
('GPT-4', 'https://api.openai.com/v1/chat/completions', 'OPENAI_API_KEY', 1),
('DeepSeek Chat', 'https://api.deepseek.com/v1/chat/completions', 'DEEPSEEK_API_KEY', 1),
('Groq Llama', 'https://api.groq.com/openai/v1/chat/completions', 'GROQ_API_KEY', 0);
```

**Соответствие в .env файле:**
```env
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...
GROQ_API_KEY=gsk_...
```

---

### 3. Таблица `results` (Результаты)

Хранит сохраненные пользователем ответы от нейросетей.

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Уникальный идентификатор результата |
| `prompt_id` | INTEGER | NOT NULL | Ссылка на промт из таблицы `prompts` (FOREIGN KEY) |
| `model_id` | INTEGER | NOT NULL | Ссылка на модель из таблицы `models` (FOREIGN KEY) |
| `response_text` | TEXT | NOT NULL | Текст ответа от нейросети |
| `selected` | INTEGER | NOT NULL DEFAULT 1 | Флаг выбора (1 - был выбран для сохранения, 0 - не выбран) |
| `created_at` | TEXT | NOT NULL | Дата и время создания результата (формат: ISO 8601) |

**Индексы:**
- `idx_results_prompt` на поле `prompt_id` (для быстрого поиска по промту)
- `idx_results_model` на поле `model_id` (для быстрого поиска по модели)
- `idx_results_created` на поле `created_at` (для сортировки по дате)

**Внешние ключи:**
- `prompt_id` → `prompts.id` (ON DELETE CASCADE)
- `model_id` → `models.id` (ON DELETE SET NULL или RESTRICT)

**Пример данных:**
```sql
INSERT INTO results (prompt_id, model_id, response_text, selected, created_at) VALUES 
(1, 1, 'Квантовая физика изучает поведение частиц на атомном уровне...', 1, '2024-01-15 10:31:00'),
(1, 2, 'Квантовая механика - это раздел физики, который описывает...', 1, '2024-01-15 10:31:05');
```

---

### 4. Таблица `settings` (Настройки)

Хранит настройки приложения в формате ключ-значение.

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Уникальный идентификатор настройки |
| `key` | TEXT | NOT NULL UNIQUE | Ключ настройки (например: 'timeout', 'max_retries') |
| `value` | TEXT | NULL | Значение настройки (всегда TEXT, преобразование при чтении) |

**Индексы:**
- `idx_settings_key` на поле `key` (для быстрого поиска)

**Пример данных:**
```sql
INSERT INTO settings (key, value) VALUES 
('timeout', '30'),
('max_retries', '3'),
('default_model', 'GPT-4'),
('auto_save', 'false');
```

---

## Схема связей (ER-диаграмма)

```
prompts (1) ────< (N) results
                      │
                      │
models (1) ───────────┘

settings (независимая таблица)
```

**Описание связей:**
- Один промт (`prompts`) может иметь множество результатов (`results`)
- Одна модель (`models`) может иметь множество результатов (`results`)
- Настройки (`settings`) не связаны с другими таблицами

---

## SQL-скрипт создания базы данных

```sql
-- Таблица промтов
CREATE TABLE IF NOT EXISTS prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    prompt TEXT NOT NULL,
    tags TEXT
);

CREATE INDEX IF NOT EXISTS idx_prompts_date ON prompts(date);
CREATE INDEX IF NOT EXISTS idx_prompts_tags ON prompts(tags);

-- Таблица моделей
CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    api_url TEXT NOT NULL,
    api_id TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_models_active ON models(is_active);

-- Таблица результатов
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id INTEGER NOT NULL,
    model_id INTEGER NOT NULL,
    response_text TEXT NOT NULL,
    selected INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE,
    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_results_prompt ON results(prompt_id);
CREATE INDEX IF NOT EXISTS idx_results_model ON results(model_id);
CREATE INDEX IF NOT EXISTS idx_results_created ON results(created_at);

-- Таблица настроек
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key);
```

---

## Примечания по реализации

1. **Временная таблица результатов** не хранится в БД - она создается в памяти приложения (например, в виде списка словарей или объектов) и отображается в GUI.

2. **API-ключи** хранятся в файле `.env` в корне проекта. Формат:
   ```
   OPENAI_API_KEY=sk-...
   DEEPSEEK_API_KEY=sk-...
   GROQ_API_KEY=gsk_...
   ```

3. **Даты** хранятся в формате ISO 8601 (текстовый формат) для простоты. При необходимости можно использовать функции SQLite для работы с датами.

4. **Теги** хранятся как строка с разделителями (запятая). При необходимости можно создать отдельную таблицу `tags` и таблицу связи `prompt_tags` для нормализации.

5. **Флаг `selected`** в таблице `results` может быть избыточным, так как все сохраненные результаты по определению были выбраны. Можно оставить для истории или удалить, если не требуется.
