"""
Модуль для работы с базой данных SQLite.
Инкапсулирует все операции с БД для приложения ChatList.
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Any


DB_FILE = "chatlist.db"


def get_connection():
    """Создает и возвращает соединение с базой данных."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Для доступа к колонкам по имени
    return conn


def init_database():
    """Инициализирует базу данных, создавая все необходимые таблицы."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Таблица промтов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                prompt TEXT NOT NULL,
                tags TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_prompts_date ON prompts(date)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_prompts_tags ON prompts(tags)
        """)
        
        # Таблица моделей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                api_url TEXT NOT NULL,
                api_id TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_models_active ON models(is_active)
        """)
        
        # Таблица результатов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_id INTEGER NOT NULL,
                model_id INTEGER NOT NULL,
                response_text TEXT NOT NULL,
                selected INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE,
                FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE RESTRICT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_results_prompt ON results(prompt_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_results_model ON results(model_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_results_created ON results(created_at)
        """)
        
        # Таблица настроек
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key)
        """)
        
        conn.commit()
        
    except sqlite3.Error as e:
        conn.rollback()
        raise Exception(f"Ошибка при создании базы данных: {e}")
    finally:
        conn.close()


# ==================== CRUD операции для таблицы prompts ====================

def create_prompt(prompt: str, tags: Optional[str] = None) -> int:
    """Создает новый промт и возвращает его ID."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO prompts (date, prompt, tags) VALUES (?, ?, ?)",
            (date, prompt, tags)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        conn.rollback()
        raise Exception(f"Ошибка при создании промта: {e}")
    finally:
        conn.close()


def get_all_prompts() -> List[Dict[str, Any]]:
    """Возвращает все промты."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM prompts ORDER BY date DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise Exception(f"Ошибка при получении промтов: {e}")
    finally:
        conn.close()


def get_prompt_by_id(prompt_id: int) -> Optional[Dict[str, Any]]:
    """Возвращает промт по ID."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        raise Exception(f"Ошибка при получении промта: {e}")
    finally:
        conn.close()


def search_prompts(query: str) -> List[Dict[str, Any]]:
    """Ищет промты по тексту запроса или тегам."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        search_pattern = f"%{query}%"
        cursor.execute(
            "SELECT * FROM prompts WHERE prompt LIKE ? OR tags LIKE ? ORDER BY date DESC",
            (search_pattern, search_pattern)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise Exception(f"Ошибка при поиске промтов: {e}")
    finally:
        conn.close()


def update_prompt(prompt_id: int, prompt: str, tags: Optional[str] = None) -> bool:
    """Обновляет промт."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "UPDATE prompts SET prompt = ?, tags = ? WHERE id = ?",
            (prompt, tags, prompt_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        conn.rollback()
        raise Exception(f"Ошибка при обновлении промта: {e}")
    finally:
        conn.close()


def delete_prompt(prompt_id: int) -> bool:
    """Удаляет промт."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        conn.rollback()
        raise Exception(f"Ошибка при удалении промта: {e}")
    finally:
        conn.close()


# ==================== CRUD операции для таблицы models ====================

def create_model(name: str, api_url: str, api_id: str, is_active: int = 1) -> int:
    """Создает новую модель и возвращает ее ID."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO models (name, api_url, api_id, is_active) VALUES (?, ?, ?, ?)",
            (name, api_url, api_id, is_active)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        conn.rollback()
        raise Exception(f"Ошибка при создании модели: {e}")
    finally:
        conn.close()


def get_all_models() -> List[Dict[str, Any]]:
    """Возвращает все модели."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM models ORDER BY name")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise Exception(f"Ошибка при получении моделей: {e}")
    finally:
        conn.close()


def get_active_models() -> List[Dict[str, Any]]:
    """Возвращает только активные модели."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM models WHERE is_active = 1 ORDER BY name")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise Exception(f"Ошибка при получении активных моделей: {e}")
    finally:
        conn.close()


def update_model(model_id: int, **kwargs) -> bool:
    """Обновляет модель. Принимает именованные аргументы для обновления."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        allowed_fields = ['name', 'api_url', 'api_id', 'is_active']
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if not updates:
            return False
        
        values.append(model_id)
        query = f"UPDATE models SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, values)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        conn.rollback()
        raise Exception(f"Ошибка при обновлении модели: {e}")
    finally:
        conn.close()


def toggle_model_active(model_id: int, is_active: int) -> bool:
    """Переключает активность модели."""
    return update_model(model_id, is_active=is_active)


def delete_model(model_id: int) -> bool:
    """Удаляет модель."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM models WHERE id = ?", (model_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        conn.rollback()
        raise Exception(f"Ошибка при удалении модели: {e}")
    finally:
        conn.close()


# ==================== CRUD операции для таблицы results ====================

def save_results(results_list: List[Dict[str, Any]]) -> int:
    """
    Сохраняет список результатов в БД.
    Каждый результат должен содержать: prompt_id, model_id, response_text
    Возвращает количество сохраненных записей.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        count = 0
        
        for result in results_list:
            cursor.execute(
                """INSERT INTO results (prompt_id, model_id, response_text, selected, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (result['prompt_id'], result['model_id'], result['response_text'], 1, created_at)
            )
            count += 1
        
        conn.commit()
        return count
    except sqlite3.Error as e:
        conn.rollback()
        raise Exception(f"Ошибка при сохранении результатов: {e}")
    finally:
        conn.close()


def get_all_results() -> List[Dict[str, Any]]:
    """Возвращает все сохраненные результаты."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT r.*, p.prompt, m.name as model_name
            FROM results r
            LEFT JOIN prompts p ON r.prompt_id = p.id
            LEFT JOIN models m ON r.model_id = m.id
            ORDER BY r.created_at DESC
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise Exception(f"Ошибка при получении результатов: {e}")
    finally:
        conn.close()


def get_results_by_prompt(prompt_id: int) -> List[Dict[str, Any]]:
    """Возвращает результаты по ID промта."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT r.*, p.prompt, m.name as model_name
            FROM results r
            LEFT JOIN prompts p ON r.prompt_id = p.id
            LEFT JOIN models m ON r.model_id = m.id
            WHERE r.prompt_id = ?
            ORDER BY r.created_at DESC
        """, (prompt_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise Exception(f"Ошибка при получении результатов: {e}")
    finally:
        conn.close()


def search_results(query: str) -> List[Dict[str, Any]]:
    """Ищет результаты по тексту ответа или промта."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        search_pattern = f"%{query}%"
        cursor.execute("""
            SELECT r.*, p.prompt, m.name as model_name
            FROM results r
            LEFT JOIN prompts p ON r.prompt_id = p.id
            LEFT JOIN models m ON r.model_id = m.id
            WHERE r.response_text LIKE ? OR p.prompt LIKE ?
            ORDER BY r.created_at DESC
        """, (search_pattern, search_pattern))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise Exception(f"Ошибка при поиске результатов: {e}")
    finally:
        conn.close()


def delete_result(result_id: int) -> bool:
    """Удаляет результат."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM results WHERE id = ?", (result_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        conn.rollback()
        raise Exception(f"Ошибка при удалении результата: {e}")
    finally:
        conn.close()


# ==================== Операции для таблицы settings ====================

def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """Получает значение настройки по ключу."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row['value'] if row else default
    except sqlite3.Error as e:
        raise Exception(f"Ошибка при получении настройки: {e}")
    finally:
        conn.close()


def set_setting(key: str, value: str) -> bool:
    """Устанавливает значение настройки."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        conn.rollback()
        raise Exception(f"Ошибка при установке настройки: {e}")
    finally:
        conn.close()


# ==================== Настройки AI-ассистента для улучшения промтов ====================

def get_prompt_improver_model() -> Optional[int]:
    """
    Получает ID модели для улучшения промтов.
    
    Returns:
        ID модели или None, если не установлено
    """
    model_id = get_setting('prompt_improver_model')
    if model_id:
        try:
            return int(model_id)
        except:
            return None
    return None


def set_prompt_improver_model(model_id: Optional[int]) -> bool:
    """
    Устанавливает модель для улучшения промтов.
    
    Args:
        model_id: ID модели или None для сброса
    
    Returns:
        True при успехе
    """
    if model_id is None:
        return set_setting('prompt_improver_model', '')
    return set_setting('prompt_improver_model', str(model_id))


def is_prompt_improver_enabled() -> bool:
    """
    Проверяет, включен ли AI-ассистент для улучшения промтов.
    
    Returns:
        True если включен, False иначе
    """
    enabled = get_setting('prompt_improver_enabled', '1')
    return enabled == '1'


def set_prompt_improver_enabled(enabled: bool) -> bool:
    """
    Включает или выключает AI-ассистент для улучшения промтов.
    
    Args:
        enabled: True для включения, False для выключения
    
    Returns:
        True при успехе
    """
    return set_setting('prompt_improver_enabled', '1' if enabled else '0')


# ==================== Настройки темы и шрифта ====================

def get_theme() -> str:
    """
    Получает текущую тему приложения.
    
    Returns:
        'light' или 'dark', по умолчанию 'light'
    """
    theme = get_setting('theme', 'light')
    if theme in ['light', 'dark']:
        return theme
    return 'light'


def set_theme(theme_name: str) -> bool:
    """
    Устанавливает тему приложения.
    
    Args:
        theme_name: 'light' или 'dark'
    
    Returns:
        True при успехе
    """
    if theme_name in ['light', 'dark']:
        return set_setting('theme', theme_name)
    return False


def get_font_size() -> int:
    """
    Получает размер шрифта приложения.
    
    Returns:
        Размер шрифта в пунктах, по умолчанию 10
    """
    font_size = get_setting('font_size', '10')
    try:
        size = int(font_size)
        if 8 <= size <= 24:
            return size
    except:
        pass
    return 10


def set_font_size(size: int) -> bool:
    """
    Устанавливает размер шрифта приложения.
    
    Args:
        size: Размер шрифта в пунктах (8-24)
    
    Returns:
        True при успехе
    """
    if 8 <= size <= 24:
        return set_setting('font_size', str(size))
    return False
