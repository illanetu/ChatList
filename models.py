"""
Модуль для логики работы с моделями нейросетей.
Управляет отправкой запросов в несколько моделей и обработкой результатов.
"""

from typing import List, Dict, Any, Optional
import db
import network


class Model:
    """Класс для представления модели нейросети."""
    
    def __init__(self, model_id: int, name: str, api_url: str, api_id: str, is_active: int = 1):
        """
        Инициализирует модель.
        
        Args:
            model_id: ID модели в БД
            name: Название модели
            api_url: URL API
            api_id: Идентификатор переменной окружения с API ключом
            is_active: Флаг активности (1 - активна, 0 - неактивна)
        """
        self.model_id = model_id
        self.name = name
        self.api_url = api_url
        self.api_id = api_id
        self.is_active = is_active
        self._api_key = None
    
    def get_api_key(self) -> Optional[str]:
        """Получает API ключ из переменных окружения по api_id."""
        if self._api_key is None:
            self._api_key = network.get_api_key(self.api_id)
        return self._api_key
    
    def send_request(self, prompt: str) -> str:
        """
        Отправляет запрос к модели через network.py.
        
        Args:
            prompt: Текст промта
        
        Returns:
            Текст ответа от модели
        
        Raises:
            Exception: При ошибке запроса
        """
        model_data = {
            'name': self.name,
            'api_url': self.api_url,
            'api_id': self.api_id
        }
        return network.send_request(model_data, prompt)
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует модель в словарь."""
        return {
            'id': self.model_id,
            'name': self.name,
            'api_url': self.api_url,
            'api_id': self.api_id,
            'is_active': self.is_active
        }


def get_active_models() -> List[Model]:
    """
    Получает список активных моделей из БД.
    
    Returns:
        Список объектов Model
    """
    models_data = db.get_active_models()
    result = []
    for model_data in models_data:
        # Преобразуем 'id' в 'model_id' для конструктора Model
        model_dict = dict(model_data)
        if 'id' in model_dict:
            model_dict['model_id'] = model_dict.pop('id')
        result.append(Model(**model_dict))
    return result


def get_all_models() -> List[Model]:
    """
    Получает все модели из БД.
    
    Returns:
        Список объектов Model
    """
    models_data = db.get_all_models()
    result = []
    for model_data in models_data:
        # Преобразуем 'id' в 'model_id' для конструктора Model
        model_dict = dict(model_data)
        if 'id' in model_dict:
            model_dict['model_id'] = model_dict.pop('id')
        result.append(Model(**model_dict))
    return result


def send_to_models(prompt: str, models: Optional[List[Model]] = None) -> List[Dict[str, Any]]:
    """
    Отправляет промт в несколько моделей и возвращает результаты.
    
    Args:
        prompt: Текст промта
        models: Список моделей для отправки. Если None, используются активные модели.
    
    Returns:
        Список словарей с результатами:
        [
            {
                'model_id': int,
                'model_name': str,
                'response_text': str,
                'error': str (если была ошибка),
                'selected': bool
            },
            ...
        ]
    """
    if models is None:
        models = get_active_models()
    
    results = []
    
    for model in models:
        if not model.is_active:
            continue
        
        result = {
            'model_id': model.model_id,
            'model_name': model.name,
            'response_text': '',
            'error': None,
            'selected': False
        }
        
        try:
            response = model.send_request(prompt)
            result['response_text'] = response
        except Exception as e:
            result['error'] = str(e)
            result['response_text'] = f"Ошибка: {str(e)}"
        
        results.append(result)
    
    return results


def create_temporary_results_table(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Создает временную таблицу результатов в памяти.
    Это просто возвращает список результатов с добавленными полями для GUI.
    
    Args:
        results: Список результатов от send_to_models()
    
    Returns:
        Список результатов, готовый для отображения в таблице
    """
    return results
