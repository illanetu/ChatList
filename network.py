"""
Модуль для отправки запросов к API различных нейросетей.
Поддерживает OpenAI, DeepSeek, Groq, OpenRouter и другие модели.
"""

import os
import requests
from typing import Dict, Optional, Any
from dotenv import load_dotenv
from abc import ABC, abstractmethod


# Загружаем переменные окружения из .env файла
load_dotenv()


def load_api_keys() -> Dict[str, Optional[str]]:
    """
    Загружает все API ключи из .env файла.
    Возвращает словарь с ключами.
    """
    keys = {}
    # Список возможных API ключей
    api_key_names = [
        'OPENAI_API_KEY',
        'DEEPSEEK_API_KEY',
        'GROQ_API_KEY',
        'OPENROUTER_API_KEY',
    ]
    
    for key_name in api_key_names:
        keys[key_name] = os.getenv(key_name)
    
    return keys


def get_api_key(api_id: str) -> Optional[str]:
    """
    Получает API ключ по идентификатору из переменных окружения.
    
    Args:
        api_id: Идентификатор переменной окружения (например, 'OPENAI_API_KEY')
    
    Returns:
        Значение API ключа или None, если ключ не найден
    """
    return os.getenv(api_id)


class BaseAPIClient(ABC):
    """Базовый класс для работы с API различных моделей."""
    
    def __init__(self, api_key: str, api_url: str, timeout: int = 30):
        """
        Инициализирует клиент API.
        
        Args:
            api_key: API ключ
            api_url: URL API endpoint
            timeout: Таймаут запроса в секундах
        """
        self.api_key = api_key
        self.api_url = api_url
        self.timeout = timeout
    
    @abstractmethod
    def send_request(self, prompt: str, model_name: Optional[str] = None) -> str:
        """
        Отправляет запрос к API и возвращает ответ.
        
        Args:
            prompt: Текст промта
            model_name: Название модели (опционально)
        
        Returns:
            Текст ответа от модели
        
        Raises:
            Exception: При ошибке запроса
        """
        pass
    
    def _handle_error(self, response: requests.Response) -> None:
        """Обрабатывает ошибки HTTP запроса."""
        if response.status_code == 401:
            raise Exception("Неверный API ключ")
        elif response.status_code == 429:
            raise Exception("Превышен лимит запросов")
        elif response.status_code >= 500:
            raise Exception(f"Ошибка сервера: {response.status_code}")
        else:
            raise Exception(f"Ошибка API: {response.status_code} - {response.text}")


class OpenAIClient(BaseAPIClient):
    """Клиент для работы с OpenAI API (GPT-4, GPT-3.5 и т.д.)."""
    
    def __init__(self, api_key: str, api_url: str = "https://api.openai.com/v1/chat/completions", timeout: int = 30):
        super().__init__(api_key, api_url, timeout)
        self.default_model = "gpt-3.5-turbo"
    
    def send_request(self, prompt: str, model_name: Optional[str] = None) -> str:
        """Отправляет запрос к OpenAI API."""
        if not self.api_key:
            raise Exception("API ключ OpenAI не установлен")
        
        model = model_name or self.default_model
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        
        try:
            response = requests.post(
                self.api_url,
                json=data,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                self._handle_error(response)
        except requests.exceptions.Timeout:
            raise Exception("Превышено время ожидания ответа от OpenAI")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ошибка сети при запросе к OpenAI: {str(e)}")


class DeepSeekClient(BaseAPIClient):
    """Клиент для работы с DeepSeek API."""
    
    def __init__(self, api_key: str, api_url: str = "https://api.deepseek.com/v1/chat/completions", timeout: int = 30):
        super().__init__(api_key, api_url, timeout)
        self.default_model = "deepseek-chat"
    
    def send_request(self, prompt: str, model_name: Optional[str] = None) -> str:
        """Отправляет запрос к DeepSeek API."""
        if not self.api_key:
            raise Exception("API ключ DeepSeek не установлен")
        
        model = model_name or self.default_model
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        
        try:
            response = requests.post(
                self.api_url,
                json=data,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                self._handle_error(response)
        except requests.exceptions.Timeout:
            raise Exception("Превышено время ожидания ответа от DeepSeek")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ошибка сети при запросе к DeepSeek: {str(e)}")


class GroqClient(BaseAPIClient):
    """Клиент для работы с Groq API."""
    
    def __init__(self, api_key: str, api_url: str = "https://api.groq.com/openai/v1/chat/completions", timeout: int = 30):
        super().__init__(api_key, api_url, timeout)
        self.default_model = "llama-3.1-8b-instant"
    
    def send_request(self, prompt: str, model_name: Optional[str] = None) -> str:
        """Отправляет запрос к Groq API."""
        if not self.api_key:
            raise Exception("API ключ Groq не установлен")
        
        model = model_name or self.default_model
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        
        try:
            response = requests.post(
                self.api_url,
                json=data,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                self._handle_error(response)
        except requests.exceptions.Timeout:
            raise Exception("Превышено время ожидания ответа от Groq")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ошибка сети при запросе к Groq: {str(e)}")


class OpenRouterClient(BaseAPIClient):
    """Клиент для работы с OpenRouter API."""
    
    def __init__(self, api_key: str, api_url: str = "https://openrouter.ai/api/v1/chat/completions", timeout: int = 30):
        super().__init__(api_key, api_url, timeout)
        self.default_model = "openai/gpt-3.5-turbo"
    
    def send_request(self, prompt: str, model_name: Optional[str] = None) -> str:
        """Отправляет запрос к OpenRouter API."""
        if not self.api_key:
            raise Exception("API ключ OpenRouter не установлен")
        
        # Для OpenRouter model_name может быть либо Model ID (содержит слэш), либо название модели
        # Если model_name содержит слэш, используем его как Model ID
        # Иначе используем default_model
        if model_name and '/' in model_name:
            model = model_name  # Это Model ID (например, "google/gemini-flash-1.5")
        else:
            model = model_name or self.default_model
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/chatlist",  # Опционально, для отслеживания
            "X-Title": "ChatList"  # Опционально
        }
        
        data = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        
        try:
            response = requests.post(
                self.api_url,
                json=data,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                self._handle_error(response)
        except requests.exceptions.Timeout:
            raise Exception("Превышено время ожидания ответа от OpenRouter")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ошибка сети при запросе к OpenRouter: {str(e)}")


def get_api_client(model_data: Dict[str, Any]) -> BaseAPIClient:
    """
    Фабрика для создания клиента API на основе данных модели.
    
    Args:
        model_data: Словарь с данными модели (name, api_url, api_id)
    
    Returns:
        Экземпляр соответствующего клиента API
    """
    api_id = model_data.get('api_id', '')
    api_url = model_data.get('api_url', '')
    api_key = get_api_key(api_id)
    
    if not api_key:
        raise Exception(f"API ключ не найден для {api_id}")
    
    # Определяем тип клиента по URL или имени
    name = model_data.get('name', '').lower()
    
    if 'openrouter' in api_url.lower() or 'openrouter' in name:
        return OpenRouterClient(api_key, api_url)
    elif 'openai' in api_url.lower() or 'openai' in name:
        return OpenAIClient(api_key, api_url)
    elif 'deepseek' in api_url.lower() or 'deepseek' in name:
        return DeepSeekClient(api_key, api_url)
    elif 'groq' in api_url.lower() or 'groq' in name:
        return GroqClient(api_key, api_url)
    else:
        # По умолчанию используем OpenAI-совместимый формат
        return OpenAIClient(api_key, api_url)


def send_request(model_data: Dict[str, Any], prompt: str) -> str:
    """
    Удобная функция для отправки запроса к модели.
    
    Args:
        model_data: Словарь с данными модели из БД
        prompt: Текст промта
    
    Returns:
        Текст ответа от модели
    """
    client = get_api_client(model_data)
    # Передаем название модели (которое может быть Model ID для OpenRouter)
    model_name = model_data.get('name')
    return client.send_request(prompt, model_name=model_name)
