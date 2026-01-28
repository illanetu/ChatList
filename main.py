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
    QSpinBox, QDoubleSpinBox, QRadioButton, QButtonGroup
)
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtCore import Qt, QThread, pyqtSignal, PYQT_VERSION_STR
from PyQt5.QtGui import QFont, QIcon
import db
import models
import export
import logger
import prompt_improver
import version
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


class ImprovementThread(QThread):
    """Поток для асинхронного улучшения промта."""
    
    finished = pyqtSignal(dict)  # Сигнал с результатами улучшения
    
    def __init__(self, prompt: str, model_data: Optional[Dict[str, Any]], improvement_type: str):
        super().__init__()
        self.prompt = prompt
        self.model_data = model_data
        self.improvement_type = improvement_type
    
    def run(self):
        """Выполняет улучшение промта в отдельном потоке."""
        result = prompt_improver.improve_prompt(self.prompt, self.model_data, self.improvement_type)
        self.finished.emit(result)


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
        logger.log_startup(version.__version__)
        self.init_ui()
        self.init_database()
        self.load_settings()
        self.load_prompts()
        self.load_saved_results()
    
    def init_ui(self):
        """Инициализирует интерфейс."""
        self.setWindowTitle(f"ChatList {version.__version__} - Сравнение ответов нейросетей")
        self.setGeometry(100, 100, 1200, 800)
        
        # Устанавливаем иконку окна
        icon_path = os.path.join(os.path.dirname(__file__), "app.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
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
        
        # Область ввода промта (сверху)
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
        self.improve_prompt_button = QPushButton("Улучшить промт")
        self.improve_prompt_button.clicked.connect(self.on_improve_prompt)
        self.save_prompt_button = QPushButton("Сохранить промт")
        self.save_prompt_button.clicked.connect(self.on_save_prompt)
        buttons_layout.addWidget(self.send_button)
        buttons_layout.addWidget(self.improve_prompt_button)
        buttons_layout.addWidget(self.save_prompt_button)
        prompt_layout.addLayout(buttons_layout)
        
        prompt_group.setLayout(prompt_layout)
        main_tab_layout.addWidget(prompt_group)
        
        # Таблица результатов (снизу)
        results_group = QGroupBox("Результаты")
        results_layout = QVBoxLayout()
        
        # Индикатор загрузки
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        results_layout.addWidget(self.progress_bar)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Выбрано", "Модель", "Ответ"])
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSortingEnabled(True)  # Включаем сортировку
        self.results_table.setColumnWidth(0, 80)  # Выбрано
        self.results_table.setColumnWidth(1, 150)  # Модель
        # Настраиваем растягивание колонки "Ответ" при изменении размера окна
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)  # Выбрано - фиксированная
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)  # Модель - фиксированная
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)  # Ответ - растягивается
        # Настраиваем высоту строк для многострочного отображения
        self.results_table.verticalHeader().setDefaultSectionSize(100)  # Минимальная высота строки
        self.results_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)  # Автоматическая высота
        results_layout.addWidget(self.results_table)
        
        results_buttons_layout = QHBoxLayout()
        self.save_results_button = QPushButton("Сохранить выбранные")
        self.save_results_button.clicked.connect(self.on_save_results)
        self.open_result_button = QPushButton("Открыть")
        self.open_result_button.clicked.connect(self.on_open_result)
        self.clear_results_button = QPushButton("Очистить результаты")
        self.clear_results_button.clicked.connect(self.on_clear_results)
        results_buttons_layout.addWidget(self.save_results_button)
        results_buttons_layout.addWidget(self.open_result_button)
        results_buttons_layout.addWidget(self.clear_results_button)
        results_layout.addLayout(results_buttons_layout)
        
        results_group.setLayout(results_layout)
        main_tab_layout.addWidget(results_group, stretch=1)  # Растягиваем таблицу результатов
        
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
        self.saved_results_table.setColumnWidth(3, 500)  # Увеличена ширина для ответов
        # Настраиваем высоту строк для многострочного отображения
        self.saved_results_table.verticalHeader().setDefaultSectionSize(100)  # Минимальная высота строки
        self.saved_results_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)  # Автоматическая высота
        
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
        
        # Меню Промты
        prompts_menu = menubar.addMenu("Промты")
        manage_prompts_action = prompts_menu.addAction("Управление промтами")
        manage_prompts_action.triggered.connect(self.on_manage_prompts)
        
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
        """Загружает промты из БД и обновляет комбобокс."""
        try:
            prompts = db.get_all_prompts()
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
                # Ответ - используем QTextEdit для многострочного отображения
                response_text = result.get('response_text', '')
                text_edit = QTextEdit()
                text_edit.setPlainText(response_text)
                text_edit.setReadOnly(True)
                text_edit.setFrameShape(QTextEdit.NoFrame)  # Убираем рамку
                text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                text_edit.setMinimumHeight(80)
                text_edit.setMaximumHeight(300)
                self.saved_results_table.setCellWidget(i, 3, text_edit)
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
            # Чекбокс (колонка 0)
            checkbox = QCheckBox()
            checkbox.setChecked(False)
            self.results_table.setCellWidget(i, 0, checkbox)
            
            # Модель (колонка 1)
            self.results_table.setItem(i, 1, QTableWidgetItem(result['model_name']))
            
            # Ответ - используем QTextEdit для многострочного отображения (колонка 2)
            response_text = result['response_text']
            if result.get('error'):
                response_text = f"Ошибка: {result['error']}"
            
            # Создаем QTextEdit для ячейки с ответом
            text_edit = QTextEdit()
            text_edit.setPlainText(response_text)
            text_edit.setReadOnly(True)
            text_edit.setFrameShape(QTextEdit.NoFrame)  # Убираем рамку
            text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # Скроллбар при необходимости
            text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            # Устанавливаем минимальную высоту
            text_edit.setMinimumHeight(80)
            text_edit.setMaximumHeight(300)  # Максимальная высота для предотвращения слишком больших ячеек
            self.results_table.setCellWidget(i, 2, text_edit)
    
    def on_save_results(self):
        """Сохраняет выбранные результаты в БД."""
        if not self.current_prompt_id:
            QMessageBox.warning(self, "Предупреждение", "Сначала создайте или выберите промт")
            return
        
        selected_results = []
        
        for i in range(self.results_table.rowCount()):
            checkbox = self.results_table.cellWidget(i, 0)  # Чекбокс теперь в колонке 0
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
    
    def on_open_result(self):
        """Открывает детальное окно с информацией о выбранном результате."""
        current_row = self.results_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Предупреждение", "Выберите строку с результатом для просмотра")
            return
        
        if current_row >= len(self.temporary_results):
            return
        
        result = self.temporary_results[current_row]
        
        # Получаем промт
        prompt_text = self.prompt_edit.toPlainText()
        if self.current_prompt_id:
            prompt_data = db.get_prompt_by_id(self.current_prompt_id)
            if prompt_data:
                prompt_text = prompt_data['prompt']
        
        # Открываем диалог с детальной информацией
        dialog = ResultDetailDialog(self, result, prompt_text)
        dialog.exec_()
    
    def on_improve_prompt(self):
        """Открывает диалог для улучшения промта."""
        prompt_text = self.prompt_edit.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, "Предупреждение", "Введите промт для улучшения")
            return
        
        # Получаем модель для улучшения из настроек
        model_id = db.get_prompt_improver_model()
        model_data = None
        
        if model_id:
            try:
                models_list = db.get_all_models()
                model_dict = next((m for m in models_list if m['id'] == model_id), None)
                if model_dict:
                    model_data = {
                        'name': model_dict['name'],
                        'api_url': model_dict['api_url'],
                        'api_id': model_dict['api_id']
                    }
            except:
                pass
        
        # Если модель не выбрана, используем первую активную
        if not model_data:
            try:
                active_models = models.get_active_models()
                if active_models:
                    model = active_models[0]
                    model_data = {
                        'name': model.name,
                        'api_url': model.api_url,
                        'api_id': model.api_id
                    }
            except:
                pass
        
        if not model_data:
            QMessageBox.warning(self, "Предупреждение", "Нет доступных моделей для улучшения промта")
            return
        
        # Открываем диалог улучшения
        dialog = PromptImprovementDialog(self, prompt_text, model_data)
        if dialog.exec_() == QDialog.Accepted:
            selected_prompt = dialog.get_selected_prompt()
            if selected_prompt:
                self.prompt_edit.setPlainText(selected_prompt)
    
    def on_clear_results(self):
        """Очищает временную таблицу результатов."""
        self.results_table.setRowCount(0)
        self.temporary_results = []
    
    def on_manage_prompts(self):
        """Открывает диалог управления промтами."""
        dialog = PromptsManagementDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_prompts()  # Обновляем комбобокс после изменений
    
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
                # Ответ - используем QTextEdit для многострочного отображения
                response_text = result.get('response_text', '')
                text_edit = QTextEdit()
                text_edit.setPlainText(response_text)
                text_edit.setReadOnly(True)
                text_edit.setFrameShape(QTextEdit.NoFrame)  # Убираем рамку
                text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                text_edit.setMinimumHeight(80)
                text_edit.setMaximumHeight(300)
                self.saved_results_table.setCellWidget(i, 3, text_edit)
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
        
        # Применяем тему и размер шрифта
        theme = db.get_theme()
        self.apply_theme(theme)
        
        font_size = db.get_font_size()
        self.set_font_size(font_size)
    
    def apply_theme(self, theme_name: str):
        """Применяет тему ко всему приложению."""
        if theme_name == 'dark':
            # Темная тема
            dark_style = """
                QMainWindow, QWidget {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QTextEdit, QLineEdit, QComboBox {
                    background-color: #3c3c3c;
                    color: #ffffff;
                    border: 1px solid #555555;
                }
                QPushButton {
                    background-color: #404040;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #505050;
                }
                QPushButton:pressed {
                    background-color: #353535;
                }
                QTableWidget {
                    background-color: #3c3c3c;
                    color: #ffffff;
                    gridline-color: #555555;
                }
                QTableWidget::item {
                    background-color: #3c3c3c;
                    color: #ffffff;
                }
                QTableWidget::item:selected {
                    background-color: #505050;
                }
                QHeaderView::section {
                    background-color: #404040;
                    color: #ffffff;
                    padding: 5px;
                    border: 1px solid #555555;
                }
                QGroupBox {
                    color: #ffffff;
                    border: 1px solid #555555;
                    margin-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }
                QTabWidget::pane {
                    border: 1px solid #555555;
                    background-color: #2b2b2b;
                }
                QTabBar::tab {
                    background-color: #404040;
                    color: #ffffff;
                    padding: 5px 10px;
                    border: 1px solid #555555;
                }
                QTabBar::tab:selected {
                    background-color: #505050;
                }
                QCheckBox {
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                }
                QProgressBar {
                    border: 1px solid #555555;
                    background-color: #3c3c3c;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #505050;
                }
                QDialog {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
            """
            self.setStyleSheet(dark_style)
        else:
            # Светлая тема (по умолчанию)
            self.setStyleSheet("")
    
    def set_font_size(self, size: int):
        """Применяет размер шрифта ко всем элементам интерфейса."""
        font = QFont()
        font.setPointSize(size)
        
        # Применяем шрифт ко всем виджетам
        self.setFont(font)
        
        # Применяем к дочерним виджетам
        for widget in self.findChildren(QWidget):
            widget.setFont(font)
    
    def apply_settings(self, settings: Dict[str, Any]):
        """Применяет настройки без сохранения в БД (для кнопки "Применить")."""
        # Сохраняем настройки в БД
        for key, value in settings.items():
            if key == 'prompt_improver_model':
                db.set_prompt_improver_model(value)
            elif key == 'theme':
                db.set_theme(value)
                self.apply_theme(value)
            elif key == 'font_size':
                db.set_font_size(value)
                self.set_font_size(value)
            else:
                db.set_setting(key, str(value))
        
        # Обновляем таймаут
        if 'timeout' in settings:
            try:
                self.timeout = int(settings['timeout'])
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
                checkbox = self.results_table.cellWidget(i, 0)  # Чекбокс теперь в колонке 0
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
                checkbox = self.results_table.cellWidget(i, 0)  # Чекбокс теперь в колонке 0
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
                    if key == 'prompt_improver_model':
                        db.set_prompt_improver_model(value)
                    elif key == 'theme':
                        db.set_theme(value)
                        self.apply_theme(value)
                    elif key == 'font_size':
                        db.set_font_size(value)
                        self.set_font_size(value)
                    else:
                        db.set_setting(key, str(value))
                
                # Обновляем таймаут
                if 'timeout' in settings:
                    try:
                        self.timeout = int(settings['timeout'])
                    except:
                        self.timeout = 30
                
                QMessageBox.information(self, "Успех", "Настройки сохранены")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить настройки: {str(e)}")
    
    def on_about(self):
        """Показывает информацию о программе."""
        about_text = f"""
        <h2>ChatList {version.__version__}</h2>
        <p><b>Приложение для сравнения ответов различных нейросетей</b></p>
        <p>Отправляйте один промт в несколько моделей и сравнивайте результаты.</p>
        <hr>
        <h3>Основные возможности:</h3>
        <ul>
            <li>Отправка промтов в несколько AI-моделей одновременно</li>
            <li>Сравнение ответов в удобной таблице</li>
            <li>Сохранение промтов и результатов в базе данных</li>
            <li>Управление моделями (OpenAI, DeepSeek, Groq, OpenRouter)</li>
            <li>AI-ассистент для улучшения промтов</li>
            <li>Экспорт результатов в Markdown и JSON</li>
            <li>Настройка темы и размера шрифта</li>
        </ul>
        <hr>
        <p><b>Версия Python:</b> {sys.version.split()[0]}</p>
        <p><b>Версия PyQt5:</b> {PYQT_VERSION_STR}</p>
        <hr>
        <p>Разработано для удобного сравнения ответов различных AI-моделей.</p>
        """
        
        QMessageBox.about(self, "О программе", about_text)


class ResultDetailDialog(QDialog):
    """Диалог для детального просмотра результата."""
    
    def __init__(self, parent=None, result: Optional[Dict[str, Any]] = None, prompt: str = ""):
        super().__init__(parent)
        self.result = result
        self.prompt = prompt
        self.setWindowTitle("Детали результата")
        self.setModal(True)
        self.setGeometry(200, 200, 800, 600)
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Модель
        model_layout = QFormLayout()
        model_label = QLabel("Модель:")
        model_value = QLabel(self.result.get('model_name', 'Неизвестная модель') if self.result else '')
        model_value.setWordWrap(True)
        model_layout.addRow(model_label, model_value)
        layout.addLayout(model_layout)
        
        # Промт
        prompt_group = QGroupBox("Промт")
        prompt_layout = QVBoxLayout()
        self.prompt_text = QTextEdit()
        self.prompt_text.setReadOnly(True)
        self.prompt_text.setMaximumHeight(150)
        prompt_layout.addWidget(self.prompt_text)
        prompt_group.setLayout(prompt_layout)
        layout.addWidget(prompt_group)
        
        # Ответ
        response_group = QGroupBox("Ответ")
        response_layout = QVBoxLayout()
        self.response_text = QTextEdit()
        self.response_text.setReadOnly(True)
        # Включаем поддержку markdown
        self.response_text.setAcceptRichText(True)
        response_layout.addWidget(self.response_text)
        response_group.setLayout(response_layout)
        layout.addWidget(response_group, stretch=1)
        
        # Кнопка закрытия
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
        
        self.setLayout(layout)
    
    def load_data(self):
        """Загружает данные в диалог."""
        if self.result:
            # Загружаем промт
            self.prompt_text.setPlainText(self.prompt)
            
            # Загружаем ответ с поддержкой markdown
            response_text = self.result.get('response_text', '')
            if self.result.get('error'):
                response_text = f"Ошибка: {self.result.get('error', 'Неизвестная ошибка')}"
            
            # Отображаем текст как markdown для форматирования
            try:
                self.response_text.setMarkdown(response_text)
            except:
                # Если markdown не поддерживается или ошибка, используем обычный текст
                self.response_text.setPlainText(response_text)


class PromptImprovementDialog(QDialog):
    """Диалог для улучшения промта с помощью AI."""
    
    def __init__(self, parent=None, original_prompt: str = "", model_data: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.original_prompt = original_prompt
        self.model_data = model_data
        self.improvement_result = None
        self.selected_prompt = None
        self.setWindowTitle("Улучшение промта")
        self.setModal(True)
        self.setGeometry(200, 200, 900, 700)
        self.init_ui()
        self.load_models()
    
    def init_ui(self):
        """Инициализирует интерфейс."""
        layout = QVBoxLayout()
        
        # Выбор типа улучшения
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Тип улучшения:"))
        self.improvement_type_combo = QComboBox()
        self.improvement_type_combo.addItem("Общее улучшение", "general")
        self.improvement_type_combo.addItem("Переформулировка", "rephrase")
        self.improvement_type_combo.addItem("Адаптация под код", "code")
        self.improvement_type_combo.addItem("Адаптация под анализ", "analysis")
        self.improvement_type_combo.addItem("Адаптация под креатив", "creative")
        type_layout.addWidget(self.improvement_type_combo)
        
        # Выбор модели
        type_layout.addWidget(QLabel("Модель:"))
        self.model_combo = QComboBox()
        type_layout.addWidget(self.model_combo)
        
        # Кнопка улучшения
        self.improve_button = QPushButton("Улучшить")
        self.improve_button.clicked.connect(self.on_improve)
        type_layout.addWidget(self.improve_button)
        layout.addLayout(type_layout)
        
        # Исходный промт
        original_group = QGroupBox("Исходный промт")
        original_layout = QVBoxLayout()
        self.original_text = QTextEdit()
        self.original_text.setPlainText(self.original_prompt)
        self.original_text.setReadOnly(True)
        self.original_text.setMaximumHeight(100)
        original_layout.addWidget(self.original_text)
        original_group.setLayout(original_layout)
        layout.addWidget(original_group)
        
        # Индикатор загрузки
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Улучшенная версия
        improved_group = QGroupBox("Улучшенная версия")
        improved_layout = QVBoxLayout()
        self.improved_text = QTextEdit()
        self.improved_text.setReadOnly(True)
        self.improved_text.setMaximumHeight(150)
        improved_layout.addWidget(self.improved_text)
        
        use_improved_button = QPushButton("Подставить улучшенную версию")
        use_improved_button.clicked.connect(lambda: self.on_use_prompt(self.improved_text.toPlainText()))
        improved_layout.addWidget(use_improved_button)
        improved_group.setLayout(improved_layout)
        layout.addWidget(improved_group)
        
        # Альтернативные варианты
        alternatives_group = QGroupBox("Альтернативные варианты")
        alternatives_layout = QVBoxLayout()
        self.alternatives_widget = QWidget()
        self.alternatives_layout = QVBoxLayout()
        self.alternatives_widget.setLayout(self.alternatives_layout)
        alternatives_layout.addWidget(self.alternatives_widget)
        alternatives_group.setLayout(alternatives_layout)
        layout.addWidget(alternatives_group, stretch=1)
        
        # Кнопки закрытия
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.reject)
        buttons_layout.addWidget(close_button)
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def load_models(self):
        """Загружает список моделей для выбора."""
        try:
            models_list = db.get_all_models()
            self.model_combo.clear()
            
            # Устанавливаем выбранную модель из настроек или первую активную
            selected_model_id = db.get_prompt_improver_model()
            selected_index = 0
            
            for i, model_dict in enumerate(models_list):
                model_name = model_dict['name']
                self.model_combo.addItem(model_name, model_dict)
                if model_dict['id'] == selected_model_id:
                    selected_index = i
            
            self.model_combo.setCurrentIndex(selected_index)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить модели: {str(e)}")
    
    def on_improve(self):
        """Запускает процесс улучшения промта."""
        if not self.original_prompt.strip():
            QMessageBox.warning(self, "Предупреждение", "Промт не может быть пустым")
            return
        
        # Получаем выбранную модель
        model_dict = self.model_combo.currentData()
        if not model_dict:
            QMessageBox.warning(self, "Предупреждение", "Выберите модель для улучшения")
            return
        
        model_data = {
            'name': model_dict['name'],
            'api_url': model_dict['api_url'],
            'api_id': model_dict['api_id']
        }
        
        # Получаем тип улучшения
        improvement_type = self.improvement_type_combo.currentData()
        
        # Показываем индикатор загрузки
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.improve_button.setEnabled(False)
        
        # Очищаем предыдущие результаты
        self.improved_text.clear()
        self.clear_alternatives()
        
        # Запускаем улучшение в отдельном потоке
        self.improvement_thread = ImprovementThread(
            self.original_prompt,
            model_data,
            improvement_type
        )
        self.improvement_thread.finished.connect(self.on_improvement_finished)
        self.improvement_thread.start()
    
    def on_improvement_finished(self, result: Dict[str, Any]):
        """Обработчик завершения улучшения промта."""
        self.progress_bar.setVisible(False)
        self.improve_button.setEnabled(True)
        
        if result.get('error'):
            QMessageBox.critical(self, "Ошибка", f"Не удалось улучшить промт: {result['error']}")
            return
        
        # Отображаем улучшенную версию
        improved_text = result.get('improved', '')
        if improved_text:
            self.improved_text.setPlainText(improved_text)
        else:
            self.improved_text.setPlainText("Не удалось получить улучшенную версию")
        
        # Отображаем альтернативные варианты
        alternatives = result.get('alternatives', [])
        if alternatives:
            self.show_alternatives(alternatives)
        else:
            # Если альтернативы не найдены, но есть улучшенная версия, используем её
            if improved_text:
                QMessageBox.information(self, "Информация", 
                                       "Получена улучшенная версия, но альтернативные варианты не найдены")
    
    def show_alternatives(self, alternatives: List[str]):
        """Отображает альтернативные варианты промта."""
        self.clear_alternatives()
        
        for i, alt_text in enumerate(alternatives, 1):
            alt_group = QGroupBox(f"Вариант {i}")
            alt_layout = QVBoxLayout()
            
            alt_text_edit = QTextEdit()
            alt_text_edit.setPlainText(alt_text)
            alt_text_edit.setReadOnly(True)
            alt_text_edit.setMaximumHeight(100)
            alt_layout.addWidget(alt_text_edit)
            
            use_button = QPushButton(f"Подставить вариант {i}")
            use_button.clicked.connect(lambda checked, text=alt_text: self.on_use_prompt(text))
            alt_layout.addWidget(use_button)
            
            alt_group.setLayout(alt_layout)
            self.alternatives_layout.addWidget(alt_group)
    
    def clear_alternatives(self):
        """Очищает виджеты альтернативных вариантов."""
        while self.alternatives_layout.count():
            item = self.alternatives_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def on_use_prompt(self, prompt_text: str):
        """Обработчик кнопки подстановки промта."""
        if prompt_text.strip():
            self.selected_prompt = prompt_text
            self.accept()
    
    def get_selected_prompt(self) -> Optional[str]:
        """Возвращает выбранный промт для подстановки."""
        return self.selected_prompt


class SettingsDialog(QDialog):
    """Диалог настроек приложения."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки приложения")
        self.setModal(True)
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # Основные настройки
        settings_group = QGroupBox("Основные настройки")
        settings_layout = QFormLayout()
        
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setMinimum(5)
        self.timeout_spin.setMaximum(300)
        self.timeout_spin.setSuffix(" секунд")
        settings_layout.addRow("Таймаут запросов:", self.timeout_spin)
        
        self.max_retries_spin = QSpinBox()
        self.max_retries_spin.setMinimum(1)
        self.max_retries_spin.setMaximum(10)
        settings_layout.addRow("Максимум повторных попыток:", self.max_retries_spin)
        
        # Модель для улучшения промтов
        self.improver_model_combo = QComboBox()
        settings_layout.addRow("Модель для улучшения промтов:", self.improver_model_combo)
        
        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)
        
        # Внешний вид
        appearance_group = QGroupBox("Внешний вид")
        appearance_layout = QFormLayout()
        
        # Выбор темы
        theme_layout = QHBoxLayout()
        self.theme_group = QButtonGroup()
        self.light_theme_radio = QRadioButton("Светлая")
        self.dark_theme_radio = QRadioButton("Темная")
        self.theme_group.addButton(self.light_theme_radio, 0)
        self.theme_group.addButton(self.dark_theme_radio, 1)
        theme_layout.addWidget(self.light_theme_radio)
        theme_layout.addWidget(self.dark_theme_radio)
        theme_layout.addStretch()
        appearance_layout.addRow("Тема:", theme_layout)
        
        # Размер шрифта
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setMinimum(8)
        self.font_size_spin.setMaximum(24)
        self.font_size_spin.setSuffix(" пунктов")
        appearance_layout.addRow("Размер шрифта:", self.font_size_spin)
        
        appearance_group.setLayout(appearance_layout)
        main_layout.addWidget(appearance_group)
        
        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        apply_button = buttons.button(QDialogButtonBox.Apply)
        apply_button.clicked.connect(self.on_apply)
        main_layout.addWidget(buttons)
        
        self.setLayout(main_layout)
    
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
        
        # Загружаем список моделей для улучшения промтов
        try:
            models_list = db.get_all_models()
            self.improver_model_combo.clear()
            self.improver_model_combo.addItem("(Не выбрано)", None)
            
            selected_model_id = db.get_prompt_improver_model()
            selected_index = 0
            
            for i, model_dict in enumerate(models_list):
                model_name = model_dict['name']
                self.improver_model_combo.addItem(model_name, model_dict['id'])
                if model_dict['id'] == selected_model_id:
                    selected_index = i + 1  # +1 из-за "(Не выбрано)"
            
            self.improver_model_combo.setCurrentIndex(selected_index)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить модели: {str(e)}")
        
        # Загружаем тему
        theme = db.get_theme()
        if theme == 'dark':
            self.dark_theme_radio.setChecked(True)
        else:
            self.light_theme_radio.setChecked(True)
        
        # Загружаем размер шрифта
        font_size = db.get_font_size()
        self.font_size_spin.setValue(font_size)
    
    def on_apply(self):
        """Применяет настройки без закрытия диалога."""
        settings = self.get_settings()
        if self.parent():
            self.parent().apply_settings(settings)
    
    def get_settings(self) -> Dict[str, Any]:
        """Возвращает настройки из формы."""
        model_id = self.improver_model_combo.currentData()
        theme = 'dark' if self.dark_theme_radio.isChecked() else 'light'
        return {
            'timeout': self.timeout_spin.value(),
            'max_retries': self.max_retries_spin.value(),
            'prompt_improver_model': model_id,
            'theme': theme,
            'font_size': self.font_size_spin.value()
        }


class PromptsManagementDialog(QDialog):
    """Диалог для управления промтами."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управление промтами")
        self.setModal(True)
        self.setGeometry(200, 200, 900, 600)
        self.parent_window = parent
        self.init_ui()
        self.load_prompts()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Поиск
        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск промтов...")
        self.search_edit.textChanged.connect(self.on_search)
        search_layout.addWidget(QLabel("Поиск:"))
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        add_button = QPushButton("Добавить")
        add_button.clicked.connect(self.on_add_prompt)
        edit_button = QPushButton("Редактировать")
        edit_button.clicked.connect(self.on_edit_prompt)
        delete_button = QPushButton("Удалить")
        delete_button.clicked.connect(self.on_delete_prompt)
        use_button = QPushButton("Использовать")
        use_button.clicked.connect(self.on_use_prompt)
        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(edit_button)
        buttons_layout.addWidget(delete_button)
        buttons_layout.addWidget(use_button)
        layout.addLayout(buttons_layout)
        
        # Таблица промтов
        self.prompts_table = QTableWidget()
        self.prompts_table.setColumnCount(3)
        self.prompts_table.setHorizontalHeaderLabels(["Дата", "Промт", "Теги"])
        self.prompts_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.prompts_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.prompts_table.setSortingEnabled(True)
        self.prompts_table.doubleClicked.connect(self.on_use_prompt)
        self.prompts_table.setColumnWidth(0, 150)
        self.prompts_table.setColumnWidth(1, 400)
        self.prompts_table.setColumnWidth(2, 150)
        layout.addWidget(self.prompts_table)
        
        # Кнопка закрытия
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
        
        self.setLayout(layout)
    
    def load_prompts(self):
        """Загружает промты из БД."""
        try:
            prompts = db.get_all_prompts()
            self.prompts_table.setRowCount(len(prompts))
            
            for i, prompt_data in enumerate(prompts):
                self.prompts_table.setItem(i, 0, QTableWidgetItem(prompt_data['date']))
                self.prompts_table.setItem(i, 1, QTableWidgetItem(prompt_data['prompt']))
                self.prompts_table.setItem(i, 2, QTableWidgetItem(prompt_data.get('tags', '')))
                self.prompts_table.item(i, 0).setData(Qt.UserRole, prompt_data['id'])
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить промты: {str(e)}")
    
    def on_search(self, text):
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
    
    def get_selected_prompt_id(self) -> Optional[int]:
        """Возвращает ID выбранного промта."""
        current_row = self.prompts_table.currentRow()
        if current_row >= 0:
            return self.prompts_table.item(current_row, 0).data(Qt.UserRole)
        return None
    
    def on_add_prompt(self):
        """Добавляет новый промт."""
        dialog = PromptDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                db.create_prompt(data['prompt'], data.get('tags'))
                self.load_prompts()
                QMessageBox.information(self, "Успех", "Промт добавлен")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось добавить промт: {str(e)}")
    
    def on_edit_prompt(self):
        """Редактирует выбранный промт."""
        prompt_id = self.get_selected_prompt_id()
        if not prompt_id:
            QMessageBox.warning(self, "Предупреждение", "Выберите промт для редактирования")
            return
        
        try:
            prompt_data = db.get_prompt_by_id(prompt_id)
            if not prompt_data:
                return
            
            dialog = PromptDialog(self, prompt_data)
            if dialog.exec_() == QDialog.Accepted:
                data = dialog.get_data()
                db.update_prompt(prompt_id, data['prompt'], data.get('tags'))
                self.load_prompts()
                QMessageBox.information(self, "Успех", "Промт обновлен")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить промт: {str(e)}")
    
    def on_delete_prompt(self):
        """Удаляет выбранный промт."""
        prompt_id = self.get_selected_prompt_id()
        if not prompt_id:
            QMessageBox.warning(self, "Предупреждение", "Выберите промт для удаления")
            return
        
        reply = QMessageBox.question(self, "Подтверждение", "Удалить выбранный промт?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                db.delete_prompt(prompt_id)
                self.load_prompts()
                QMessageBox.information(self, "Успех", "Промт удален")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить промт: {str(e)}")
    
    def on_use_prompt(self):
        """Использует выбранный промт в основном окне."""
        prompt_id = self.get_selected_prompt_id()
        if not prompt_id:
            return
        
        try:
            prompt_data = db.get_prompt_by_id(prompt_id)
            if prompt_data and self.parent_window:
                self.parent_window.prompt_edit.setPlainText(prompt_data['prompt'])
                self.parent_window.tags_edit.setText(prompt_data.get('tags', ''))
                self.parent_window.current_prompt_id = prompt_id
                self.parent_window.on_clear_results()
                self.accept()  # Закрываем диалог
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка: {str(e)}")


class PromptDialog(QDialog):
    """Диалог для добавления/редактирования промта."""
    
    def __init__(self, parent=None, prompt_data: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.prompt_data = prompt_data
        self.setWindowTitle("Добавить промт" if prompt_data is None else "Редактировать промт")
        self.setModal(True)
        self.init_ui()
        
        if prompt_data:
            self.load_prompt_data()
    
    def init_ui(self):
        layout = QFormLayout()
        
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Введите текст промта...")
        self.prompt_edit.setMinimumHeight(150)
        layout.addRow("Промт:", self.prompt_edit)
        
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("Теги (через запятую)")
        layout.addRow("Теги:", self.tags_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
        self.setLayout(layout)
    
    def load_prompt_data(self):
        """Загружает данные промта в форму."""
        if self.prompt_data:
            self.prompt_edit.setPlainText(self.prompt_data.get('prompt', ''))
            self.tags_edit.setText(self.prompt_data.get('tags', ''))
    
    def get_data(self) -> Dict[str, Any]:
        """Возвращает данные из формы."""
        return {
            'prompt': self.prompt_edit.toPlainText().strip(),
            'tags': self.tags_edit.text().strip()
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
    
    # Устанавливаем иконку приложения
    icon_path = os.path.join(os.path.dirname(__file__), "app.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
