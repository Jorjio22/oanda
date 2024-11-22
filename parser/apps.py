import threading
import os
import signal
from django.apps import AppConfig
import logging


logger = logging.getLogger('parser')


class ParserConfig(AppConfig):
    name = 'parser'
    # lock_file = 'D:/OANDA_TREADING/parser_thread.lock'
    lock_file = '/tmp/parser_thread.lock'

    def ready(self):
        # Подключаем обработчик сигнала завершения
        signal.signal(signal.SIGTERM, self.cleanup)
        signal.signal(signal.SIGINT, self.cleanup)

        # Проверяем, есть ли файл блокировки
        if not os.path.exists(self.lock_file):
            open(self.lock_file, 'w').close()  # Создаем файл-маркер
            logger.info("Запуск нового потока парсера")
            threading.Thread(target=self.start_parser_thread, daemon=True).start()
        else:
            logger.info("Парсер уже запущен, новый поток не создан")

    def start_parser_thread(self):
        from .pars import run_parser_in_thread
        try:
            run_parser_in_thread()
        except Exception as e:
            logger.error(f"Ошибка при запуске потока парсера: {e}")
        finally:
            self.cleanup()

    def cleanup(self, *args):
        # Удаляем файл блокировки, если он существует
        if os.path.exists(self.lock_file):
            os.remove(self.lock_file)
            logger.info("Файл блокировки удален, парсер завершен")
