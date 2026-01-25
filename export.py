"""
Модуль для экспорта данных в различные форматы.
"""

import json
from typing import List, Dict, Any
from datetime import datetime


def export_to_markdown(results: List[Dict[str, Any]], prompt: str = "") -> str:
    """
    Экспортирует результаты в формат Markdown.
    
    Args:
        results: Список результатов для экспорта
        prompt: Текст промта (опционально)
    
    Returns:
        Строка в формате Markdown
    """
    md = []
    
    if prompt:
        md.append(f"# Промт\n\n{prompt}\n\n")
    
    md.append("## Результаты\n\n")
    md.append(f"*Экспортировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
    
    for i, result in enumerate(results, 1):
        model_name = result.get('model_name', 'Неизвестная модель')
        response_text = result.get('response_text', '')
        created_at = result.get('created_at', '')
        
        md.append(f"### {i}. {model_name}\n\n")
        if created_at:
            md.append(f"*Дата: {created_at}*\n\n")
        md.append(f"{response_text}\n\n")
        md.append("---\n\n")
    
    return "".join(md)


def export_to_json(results: List[Dict[str, Any]], prompt: str = "") -> str:
    """
    Экспортирует результаты в формат JSON.
    
    Args:
        results: Список результатов для экспорта
        prompt: Текст промта (опционально)
    
    Returns:
        JSON строка
    """
    data = {
        "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "prompt": prompt,
        "results": results
    }
    
    return json.dumps(data, ensure_ascii=False, indent=2)
