"""
Модуль для улучшения промтов с помощью AI-ассистента.
Использует существующие модели через network.py для улучшения и переформулировки промтов.
"""

from typing import Dict, List, Optional, Any
import network
import models
import re


# Типы улучшения промтов
IMPROVEMENT_TYPES = {
    'general': 'Общее улучшение',
    'rephrase': 'Переформулировка',
    'code': 'Адаптация под код',
    'analysis': 'Адаптация под анализ',
    'creative': 'Адаптация под креатив'
}


def get_improvement_prompt(improvement_type: str, original_prompt: str) -> str:
    """
    Формирует системный промт для улучшения в зависимости от типа.
    
    Args:
        improvement_type: Тип улучшения ('general', 'rephrase', 'code', 'analysis', 'creative')
        original_prompt: Исходный промт для улучшения
    
    Returns:
        Системный промт для отправки в модель
    """
    base_instruction = """Ты помощник для улучшения промтов. Твоя задача - улучшить промт пользователя, сделав его более четким, структурированным и эффективным.

Исходный промт пользователя:
"""
    
    if improvement_type == 'general':
        return f"""{base_instruction}
{original_prompt}

Улучши этот промт, сделав его:
- Более четким и понятным
- Структурированным (если нужно)
- С конкретными инструкциями
- Без лишних слов

Верни улучшенную версию промта. Затем добавь раздел "Альтернативные варианты:" и предложи 2-3 альтернативных формулировки того же запроса."""
    
    elif improvement_type == 'rephrase':
        return f"""{base_instruction}
{original_prompt}

Переформулируй этот промт, сохраняя его смысл, но изменив формулировку. Предложи:
1. Улучшенную версию (основную)
2. 2-3 альтернативных варианта переформулировки

Каждый вариант должен быть четким и понятным."""
    
    elif improvement_type == 'code':
        return f"""{base_instruction}
{original_prompt}

Адаптируй этот промт для технических задач и программирования. Сделай его:
- Технически точным
- С конкретными требованиями к коду
- С указанием языка программирования (если применимо)
- С примерами или спецификациями (если нужно)

Верни улучшенную версию и 2-3 альтернативных формулировки для разных подходов."""
    
    elif improvement_type == 'analysis':
        return f"""{base_instruction}
{original_prompt}

Адаптируй этот промт для аналитических задач. Сделай его:
- Сфокусированным на анализе данных
- С четкими критериями оценки
- С указанием формата вывода (если нужно)
- Структурированным для логического анализа

Верни улучшенную версию и 2-3 альтернативных формулировки."""
    
    elif improvement_type == 'creative':
        return f"""{base_instruction}
{original_prompt}

Адаптируй этот промт для творческих задач. Сделай его:
- Вдохновляющим и креативным
- С пространством для творчества
- С указанием стиля или тона (если нужно)
- С акцентом на оригинальность

Верни улучшенную версию и 2-3 альтернативных формулировки для разных творческих подходов."""
    
    else:
        # По умолчанию - общее улучшение
        return get_improvement_prompt('general', original_prompt)


def parse_improvement_response(response_text: str) -> Dict[str, Any]:
    """
    Парсит ответ от AI и извлекает улучшенную версию и альтернативы.
    
    Args:
        response_text: Текст ответа от модели
    
    Returns:
        Словарь с ключами:
        - 'improved': улучшенная версия промта
        - 'alternatives': список альтернативных вариантов (2-3 штуки)
    """
    result = {
        'improved': '',
        'alternatives': []
    }
    
    if not response_text:
        return result
    
    # Пытаемся найти улучшенную версию и альтернативы
    text = response_text.strip()
    
    # Ищем разделители для альтернатив
    alternatives_markers = [
        'Альтернативные варианты:',
        'Альтернативные варианты',
        'Варианты:',
        'Варианты',
        'Альтернативы:',
        'Альтернативы',
        'Другие варианты:',
        'Другие варианты'
    ]
    
    # Разделяем на основную часть и альтернативы
    main_text = text
    alternatives_text = ""
    
    for marker in alternatives_markers:
        if marker in text:
            parts = text.split(marker, 1)
            if len(parts) == 2:
                main_text = parts[0].strip()
                alternatives_text = parts[1].strip()
                break
    
    # Извлекаем улучшенную версию (первый абзац или до первого списка)
    lines = main_text.split('\n')
    improved_lines = []
    
    for line in lines:
        line = line.strip()
        # Пропускаем пустые строки в начале
        if not improved_lines and not line:
            continue
        # Останавливаемся на маркерах списков или разделителях
        if line.startswith(('-', '*', '1.', '2.', '3.', '•')) or any(marker in line for marker in alternatives_markers):
            break
        improved_lines.append(line)
    
    result['improved'] = '\n'.join(improved_lines).strip()
    
    # Если улучшенная версия пустая, берем весь основной текст
    if not result['improved']:
        result['improved'] = main_text.strip()
    
    # Извлекаем альтернативы
    if alternatives_text:
        # Парсим список альтернатив
        alt_lines = alternatives_text.split('\n')
        current_alt = []
        
        for line in alt_lines:
            line = line.strip()
            if not line:
                if current_alt:
                    alt_text = '\n'.join(current_alt).strip()
                    # Убираем маркеры списка
                    alt_text = re.sub(r'^[-*•]\s*', '', alt_text)
                    alt_text = re.sub(r'^\d+[.)]\s*', '', alt_text)
                    if alt_text:
                        result['alternatives'].append(alt_text)
                    current_alt = []
                continue
            
            # Проверяем, начинается ли новая альтернатива
            if re.match(r'^[-*•]\s+', line) or re.match(r'^\d+[.)]\s+', line):
                if current_alt:
                    alt_text = '\n'.join(current_alt).strip()
                    alt_text = re.sub(r'^[-*•]\s*', '', alt_text)
                    alt_text = re.sub(r'^\d+[.)]\s*', '', alt_text)
                    if alt_text:
                        result['alternatives'].append(alt_text)
                current_alt = [line]
            else:
                current_alt.append(line)
        
        # Добавляем последнюю альтернативу
        if current_alt:
            alt_text = '\n'.join(current_alt).strip()
            alt_text = re.sub(r'^[-*•]\s*', '', alt_text)
            alt_text = re.sub(r'^\d+[.)]\s*', '', alt_text)
            if alt_text:
                result['alternatives'].append(alt_text)
    
    # Если альтернативы не найдены, пытаемся найти их в основном тексте
    if not result['alternatives']:
        # Ищем нумерованные или маркированные списки
        lines = text.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            # Проверяем маркеры списка
            if re.match(r'^[-*•]\s+', line) or re.match(r'^\d+[.)]\s+', line):
                alt_text = re.sub(r'^[-*•]\s*', '', line)
                alt_text = re.sub(r'^\d+[.)]\s*', '', alt_text)
                if alt_text and alt_text not in result['alternatives']:
                    result['alternatives'].append(alt_text)
                    if len(result['alternatives']) >= 3:
                        break
    
    # Ограничиваем количество альтернатив до 3
    result['alternatives'] = result['alternatives'][:3]
    
    # Если улучшенная версия все еще пустая, используем весь ответ
    if not result['improved']:
        result['improved'] = text.split('\n')[0].strip() or text[:200].strip()
    
    return result


def improve_prompt(prompt: str, model_data: Optional[Dict[str, Any]] = None, 
                   improvement_type: str = 'general') -> Dict[str, Any]:
    """
    Улучшает промт с помощью указанной модели.
    
    Args:
        prompt: Исходный промт для улучшения
        model_data: Данные модели из БД (если None, используется модель по умолчанию)
        improvement_type: Тип улучшения ('general', 'rephrase', 'code', 'analysis', 'creative')
    
    Returns:
        Словарь с результатами:
        - 'improved': улучшенная версия промта
        - 'alternatives': список альтернативных вариантов
        - 'error': текст ошибки (если была)
    """
    if not prompt or not prompt.strip():
        return {
            'improved': '',
            'alternatives': [],
            'error': 'Промт не может быть пустым'
        }
    
    # Формируем системный промт для улучшения
    system_prompt = get_improvement_prompt(improvement_type, prompt)
    
    try:
        # Если модель не указана, используем первую активную модель
        if not model_data:
            active_models = models.get_active_models()
            if not active_models:
                return {
                    'improved': '',
                    'alternatives': [],
                    'error': 'Нет активных моделей для улучшения промта'
                }
            model = active_models[0]
            model_data = {
                'name': model.name,
                'api_url': model.api_url,
                'api_id': model.api_id
            }
        
        # Отправляем запрос через network.py
        response_text = network.send_request(model_data, system_prompt)
        
        # Парсим ответ
        result = parse_improvement_response(response_text)
        result['error'] = None
        
        return result
        
    except Exception as e:
        return {
            'improved': '',
            'alternatives': [],
            'error': str(e)
        }
