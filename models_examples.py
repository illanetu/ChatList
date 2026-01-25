"""
Примеры бесплатных моделей OpenRouter для добавления в базу данных.
Все модели используют API ID: OPENROUTER_API_KEY
"""

# Список бесплатных моделей OpenRouter
FREE_MODELS = [
    {
        'name': 'google/gemini-flash-1.5',  # Используем Model ID как название
        'api_url': 'https://openrouter.ai/api/v1/chat/completions',
        'api_id': 'OPENROUTER_API_KEY',
        'is_active': 1
    },
    {
        'name': 'meta-llama/llama-3.2-3b-instruct:free',  # Используем Model ID как название
        'api_url': 'https://openrouter.ai/api/v1/chat/completions',
        'api_id': 'OPENROUTER_API_KEY',
        'is_active': 1
    },
    {
        'name': 'mistralai/mistral-7b-instruct:free',  # Используем Model ID как название
        'api_url': 'https://openrouter.ai/api/v1/chat/completions',
        'api_id': 'OPENROUTER_API_KEY',
        'is_active': 1
    },
    {
        'name': 'microsoft/phi-3-mini-128k-instruct:free',  # Используем Model ID как название
        'api_url': 'https://openrouter.ai/api/v1/chat/completions',
        'api_id': 'OPENROUTER_API_KEY',
        'is_active': 1
    },
    {
        'name': 'qwen/qwen-2.5-7b-instruct:free',  # Используем Model ID как название
        'api_url': 'https://openrouter.ai/api/v1/chat/completions',
        'api_id': 'OPENROUTER_API_KEY',
        'is_active': 1
    }
]


def add_free_models_to_db():
    """
    Добавляет бесплатные модели OpenRouter в базу данных.
    Запустите этот скрипт для автоматического добавления моделей.
    """
    import db
    
    print("Добавление бесплатных моделей OpenRouter в базу данных...")
    
    for model in FREE_MODELS:
        try:
            # Проверяем, существует ли модель с таким именем
            existing_models = db.get_all_models()
            model_exists = any(m['name'] == model['name'] for m in existing_models)
            
            if not model_exists:
                db.create_model(
                    name=model['name'],
                    api_url=model['api_url'],
                    api_id=model['api_id'],
                    is_active=model['is_active']
                )
                print(f"[OK] Добавлена модель: {model['name']}")
            else:
                print(f"[SKIP] Модель уже существует: {model['name']}")
        except Exception as e:
            print(f"[ERROR] Ошибка при добавлении {model['name']}: {str(e)}")
    
    print("\nГотово! Модели добавлены в базу данных.")
    print("\nПримечание: В поле 'model' при отправке запроса используйте model_id из списка выше.")


if __name__ == "__main__":
    import db
    # Инициализируем БД
    db.init_database()
    # Добавляем модели
    add_free_models_to_db()
