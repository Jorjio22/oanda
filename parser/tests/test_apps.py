import unittest
from unittest.mock import patch
from parser.apps import ParserConfig


class TestParserConfig(unittest.TestCase):
    def setUp(self):
        """
        Общая настройка для тестов.
        Создаём подкласс ParserConfig с фиктивным путём.
        """
        class TestableParserConfig(ParserConfig):
            path = '/test/path'

        self.config_class = TestableParserConfig
        self.config = TestableParserConfig('parser', TestableParserConfig)

    @patch('os.path.exists')
    @patch('builtins.open')
    @patch('threading.Thread')
    @patch('parser.apps.logger')
    def test_ready_creates_lock_file_and_starts_thread(self, mock_logger, mock_thread, mock_open, mock_exists):
        """
        Описание теста:
        Этот тест проверяет, что если файл блокировки не существует, то:
        1. Он будет создан.
        2. Новый поток парсера будет запущен.
        3. В логах появится сообщение о запуске нового потока.
        """
        # Симулируем, что файл блокировки не существует
        mock_exists.return_value = False

        # Вызываем метод ready
        self.config.ready()

        # Проверяем, что файл блокировки был создан
        mock_open.assert_called_once_with(self.config.lock_file, 'w')

        # Проверяем, что новый поток был запущен
        mock_thread.assert_called_once_with(target=self.config.start_parser_thread, daemon=True)

        # Проверяем, что в логах есть сообщение о запуске нового потока
        mock_logger.info.assert_any_call("Запуск нового потока парсера")

    @patch('os.path.exists')
    @patch('parser.apps.logger')
    def test_ready_does_not_create_thread_if_lock_file_exists(self, mock_logger, mock_exists):
        """
        Описание теста:
        Этот тест проверяет, что если файл блокировки существует, то:
        1. Новый поток не будет создан.
        2. В логах появится сообщение о том, что парсер уже запущен.
        """
        # Симулируем, что файл блокировки уже существует
        mock_exists.return_value = True

        # Вызываем метод ready
        self.config.ready()

        # Проверяем, что новый поток не был создан
        mock_logger.info.assert_any_call("Парсер уже запущен, новый поток не создан")

    @patch('parser.pars.run_parser_in_thread')
    @patch('parser.apps.logger')
    def test_start_parser_thread_runs_parser_successfully(self, mock_logger, mock_run_parser):
        """
        Тестирует успешный вызов run_parser_in_thread.
        """
        # Вызываем метод start_parser_thread
        self.config.start_parser_thread()

        # Проверяем, что run_parser_in_thread был вызван
        mock_run_parser.assert_called_once()

        # Проверяем, что не было вызовов логгера с ошибками
        mock_logger.error.assert_not_called()

    @patch('parser.pars.run_parser_in_thread')
    @patch('parser.apps.logger')
    def test_start_parser_thread_logs_exception_on_failure(self, mock_logger, mock_run_parser):
        """
        Тестирует, что исключение в run_parser_in_thread логируется.
        """
        # Симулируем исключение в run_parser_in_thread
        mock_run_parser.side_effect = Exception("Test Exception")

        # Вызываем метод start_parser_thread
        self.config.start_parser_thread()

        # Проверяем, что run_parser_in_thread был вызван
        mock_run_parser.assert_called_once()

        # Проверяем, что ошибка была залогирована
        mock_logger.error.assert_called_once_with("Ошибка при запуске потока парсера: Test Exception")

    @patch('parser.pars.run_parser_in_thread')
    @patch('parser.apps.ParserConfig.cleanup')
    def test_start_parser_thread_calls_cleanup(self, mock_cleanup, mock_run_parser):
        """
        Тестирует, что метод cleanup вызывается в блоке finally.
        """
        # Вызываем метод start_parser_thread
        self.config.start_parser_thread()

        # Проверяем, что cleanup был вызван
        mock_cleanup.assert_called_once()

    @patch('os.path.exists')
    @patch('os.remove')
    @patch('parser.apps.logger')
    def test_cleanup_removes_lock_file_if_exists(self, mock_logger, mock_remove, mock_exists):
        """
        Тестирует, что файл блокировки удаляется, если он существует,
        и логгер записывает сообщение об этом.
        """
        # Симулируем, что файл блокировки существует
        mock_exists.return_value = True

        # Создаём объект конфигурации
        config = self.config

        # Вызываем метод cleanup
        config.cleanup()

        # Проверяем, что os.path.exists был вызван с правильным путём
        mock_exists.assert_called_once_with(config.lock_file)

        # Проверяем, что os.remove был вызван
        mock_remove.assert_called_once_with(config.lock_file)

        # Проверяем, что логгер записал сообщение
        mock_logger.info.assert_called_once_with("Файл блокировки удален, парсер завершен")

    @patch('os.path.exists')
    @patch('os.remove')
    @patch('parser.apps.logger')
    def test_cleanup_does_nothing_if_lock_file_does_not_exist(self, mock_logger, mock_remove, mock_exists):
        """
        Тестирует, что метод ничего не делает, если файл блокировки не существует.
        """
        # Симулируем, что файл блокировки не существует
        mock_exists.return_value = False

        # Создаём объект конфигурации
        config = self.config

        # Вызываем метод cleanup
        config.cleanup()

        # Проверяем, что os.path.exists был вызван с правильным путём
        mock_exists.assert_called_once_with(config.lock_file)

        # Проверяем, что os.remove не был вызван
        mock_remove.assert_not_called()

        # Проверяем, что логгер ничего не записывал
        mock_logger.info.assert_not_called()
