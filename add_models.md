# Инструкция по добавлению бесплатных моделей OpenRouter

## 5 бесплатных моделей OpenRouter

Следующие модели доступны бесплатно через OpenRouter API:

### 1. Google Gemini Flash 1.5
- **Название (Model ID)**: `google/gemini-flash-1.5`
- **Описание**: Быстрая и эффективная модель от Google
- **API URL**: `https://openrouter.ai/api/v1/chat/completions`
- **API ID**: `OPENROUTER_API_KEY`

### 2. Meta Llama 3.2 3B Instruct
- **Название (Model ID)**: `meta-llama/llama-3.2-3b-instruct:free`
- **Описание**: Компактная модель от Meta, оптимизированная для инструкций
- **API URL**: `https://openrouter.ai/api/v1/chat/completions`
- **API ID**: `OPENROUTER_API_KEY`

### 3. Mistral 7B Instruct
- **Название (Model ID)**: `mistralai/mistral-7b-instruct:free`
- **Описание**: Мощная модель от Mistral AI для выполнения инструкций
- **API URL**: `https://openrouter.ai/api/v1/chat/completions`
- **API ID**: `OPENROUTER_API_KEY`

### 4. Microsoft Phi-3 Mini
- **Название (Model ID)**: `microsoft/phi-3-mini-128k-instruct:free`
- **Описание**: Легковесная модель от Microsoft с большим контекстом
- **API URL**: `https://openrouter.ai/api/v1/chat/completions`
- **API ID**: `OPENROUTER_API_KEY`

### 5. Qwen 2.5 7B Instruct
- **Название (Model ID)**: `qwen/qwen-2.5-7b-instruct:free`
- **Описание**: Модель от Alibaba Cloud, оптимизированная для инструкций
- **API URL**: `https://openrouter.ai/api/v1/chat/completions`
- **API ID**: `OPENROUTER_API_KEY`

## Способы добавления моделей

### Способ 1: Автоматическое добавление (рекомендуется)

Запустите скрипт для автоматического добавления всех 5 моделей:

```powershell
python models_examples.py
```

### Способ 2: Ручное добавление через интерфейс

1. Запустите приложение: `python main.py`
2. Перейдите в меню **Настройки → Управление моделями**
3. Нажмите **Добавить**
4. Заполните форму для каждой модели:
   - **Название**: Model ID (например, `google/gemini-flash-1.5`)
   - **API URL**: `https://openrouter.ai/api/v1/chat/completions`
   - **API ID**: `OPENROUTER_API_KEY`
   - **Активна**: ✓ (включите чекбокс)

### Способ 3: Добавление через Python

```python
import db

db.init_database()

# Добавьте модель (используйте Model ID как название)
db.create_model(
    name="google/gemini-flash-1.5",  # Model ID
    api_url="https://openrouter.ai/api/v1/chat/completions",
    api_id="OPENROUTER_API_KEY",
    is_active=1
)
```

## Важно!

⚠️ **Примечание о Model ID**: 
Для OpenRouter в поле "Название" нужно указывать Model ID (например, `google/gemini-flash-1.5`). Приложение автоматически распознает Model ID по наличию слэша в названии и использует его при отправке запроса.

Для работы с OpenRouter убедитесь, что:
1. В файле `.env` указан `OPENROUTER_API_KEY`
2. Модели добавлены в базу данных
3. Модели помечены как активные (is_active = 1)

## Проверка работы

После добавления моделей:
1. Введите промт в приложении
2. Нажмите "Отправить запрос"
3. Проверьте, что запросы отправляются во все активные модели
4. Просмотрите результаты в таблице
