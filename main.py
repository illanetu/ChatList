"""
Основной модуль приложения ChatList.
Графический интерфейс на PyQt5 для сравнения ответов различных нейросетей.
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QLabel, QComboBox, QCheckBox, QMessageBox, QDialog, QDialogButtonBox,
    QFormLayout, QGroupBox, QSplitter, QProgressBar, QTabWidget, QFileDialog,
    QSpinBox, QDoubleSpinBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
import db
import models
import export
import logger
from typing import List, Dict, Any, Optional
import os


class RequestThread(QThread):
    """Поток для асинхронной отправки запросов к API."""
    
    finished = pyqtSignal(list)  # Сигнал с результатами
    
    def __init__(self, prompt: str, model_list: List[models.Model]):
        super().__init__()
        self.prompt = prompt
        self.model_list = model_list
    
    def run(self):
        """Выполняет отправку запросов в отдельном потоке."""
        results = models.send_to_models(self.prompt, self.model_list)
        self.finished.emit(results)


class ModelDialog(QDialog):
    """Диалог для добавления/редактирования модели."""
    
    def __init__(self, parent=None, model_data: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.model_data = model_data
        self.setWindowTitle("Добавить модель" if model_data is None else "Редактировать модель")
        self.setModal(True)
        self.init_ui()
        
        if model_data:
            self.load_model_data()
    
    def init_ui(self):
        layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.api_url_edit = QLineEdit()
        self.api_id_edit = QLineEdit()
        self.is_active_checkbox = QCheckBox("Активна")
        self.is_active_checkbox.setChecked(True)
        
        layout.addRow("Название:", self.name_edit)
        layout.addRow("API URL:", self.api_url_edit)
        layout.addRow("API ID (переменная .env):", self.api_id_edit)
        layout.addRow("", self.is_active_checkbox)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
        self.setLayout(layout)
    
    def load_model_data(self):
        """Загружает данные модели в форму."""
        if self.model_data:
            self.name_edit.setText(self.model_data.get('name', ''))
            self.api_url_edit.setText(self.model_data.get('api_url', ''))
            self.api_id_edit.setText(self.model_data.get('api_id', ''))
            self.is_active_checkbox.setChecked(self.model_data.get('is_active', 1) == 1)
    
    def get_data(self) -> Dict[str, Any]:
        """Возвращает данные из формы."""
        return {
            'name': self.name_edit.text(),
            'api_url': self.api_url_edit.text(),
            'api_id': self.api_id_edit.text(),
            'is_active': 1 if self.is_active_checkbox.isChecked() else 0
        }


class MainWindow(QMainWindow):
    """Главное окно приложения."""
    
    def __init__(self):
        super().__init__()
        self.temporary_results = []  # Временная таблица результатов в памяти
        self.current_prompt_id = None
        # Инициализируем логгер
        logger.setup_logger()
        self.init_ui()
        self.init_database()
        self.load_settings()
        self.load_prompts()
        self.load_saved_results()
    
    def init_ui(self):
        """Инициализирует интерфейс."""
        self.setWindowTitle("ChatList - Сравнение ответов нейросетей")
        self.setGeometry(100, 100, 1200, 800)
        
        # Создаем меню
        self.create_menu()
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Создаем вкладки
        tabs = QTabWidget()
        main_layout.addWidget(tabs)
        
        # Вкладка 1: Основная работа
        main_tab = QWidget()
        tabs.addTab(main_tab, "Запросы")
        main_tab_layout = QVBoxLayout()
        main_tab.setLayout(main_tab_layout)
        
        # Разделитель для основной вкладки
        splitter = QSplitter(Qt.Horizontal)
        main_tab_layout.addWidget(splitter)
        
        # Левая панель: ввод промта и список промтов
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        
        # Область ввода промта
        prompt_group = QGroupBox("Ввод промта")
        prompt_layout = QVBoxLayout()
        
        self.prompt_combo = QComboBox()
        self.prompt_combo.setEditable(True)
        self.prompt_combo.setInsertPolicy(QComboBox.NoInsert)
        self.prompt_combo.currentTextChanged.connect(self.on_prompt_selected)
        prompt_layout.addWidget(QLabel("Выберите или введите промт:"))
        prompt_layout.addWidget(self.prompt_combo)
        
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Введите ваш запрос здесь...")
        self.prompt_edit.setMaximumHeight(100)
        prompt_layout.addWidget(self.prompt_edit)
        
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("Теги (через запятую)")
        prompt_layout.addWidget(self.tags_edit)
        
        buttons_layout = QHBoxLayout()
        self.send_button = QPushButton("Отправить запрос")
        self.send_button.clicked.connect(self.on_send_request)
        self.save_prompt_button = QPushButton("Сохранить промт")
        self.save_prompt_button.clicked.connect(self.on_save_prompt)
        buttons_layout.addWidget(self.send_button)
        buttons_layout.addWidget(self.save_prompt_button)
        prompt_layout.addLayout(buttons_layout)
        
        prompt_group.setLayout(prompt_layout)
        left_layout.addWidget(prompt_group)
        
        # Список промтов
        prompts_group = QGroupBox("Сохраненные промты")
        prompts_layout = QVBoxLayout()
        
        search_layout = QHBoxLayout()
        self.prompts_search = QLineEdit()
        self.prompts_search.setPlaceholderText("Поиск промтов...")
        self.prompts_search.textChanged.connect(self.on_search_prompts)
        search_layout.addWidget(self.prompts_search)
        prompts_layout.addLayout(search_layout)
        
        self.prompts_table = QTableWidget()
        self.prompts_table.setColumnCount(3)
        self.prompts_table.setHorizontalHeaderLabels(["Дата", "Промт", "Теги"])
        self.prompts_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.prompts_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.prompts_table.setSortingEnabled(True)  # Включаем сортировку
        self.prompts_table.doubleClicked.connect(self.on_prompt_double_clicked)
        self.prompts_table.setColumnWidth(0, 150)
        self.prompts_table.setColumnWidth(1, 300)
        self.prompts_table.setColumnWidth(2, 150)
        prompts_layout.addWidget(self.prompts_table)
        
        prompts_group.setLayout(prompts_layout)
        left_layout.addWidget(prompts_group)
        
        splitter.addWidget(left_panel)
        
        # Правая панель: результаты
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)
        
        results_group = QGroupBox("Результаты")
        results_layout = QVBoxLayout()
        
        # Индикатор загрузки
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        results_layout.addWidget(self.progress_bar)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Модель", "Ответ", "Выбрано"])
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSortingEnabled(True)  # Включаем сортировку
        self.results_table.setColumnWidth(0, 150)
        self.results_table.setColumnWidth(1, 400)
        self.results_table.setColumnWidth(2, 80)
        results_layout.addWidget(self.results_table)
        
        results_buttons_layout = QHBoxLayout()
        self.save_results_button = QPushButton("Сохранить выбранные")
        self.save_results_button.clicked.connect(self.on_save_results)
        self.clear_results_button = QPushButton("Очистить результаты")
        self.clear_results_button.clicked.connect(self.on_clear_results)
        results_buttons_layout.addWidget(self.save_results_button)
        results_buttons_layout.addWidget(self.clear_results_button)
        results_layout.addLayout(results_buttons_layout)
        
        results_group.setLayout(results_layout)
        right_layout.addWidget(results_group)
        
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        # Вкладка 2: Сохраненные результаты
        results_tab = QWidget()
        tabs.addTab(results_tab, "Сохраненные результаты")
        results_tab_layout = QVBoxLayout()
        results_tab.setLayout(results_tab_layout)
        
        saved_search_layout = QHBoxLayout()
        self.saved_results_search = QLineEdit()
        self.saved_results_search.setPlaceholderText("Поиск результатов...")
        self.saved_results_search.textChanged.connect(self.on_search_saved_results)
        saved_search_layout.addWidget(self.saved_results_search)
        results_tab_layout.addLayout(saved_search_layout)
        
        self.saved_results_table = QTableWidget()
        self.saved_results_table.setColumnCount(4)
        self.saved_results_table.setHorizontalHeaderLabels(["Дата", "Промт", "Модель", "Ответ"])
        self.saved_results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.saved_results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.saved_results_table.setSortingEnabled(True)  # Включаем сортировку
        self.saved_results_table.setColumnWidth(0, 150)
        self.saved_results_table.setColumnWidth(1, 200)
        self.saved_results_table.setColumnWidth(2, 150)
        self.saved_results_table.setColumnWidth(3, 400)
        
        # Кнопка экспорта для сохраненных результатов
        export_layout = QHBoxLayout()
        export_md_button = QPushButton("Экспорт в Markdown")
        export_md_button.clicked.connect(self.on_export_markdown)
        export_json_button = QPushButton("Экспорт в JSON")
        export_json_button.clicked.connect(self.on_export_json)
        export_layout.addWidget(export_md_button)
        export_layout.addWidget(export_json_button)
        results_tab_layout.addLayout(export_layout)
        results_tab_layout.addWidget(self.saved_results_table)
    
    def create_menu(self):
        """Создает меню приложения."""
        menubar = self.menuBar()
        
        # Меню Файл
        file_menu = menubar.addMenu("Файл")
        export_md_action = file_menu.addAction("Экспорт результатов в Markdown")
        export_md_action.triggered.connect(self.on_export_markdown)
        export_json_action = file_menu.addAction("Экспорт результатов в JSON")
        export_json_action.triggered.connect(self.on_export_json)
        file_menu.addSeparator()
        exit_action = file_menu.addAction("Выход")
        exit_action.triggered.connect(self.close)
        
        # Меню Настройки
        settings_menu = menubar.addMenu("Настройки")
        models_action = settings_menu.addAction("Управление моделями")
        models_action.triggered.connect(self.on_manage_models)
        app_settings_action = settings_menu.addAction("Настройки приложения")
        app_settings_action.triggered.connect(self.on_app_settings)
        
        # Меню Помощь
        help_menu = menubar.addMenu("Помощь")
        about_action = help_menu.addAction("О программе")
        about_action.triggered.connect(self.on_about)
    
    def init_database(self):
        """Инициализирует базу данных."""
        try:
            db.init_database()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось инициализировать базу данных: {str(e)}")
    
    def load_prompts(self):
        """Загружает промты из БД и обновляет интерфейс."""
        try:
            prompts = db.get_all_prompts()
            self.prompts_table.setRowCount(len(prompts))
            
            for i, prompt_data in enumerate(prompts):
                self.prompts_table.setItem(i, 0, QTableWidgetItem(prompt_data['date']))
                self.prompts_table.setItem(i, 1, QTableWidgetItem(prompt_data['prompt']))
                self.prompts_table.setItem(i, 2, QTableWidgetItem(prompt_data.get('tags', '')))
                self.prompts_table.item(i, 0).setData(Qt.UserRole, prompt_data['id'])
            
            # Обновляем комбобокс
            self.prompt_combo.clear()
            self.prompt_combo.addItem("")
            for prompt_data in prompts:
                self.prompt_combo.addItem(prompt_data['prompt'], prompt_data['id'])
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить промты: {str(e)}")
    
    def load_saved_results(self):
        """Загружает сохраненные результаты из БД."""
        try:
            results = db.get_all_results()
            self.saved_results_table.setRowCount(len(results))
            
            for i, result in enumerate(results):
                self.saved_results_table.setItem(i, 0, QTableWidgetItem(result.get('created_at', '')))
                self.saved_results_table.setItem(i, 1, QTableWidgetItem(result.get('prompt', '')))
                self.saved_results_table.setItem(i, 2, QTableWidgetItem(result.get('model_name', '')))
                self.saved_results_table.setItem(i, 3, QTableWidgetItem(result.get('response_text', '')))
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить результаты: {str(e)}")
    
    def on_prompt_selected(self, text):
        """Обработчик выбора промта из комбобокса."""
        if text and self.prompt_combo.currentData():
            prompt_id = self.prompt_combo.currentData()
            prompt_data = db.get_prompt_by_id(prompt_id)
            if prompt_data:
                self.prompt_edit.setPlainText(prompt_data['prompt'])
                self.tags_edit.setText(prompt_data.get('tags', ''))
                self.current_prompt_id = prompt_id
                self.on_clear_results()  # Очищаем временную таблицу
    
    def on_prompt_double_clicked(self, index):
        """Обработчик двойного клика по промту в таблице."""
        row = index.row()
        prompt_id = self.prompts_table.item(row, 0).data(Qt.UserRole)
        prompt_data = db.get_prompt_by_id(prompt_id)
        if prompt_data:
            self.prompt_edit.setPlainText(prompt_data['prompt'])
            self.tags_edit.setText(prompt_data.get('tags', ''))
            self.current_prompt_id = prompt_id
            self.on_clear_results()
    
    def on_save_prompt(self):
        """Сохраняет промт в БД."""
        prompt_text = self.prompt_edit.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, "Предупреждение", "Введите текст промта")
            return
        
        tags = self.tags_edit.text().strip()
        
        try:
            if self.current_prompt_id:
                db.update_prompt(self.current_prompt_id, prompt_text, tags)
                QMessageBox.information(self, "Успех", "Промт обновлен")
            else:
                prompt_id = db.create_prompt(prompt_text, tags)
                self.current_prompt_id = prompt_id
                QMessageBox.information(self, "Успех", "Промт сохранен")
            
            self.load_prompts()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить промт: {str(e)}")
    
    def on_send_request(self):
        """Отправляет запрос во все активные модели."""
        prompt_text = self.prompt_edit.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, "Предупреждение", "Введите текст промта")
            return
        
        # Сохраняем промт, если он новый
        if not self.current_prompt_id:
            tags = self.tags_edit.text().strip()
            try:
                self.current_prompt_id = db.create_prompt(prompt_text, tags)
                self.load_prompts()
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить промт: {str(e)}")
        
        # Очищаем предыдущие результаты
        self.on_clear_results()
        
        # Получаем активные модели
        try:
            model_list = models.get_active_models()
            if not model_list:
                QMessageBox.warning(self, "Предупреждение", "Нет активных моделей. Добавьте модели в настройках.")
                return
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить модели: {str(e)}")
            return
        
        # Показываем индикатор загрузки
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Неопределенный прогресс
        self.send_button.setEnabled(False)
        
        # Запускаем запросы в отдельном потоке
        self.request_thread = RequestThread(prompt_text, model_list)
        self.request_thread.finished.connect(self.on_request_finished)
        self.request_thread.start()
    
    def on_request_finished(self, results: List[Dict[str, Any]]):
        """Обработчик завершения запросов."""
        self.progress_bar.setVisible(False)
        self.send_button.setEnabled(True)
        
        # Сохраняем результаты во временную таблицу
        self.temporary_results = results
        
        # Логируем результаты
        prompt_text = self.prompt_edit.toPlainText()
        for result in results:
            success = not result.get('error')
            logger.log_request(
                prompt_text,
                result['model_name'],
                success,
                result.get('response_text'),
                result.get('error')
            )
        
        # Отображаем результаты
        self.results_table.setRowCount(len(results))
        
        for i, result in enumerate(results):
            # Модель
            self.results_table.setItem(i, 0, QTableWidgetItem(result['model_name']))
            
            # Ответ
            response_text = result['response_text']
            if result.get('error'):
                response_text = f"Ошибка: {result['error']}"
            self.results_table.setItem(i, 1, QTableWidgetItem(response_text))
            
            # Чекбокс
            checkbox = QCheckBox()
            checkbox.setChecked(False)
            self.results_table.setCellWidget(i, 2, checkbox)
    
    def on_save_results(self):
        """Сохраняет выбранные результаты в БД."""
        if not self.current_prompt_id:
            QMessageBox.warning(self, "Предупреждение", "Сначала создайте или выберите промт")
            return
        
        selected_results = []
        
        for i in range(self.results_table.rowCount()):
            checkbox = self.results_table.cellWidget(i, 2)
            if checkbox and checkbox.isChecked():
                result = self.temporary_results[i]
                if not result.get('error'):
                    selected_results.append({
                        'prompt_id': self.current_prompt_id,
                        'model_id': result['model_id'],
                        'response_text': result['response_text']
                    })
        
        if not selected_results:
            QMessageBox.warning(self, "Предупреждение", "Выберите результаты для сохранения")
            return
        
        try:
            count = db.save_results(selected_results)
            QMessageBox.information(self, "Успех", f"Сохранено результатов: {count}")
            self.load_saved_results()
            self.on_clear_results()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить результаты: {str(e)}")
    
    def on_clear_results(self):
        """Очищает временную таблицу результатов."""
        self.results_table.setRowCount(0)
        self.temporary_results = []
    
    def on_search_prompts(self, text):
        """Поиск промтов."""
        if not text:
            self.load_prompts()
            return
        
        try:
            prompts = db.search_prompts(text)
            self.prompts_table.setRowCount(len(prompts))
            
            for i, prompt_data in enumerate(prompts):
                self.prompts_table.setItem(i, 0, QTableWidgetItem(prompt_data['date']))
                self.prompts_table.setItem(i, 1, QTableWidgetItem(prompt_data['prompt']))
                self.prompts_table.setItem(i, 2, QTableWidgetItem(prompt_data.get('tags', '')))
                self.prompts_table.item(i, 0).setData(Qt.UserRole, prompt_data['id'])
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка поиска: {str(e)}")
    
    def on_search_saved_results(self, text):
        """Поиск сохраненных результатов."""
        if not text:
            self.load_saved_results()
            return
        
        try:
            results = db.search_results(text)
            self.saved_results_table.setRowCount(len(results))
            
            for i, result in enumerate(results):
                self.saved_results_table.setItem(i, 0, QTableWidgetItem(result.get('created_at', '')))
                self.saved_results_table.setItem(i, 1, QTableWidgetItem(result.get('prompt', '')))
                self.saved_results_table.setItem(i, 2, QTableWidgetItem(result.get('model_name', '')))
                self.saved_results_table.setItem(i, 3, QTableWidgetItem(result.get('response_text', '')))
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка поиска: {str(e)}")
    
    def on_manage_models(self):
        """Открывает диалог управления моделями."""
        dialog = ModelManagementDialog(self)
        dialog.exec_()
    
    def load_settings(self):
        """Загружает настройки из БД."""
        try:
            timeout = db.get_setting('timeout', '30')
            self.timeout = int(timeout)
        except:
            self.timeout = 30
    
    def on_export_markdown(self):
        """Экспортирует результаты в Markdown."""
        # Получаем выбранные результаты или все сохраненные
        results = []
        prompt = ""
        
        # Если есть выбранные результаты во временной таблице
        if self.temporary_results:
            for i in range(self.results_table.rowCount()):
                checkbox = self.results_table.cellWidget(i, 2)
                if checkbox and checkbox.isChecked():
                    results.append(self.temporary_results[i])
            prompt = self.prompt_edit.toPlainText()
        else:
            # Экспортируем все сохраненные результаты
            saved_results = db.get_all_results()
            for result in saved_results:
                results.append({
                    'model_name': result.get('model_name', ''),
                    'response_text': result.get('response_text', ''),
                    'created_at': result.get('created_at', '')
                })
        
        if not results:
            QMessageBox.warning(self, "Предупреждение", "Нет результатов для экспорта")
            return
        
        # Выбираем файл для сохранения
        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить как Markdown", "", "Markdown Files (*.md);;All Files (*)"
        )
        
        if filename:
            try:
                md_content = export.export_to_markdown(results, prompt)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                QMessageBox.information(self, "Успех", f"Результаты экспортированы в {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать: {str(e)}")
    
    def on_export_json(self):
        """Экспортирует результаты в JSON."""
        # Получаем выбранные результаты или все сохраненные
        results = []
        prompt = ""
        
        # Если есть выбранные результаты во временной таблице
        if self.temporary_results:
            for i in range(self.results_table.rowCount()):
                checkbox = self.results_table.cellWidget(i, 2)
                if checkbox and checkbox.isChecked():
                    results.append(self.temporary_results[i])
            prompt = self.prompt_edit.toPlainText()
        else:
            # Экспортируем все сохраненные результаты
            saved_results = db.get_all_results()
            for result in saved_results:
                results.append({
                    'model_name': result.get('model_name', ''),
                    'response_text': result.get('response_text', ''),
                    'created_at': result.get('created_at', '')
                })
        
        if not results:
            QMessageBox.warning(self, "Предупреждение", "Нет результатов для экспорта")
            return
        
        # Выбираем файл для сохранения
        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить как JSON", "", "JSON Files (*.json);;All Files (*)"
        )
        
        if filename:
            try:
                json_content = export.export_to_json(results, prompt)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(json_content)
                QMessageBox.information(self, "Успех", f"Результаты экспортированы в {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать: {str(e)}")
    
    def on_app_settings(self):
        """Открывает окно настроек приложения."""
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            settings = dialog.get_settings()
            try:
                for key, value in settings.items():
                    db.set_setting(key, str(value))
                self.load_settings()
                QMessageBox.information(self, "Успех", "Настройки сохранены")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить настройки: {str(e)}")
    
    def on_about(self):
        """Показывает информацию о программе."""
        QMessageBox.about(self, "О программе", 
                         "ChatList v1.0\n\n"
                         "Приложение для сравнения ответов различных нейросетей.\n"
                         "Отправляйте один промт в несколько моделей и сравнивайте результаты.")


class SettingsDialog(QDialog):
    """Диалог настроек приложения."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки приложения")
        self.setModal(True)
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        layout = QFormLayout()
        
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setMinimum(5)
        self.timeout_spin.setMaximum(300)
        self.timeout_spin.setSuffix(" секунд")
        layout.addRow("Таймаут запросов:", self.timeout_spin)
        
        self.max_retries_spin = QSpinBox()
        self.max_retries_spin.setMinimum(1)
        self.max_retries_spin.setMaximum(10)
        layout.addRow("Максимум повторных попыток:", self.max_retries_spin)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
        self.setLayout(layout)
    
    def load_settings(self):
        """Загружает текущие настройки."""
        try:
            timeout = int(db.get_setting('timeout', '30'))
            self.timeout_spin.setValue(timeout)
        except:
            self.timeout_spin.setValue(30)
        
        try:
            max_retries = int(db.get_setting('max_retries', '3'))
            self.max_retries_spin.setValue(max_retries)
        except:
            self.max_retries_spin.setValue(3)
    
    def get_settings(self) -> Dict[str, Any]:
        """Возвращает настройки из формы."""
        return {
            'timeout': self.timeout_spin.value(),
            'max_retries': self.max_retries_spin.value()
        }


class ModelManagementDialog(QDialog):
    """Диалог для управления моделями."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управление моделями")
        self.setModal(True)
        self.setGeometry(200, 200, 800, 600)
        self.init_ui()
        self.load_models()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        add_button = QPushButton("Добавить")
        add_button.clicked.connect(self.on_add_model)
        edit_button = QPushButton("Редактировать")
        edit_button.clicked.connect(self.on_edit_model)
        delete_button = QPushButton("Удалить")
        delete_button.clicked.connect(self.on_delete_model)
        toggle_button = QPushButton("Включить/Выключить")
        toggle_button.clicked.connect(self.on_toggle_model)
        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(edit_button)
        buttons_layout.addWidget(delete_button)
        buttons_layout.addWidget(toggle_button)
        layout.addLayout(buttons_layout)
        
        # Таблица моделей
        self.models_table = QTableWidget()
        self.models_table.setColumnCount(4)
        self.models_table.setHorizontalHeaderLabels(["Название", "API URL", "API ID", "Активна"])
        self.models_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.models_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.models_table.setColumnWidth(0, 150)
        self.models_table.setColumnWidth(1, 300)
        self.models_table.setColumnWidth(2, 150)
        self.models_table.setColumnWidth(3, 80)
        layout.addWidget(self.models_table)
        
        # Кнопки закрытия
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
        
        self.setLayout(layout)
    
    def load_models(self):
        """Загружает модели из БД."""
        try:
            models_list = db.get_all_models()
            self.models_table.setRowCount(len(models_list))
            
            for i, model_data in enumerate(models_list):
                self.models_table.setItem(i, 0, QTableWidgetItem(model_data['name']))
                self.models_table.setItem(i, 1, QTableWidgetItem(model_data['api_url']))
                self.models_table.setItem(i, 2, QTableWidgetItem(model_data['api_id']))
                
                is_active = "Да" if model_data['is_active'] == 1 else "Нет"
                self.models_table.setItem(i, 3, QTableWidgetItem(is_active))
                self.models_table.item(i, 0).setData(Qt.UserRole, model_data['id'])
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить модели: {str(e)}")
    
    def get_selected_model_id(self) -> Optional[int]:
        """Возвращает ID выбранной модели."""
        current_row = self.models_table.currentRow()
        if current_row >= 0:
            return self.models_table.item(current_row, 0).data(Qt.UserRole)
        return None
    
    def on_add_model(self):
        """Добавляет новую модель."""
        dialog = ModelDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                db.create_model(data['name'], data['api_url'], data['api_id'], data['is_active'])
                self.load_models()
                QMessageBox.information(self, "Успех", "Модель добавлена")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось добавить модель: {str(e)}")
    
    def on_edit_model(self):
        """Редактирует выбранную модель."""
        model_id = self.get_selected_model_id()
        if not model_id:
            QMessageBox.warning(self, "Предупреждение", "Выберите модель для редактирования")
            return
        
        try:
            models_list = db.get_all_models()
            model_data = next((m for m in models_list if m['id'] == model_id), None)
            if not model_data:
                return
            
            dialog = ModelDialog(self, model_data)
            if dialog.exec_() == QDialog.Accepted:
                data = dialog.get_data()
                db.update_model(model_id, **data)
                self.load_models()
                QMessageBox.information(self, "Успех", "Модель обновлена")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить модель: {str(e)}")
    
    def on_delete_model(self):
        """Удаляет выбранную модель."""
        model_id = self.get_selected_model_id()
        if not model_id:
            QMessageBox.warning(self, "Предупреждение", "Выберите модель для удаления")
            return
        
        reply = QMessageBox.question(self, "Подтверждение", "Удалить выбранную модель?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                db.delete_model(model_id)
                self.load_models()
                QMessageBox.information(self, "Успех", "Модель удалена")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить модель: {str(e)}")
    
    def on_toggle_model(self):
        """Переключает активность модели."""
        model_id = self.get_selected_model_id()
        if not model_id:
            QMessageBox.warning(self, "Предупреждение", "Выберите модель")
            return
        
        try:
            models_list = db.get_all_models()
            model_data = next((m for m in models_list if m['id'] == model_id), None)
            if model_data:
                new_status = 0 if model_data['is_active'] == 1 else 1
                db.toggle_model_active(model_id, new_status)
                self.load_models()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось изменить статус модели: {str(e)}")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
