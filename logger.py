"""
Модуль для логирования запросов и операций приложения.
"""

import logging
import os
from datetime import datetime
from typing import Optional


LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "chatlist.log")


def setup_logger():
    """Настраивает логгер для приложения."""
    # Создаем директорию для логов, если её нет
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    
    # Настраиваем формат логирования
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Настраиваем логгер
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler()  # Также выводим в консоль
        ]
    )
    
    logger = logging.getLogger('ChatList')
    return logger


def log_startup(version_str: str):
    """Логирует запуск приложения с указанием версии."""
    logging.getLogger('ChatList').info("ChatList v%s запущен", version_str)


def log_request(prompt: str, model_name: str, success: bool, response: Optional[str] = None, error: Optional[str] = None):
    """
    Логирует запрос к API.
    
    Args:
        prompt: Текст промта
        model_name: Название модели
        success: Успешность запроса
        response: Ответ модели (если успешно)
        error: Текст ошибки (если неуспешно)
    """
    logger = logging.getLogger('ChatList')
    
    if success:
        logger.info(f"Запрос к {model_name}: Успешно (длина ответа: {len(response) if response else 0} символов)")
    else:
        logger.error(f"Запрос к {model_name}: Ошибка - {error}")
    
    # Дополнительное логирование в отдельный файл запросов
    request_log_file = os.path.join(LOG_DIR, "requests.log")
    with open(request_log_file, 'a', encoding='utf-8') as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"[{timestamp}] {model_name} - {'SUCCESS' if success else 'ERROR'}\n")
        f.write(f"Промт: {prompt[:100]}...\n")
        if success and response:
            f.write(f"Ответ: {response[:200]}...\n")
        elif error:
            f.write(f"Ошибка: {error}\n")
        f.write("\n")


def log_database_operation(operation: str, table: str, success: bool, error: Optional[str] = None):
    """
    Логирует операцию с базой данных.
    
    Args:
        operation: Тип операции (CREATE, UPDATE, DELETE, SELECT)
        table: Название таблицы
        success: Успешность операции
        error: Текст ошибки (если неуспешно)
    """
    logger = logging.getLogger('ChatList')
    
    if success:
        logger.debug(f"БД: {operation} в таблице {table} - Успешно")
    else:
        logger.error(f"БД: {operation} в таблице {table} - Ошибка: {error}")
