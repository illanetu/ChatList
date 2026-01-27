"""
Тестовая программа для просмотра и редактирования SQLite баз данных.
Отображает список таблиц, позволяет открыть таблицу с пагинацией и выполнять CRUD операции.
"""

import sys
import sqlite3
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QLabel, QFileDialog,
    QMessageBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit,
    QTextEdit, QGroupBox, QComboBox, QSpinBox
)
from PyQt5.QtCore import Qt
from typing import Optional, List, Dict, Any


class DatabaseViewer(QMainWindow):
    """Главное окно программы для просмотра БД."""
    
    def __init__(self):
        super().__init__()
        self.db_path = None
        self.connection = None
        self.current_table = None
        self.current_page = 1
        self.page_size = 50
        self.init_ui()
    
    def init_ui(self):
        """Инициализирует интерфейс."""
        self.setWindowTitle("Просмотр SQLite базы данных")
        self.setGeometry(100, 100, 1000, 700)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Кнопка выбора файла БД
        file_layout = QHBoxLayout()
        self.file_label = QLabel("База данных не выбрана")
        self.open_file_button = QPushButton("Выбрать файл БД")
        self.open_file_button.clicked.connect(self.on_open_file)
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.open_file_button)
        layout.addLayout(file_layout)
        
        # Список таблиц
        tables_group = QGroupBox("Таблицы")
        tables_layout = QVBoxLayout()
        
        self.tables_list = QTableWidget()
        self.tables_list.setColumnCount(2)
        self.tables_list.setHorizontalHeaderLabels(["Таблица", "Действие"])
        self.tables_list.setSelectionBehavior(QTableWidget.SelectRows)
        self.tables_list.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tables_list.setColumnWidth(0, 300)
        self.tables_list.setColumnWidth(1, 100)
        tables_layout.addWidget(self.tables_list)
        
        tables_group.setLayout(tables_layout)
        layout.addWidget(tables_group)
    
    def on_open_file(self):
        """Открывает диалог выбора файла БД."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл SQLite", "", "SQLite Files (*.db *.sqlite *.sqlite3);;All Files (*)"
        )
        
        if filename:
            try:
                self.db_path = filename
                self.file_label.setText(f"База данных: {filename}")
                self.connection = sqlite3.connect(filename)
                self.connection.row_factory = sqlite3.Row
                self.load_tables()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось открыть базу данных: {str(e)}")
    
    def load_tables(self):
        """Загружает список таблиц из БД."""
        if not self.connection:
            return
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            tables = cursor.fetchall()
            
            self.tables_list.setRowCount(len(tables))
            
            for i, table in enumerate(tables):
                table_name = table[0]
                self.tables_list.setItem(i, 0, QTableWidgetItem(table_name))
                
                # Кнопка "Открыть"
                open_button = QPushButton("Открыть")
                open_button.clicked.connect(lambda checked, name=table_name: self.on_open_table(name))
                self.tables_list.setCellWidget(i, 1, open_button)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить таблицы: {str(e)}")
    
    def on_open_table(self, table_name: str):
        """Открывает диалог просмотра таблицы."""
        if not self.connection:
            return
        
        dialog = TableViewDialog(self, self.connection, table_name)
        dialog.exec_()


class TableViewDialog(QDialog):
    """Диалог для просмотра и редактирования таблицы."""
    
    def __init__(self, parent=None, connection: Optional[sqlite3.Connection] = None, table_name: str = ""):
        super().__init__(parent)
        self.connection = connection
        self.table_name = table_name
        self.current_page = 1
        self.page_size = 50
        self.total_rows = 0
        self.columns = []
        self.setWindowTitle(f"Таблица: {table_name}")
        self.setModal(True)
        self.setGeometry(150, 150, 1200, 800)
        self.init_ui()
        self.load_table_info()
        self.load_data()
    
    def init_ui(self):
        """Инициализирует интерфейс."""
        layout = QVBoxLayout()
        
        # Пагинация
        pagination_layout = QHBoxLayout()
        self.page_label = QLabel("Страница: 1")
        self.prev_button = QPushButton("◄ Предыдущая")
        self.prev_button.clicked.connect(self.on_prev_page)
        self.next_button = QPushButton("Следующая ►")
        self.next_button.clicked.connect(self.on_next_page)
        
        page_size_layout = QHBoxLayout()
        page_size_layout.addWidget(QLabel("Записей на странице:"))
        self.page_size_spin = QSpinBox()
        self.page_size_spin.setMinimum(10)
        self.page_size_spin.setMaximum(500)
        self.page_size_spin.setValue(self.page_size)
        self.page_size_spin.valueChanged.connect(self.on_page_size_changed)
        page_size_layout.addWidget(self.page_size_spin)
        
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.prev_button)
        pagination_layout.addWidget(self.next_button)
        pagination_layout.addStretch()
        pagination_layout.addLayout(page_size_layout)
        layout.addLayout(pagination_layout)
        
        # Таблица данных
        self.data_table = QTableWidget()
        self.data_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.data_table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.SelectedClicked)
        self.data_table.itemChanged.connect(self.on_item_changed)
        layout.addWidget(self.data_table)
        
        # Кнопки CRUD
        crud_layout = QHBoxLayout()
        self.create_button = QPushButton("Создать")
        self.create_button.clicked.connect(self.on_create)
        self.refresh_button = QPushButton("Обновить")
        self.refresh_button.clicked.connect(self.load_data)
        self.delete_button = QPushButton("Удалить")
        self.delete_button.clicked.connect(self.on_delete)
        crud_layout.addWidget(self.create_button)
        crud_layout.addWidget(self.refresh_button)
        crud_layout.addWidget(self.delete_button)
        crud_layout.addStretch()
        
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.accept)
        crud_layout.addWidget(close_button)
        layout.addLayout(crud_layout)
        
        self.setLayout(layout)
    
    def load_table_info(self):
        """Загружает информацию о структуре таблицы."""
        if not self.connection:
            return
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"PRAGMA table_info({self.table_name})")
            self.columns = [dict(row) for row in cursor.fetchall()]
            
            # Подсчитываем общее количество строк
            cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            self.total_rows = cursor.fetchone()[0]
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить информацию о таблице: {str(e)}")
    
    def load_data(self):
        """Загружает данные таблицы с пагинацией."""
        if not self.connection:
            return
        
        try:
            cursor = self.connection.cursor()
            
            # Получаем данные с пагинацией
            offset = (self.current_page - 1) * self.page_size
            cursor.execute(f"SELECT * FROM {self.table_name} LIMIT ? OFFSET ?", (self.page_size, offset))
            rows = cursor.fetchall()
            
            # Настраиваем таблицу
            column_names = [col['name'] for col in self.columns]
            self.data_table.setColumnCount(len(column_names))
            self.data_table.setHorizontalHeaderLabels(column_names)
            self.data_table.setRowCount(len(rows))
            
            # Заполняем данные
            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    item = QTableWidgetItem(str(value) if value is not None else "")
                    # Сохраняем оригинальное значение для отслеживания изменений
                    item.setData(Qt.UserRole, value)
                    self.data_table.setItem(i, j, item)
            
            # Обновляем информацию о странице
            total_pages = (self.total_rows + self.page_size - 1) // self.page_size if self.total_rows > 0 else 1
            self.page_label.setText(f"Страница: {self.current_page} из {total_pages} (Всего записей: {self.total_rows})")
            
            # Обновляем состояние кнопок
            self.prev_button.setEnabled(self.current_page > 1)
            self.next_button.setEnabled(self.current_page < total_pages)
            
            # Автоматически подгоняем ширину колонок
            self.data_table.resizeColumnsToContents()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить данные: {str(e)}")
    
    def on_prev_page(self):
        """Переход на предыдущую страницу."""
        if self.current_page > 1:
            self.current_page -= 1
            self.load_data()
    
    def on_next_page(self):
        """Переход на следующую страницу."""
        total_pages = (self.total_rows + self.page_size - 1) // self.page_size if self.total_rows > 0 else 1
        if self.current_page < total_pages:
            self.current_page += 1
            self.load_data()
    
    def on_page_size_changed(self, value):
        """Обработчик изменения размера страницы."""
        self.page_size = value
        self.current_page = 1
        self.load_data()
    
    def on_item_changed(self, item):
        """Обработчик изменения ячейки таблицы."""
        # Здесь можно добавить логику для автоматического сохранения изменений
        pass
    
    def on_create(self):
        """Создает новую запись."""
        dialog = CreateEditDialog(self, self.columns, self.table_name)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                cursor = self.connection.cursor()
                # Формируем SQL запрос для вставки
                column_names = [col['name'] for col in self.columns if col['name'] in data]
                placeholders = ', '.join(['?' for _ in column_names])
                values = [data[col] for col in column_names]
                
                sql = f"INSERT INTO {self.table_name} ({', '.join(column_names)}) VALUES ({placeholders})"
                cursor.execute(sql, values)
                self.connection.commit()
                
                # Обновляем количество строк и перезагружаем данные
                cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
                self.total_rows = cursor.fetchone()[0]
                self.load_data()
                
                QMessageBox.information(self, "Успех", "Запись создана")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось создать запись: {str(e)}")
                self.connection.rollback()
    
    def on_delete(self):
        """Удаляет выбранную запись."""
        current_row = self.data_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Предупреждение", "Выберите строку для удаления")
            return
        
        reply = QMessageBox.question(self, "Подтверждение", "Удалить выбранную запись?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                cursor = self.connection.cursor()
                
                # Получаем значения первичного ключа или всех колонок для идентификации строки
                primary_key_col = None
                for col in self.columns:
                    if col.get('pk', 0) == 1:
                        primary_key_col = col['name']
                        break
                
                if primary_key_col:
                    # Используем первичный ключ
                    pk_value = self.data_table.item(current_row, 
                                                    [col['name'] for col in self.columns].index(primary_key_col)).text()
                    cursor.execute(f"DELETE FROM {self.table_name} WHERE {primary_key_col} = ?", (pk_value,))
                else:
                    # Если нет первичного ключа, используем все значения
                    values = []
                    conditions = []
                    for j, col in enumerate(self.columns):
                        item = self.data_table.item(current_row, j)
                        if item:
                            value = item.text()
                            conditions.append(f"{col['name']} = ?")
                            values.append(value)
                    if conditions:
                        sql = f"DELETE FROM {self.table_name} WHERE {' AND '.join(conditions)}"
                        cursor.execute(sql, values)
                    else:
                        QMessageBox.warning(self, "Ошибка", "Не удалось определить запись для удаления")
                        return
                
                self.connection.commit()
                
                # Обновляем количество строк и перезагружаем данные
                cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
                self.total_rows = cursor.fetchone()[0]
                self.load_data()
                
                QMessageBox.information(self, "Успех", "Запись удалена")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить запись: {str(e)}")
                self.connection.rollback()


class CreateEditDialog(QDialog):
    """Диалог для создания новой записи."""
    
    def __init__(self, parent=None, columns: List[Dict[str, Any]] = None, table_name: str = ""):
        super().__init__(parent)
        self.columns = columns or []
        self.table_name = table_name
        self.setWindowTitle(f"Создать запись в таблице {table_name}")
        self.setModal(True)
        self.init_ui()
    
    def init_ui(self):
        """Инициализирует интерфейс."""
        layout = QFormLayout()
        
        self.fields = {}
        
        for col in self.columns:
            col_name = col['name']
            col_type = col.get('type', '').upper()
            
            # Пропускаем AUTOINCREMENT поля
            if 'AUTOINCREMENT' in col_type or col.get('pk', 0) == 1 and 'INTEGER' in col_type:
                continue
            
            if 'TEXT' in col_type or 'VARCHAR' in col_type or 'CHAR' in col_type:
                field = QLineEdit()
            elif 'INTEGER' in col_type or 'INT' in col_type:
                field = QSpinBox()
                field.setMinimum(-2147483648)
                field.setMaximum(2147483647)
            elif 'REAL' in col_type or 'FLOAT' in col_type or 'DOUBLE' in col_type:
                from PyQt5.QtWidgets import QDoubleSpinBox
                field = QDoubleSpinBox()
            elif 'BLOB' in col_type:
                field = QTextEdit()
                field.setMaximumHeight(100)
            else:
                field = QLineEdit()
            
            self.fields[col_name] = field
            layout.addRow(f"{col_name} ({col_type}):", field)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
        self.setLayout(layout)
    
    def get_data(self) -> Dict[str, Any]:
        """Возвращает данные из формы."""
        data = {}
        for col_name, field in self.fields.items():
            if isinstance(field, QLineEdit):
                value = field.text()
            elif isinstance(field, QSpinBox):
                value = field.value()
            elif isinstance(field, QTextEdit):
                value = field.toPlainText()
            else:
                from PyQt5.QtWidgets import QDoubleSpinBox
                if isinstance(field, QDoubleSpinBox):
                    value = field.value()
                else:
                    value = field.text()
            
            # Пустые строки преобразуем в None для NULL значений
            if value == "":
                value = None
            
            data[col_name] = value
        return data


def main():
    app = QApplication(sys.argv)
    window = DatabaseViewer()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
