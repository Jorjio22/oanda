import django
import os

os.environ['DJANGO_SETTINGS_MODULE'] = 'traeading_db.settings'
django.setup()

import unittest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from parser.pars import TradingParser
from datetime import datetime
from decimal import Decimal
import time
from itertools import cycle


class TestTradingParser(unittest.TestCase):
    def setUp(self):
        # Патч chrome webdriver
        self.patcher_chrome = patch('selenium.webdriver.Chrome')
        self.mock_chrome = self.patcher_chrome.start()

        # Патч ChromeDriverManager().install
        self.patcher_driver_install = patch(
            'webdriver_manager.chrome.ChromeDriverManager.install',
            return_value='/path/to/fake/driver'
        )
        self.mock_driver_install = self.patcher_driver_install.start()

        # Создаём парсер
        self.parser = TradingParser()

    def test_driver_manager_installed(self):
        # Проверка, что метод install был вызван и вернул фиктивный путь
        self.mock_driver_install.assert_called_once()
        # Также проверим, что путь возвращает фальшивый путь
        self.assertEqual(self.mock_driver_install.return_value, '/path/to/fake/driver')

    @patch.object(TradingParser, 'get_driver')  # Патчим метод get_driver
    def test_exchange_rate_scrap_success(self, mock_get_driver):
        self.parser.driver = MagicMock()

        # Создаем мок-объект для метода find_element
        mock_element = MagicMock()
        mock_element.text = "1.2345"  # Задаем текст, который должен быть возвращен

        # Настройка поведения mock: метод find_element должен вернуть mock_element
        self.parser.driver.find_element.return_value = mock_element

        # Текущая временная метка с использованием timezone.now()
        current_time = timezone.localtime().strftime("%Y-%m-%d %H:%M:%S")

        # Выполняем тестируемый метод
        result = self.parser.exchange_rate_scrap()

        # Проверяем, что результат является списком с двумя элементами
        self.assertEqual(result, [Decimal('1.2345'), current_time])

    def test_should_run_parser_weekday_within_hours(self):
        # Рабочий день и время между 8:00 и 23:59
        with patch('django.utils.timezone.localtime') as mock_time:
            # Мокируем дату и время, возвращая правильный объект datetime с временной зоной
            mock_time.return_value = datetime(2024, 11, 15, 10, 0, 0, tzinfo=timezone.get_current_timezone())
            result = self.parser.should_run_parser()
            self.assertTrue(result, "Функция должна возвращать True в рабочий день между 8:00 и 23:59.")

    def test_should_run_parser_weekday_outside_hours(self):
        # Рабочий день, но время за пределами рабочего (например, 7:00)
        with patch('django.utils.timezone.localtime') as mock_time:
            # Мокируем дату и время, возвращая правильный объект datetime с временной зоной
            mock_time.return_value = datetime(2024, 11, 15, 7, 0, 0, tzinfo=timezone.get_current_timezone())
            result = self.parser.should_run_parser()
            self.assertFalse(result, "Функция должна возвращать False до 8:00.")

    def test_should_run_parser_weekend(self):
        # Суббота, любое время
        with patch('django.utils.timezone.localtime') as mock_time:
            # Мокируем дату и время, возвращая правильный объект datetime с временной зоной
            mock_time.return_value = datetime(2024, 11, 16, 10, 0, 0, tzinfo=timezone.get_current_timezone())
            result = self.parser.should_run_parser()
            self.assertFalse(result, "Функция должна возвращать False в выходной день.")

    @patch.object(TradingParser, 'sales_volume_scrap')  # Мокаем sales_volume_scrap
    @patch.object(TradingParser, 'exchange_rate_scrap')  # Мокаем exchange_rate_scrap
    @patch('django.utils.timezone.localtime')  # Мокаем timezone.localtime
    @patch('time.sleep')  # Мокаем time.sleep, чтобы избежать задержек
    def test_unique_course_value(self, mock_sleep, mock_localtime, mock_exchange_rate_scrap, mock_sales_volume_scrap):
        # Настройка мока для времени с использованием timezone
        mock_localtime.return_value = timezone.make_aware(timezone.datetime(
            2024, 11, 15, 18, 30, 0
        ))

        # Настройка мока для sales_volume_scrap
        mock_sales_volume_scrap.side_effect = [Decimal('1234.56'), Decimal('2345.67')]  # Пример объемов

        # Настройка мока для exchange_rate_scrap с циклом данных, ограниченным количеством итераций
        mock_exchange_rate_scrap.side_effect = cycle([
            ("2024-11-15 18:30:00", 1.234),
            ("2024-11-15 18:30:01", 1.235),
            ("2024-11-15 18:30:02", 1.236)
        ])

        # Ограничиваем количество итераций в методе unique_course_value
        def limited_unique_course_value():
            candles_data = []
            volume_start = self.parser.sales_volume_scrap()

            for _ in range(3):  # Ограничиваем количество итераций до 3
                one_second = self.parser.exchange_rate_scrap()
                if not candles_data or candles_data[-1][0] != one_second[0]:
                    candles_data.append(one_second)
                time.sleep(0.5)

            volume_stop = self.parser.sales_volume_scrap()
            return candles_data, volume_start, volume_stop

        # Присваиваем метод с ограничением итераций
        self.parser.unique_course_value = limited_unique_course_value

        # Запуск тестируемого метода
        candles_data, volume_start, volume_stop = self.parser.unique_course_value()

        # Проверяем, что sales_volume_scrap был вызван дважды
        self.assertEqual(mock_sales_volume_scrap.call_count, 2)

        # Проверяем, что exchange_rate_scrap был вызван трижды
        self.assertEqual(mock_exchange_rate_scrap.call_count, 3)

        # Проверяем, что данные candles_data содержат 3 элемента
        self.assertEqual(len(candles_data), 3)

        # Проверяем, что начальный и конечный объемы правильные
        self.assertEqual(volume_start, Decimal('1234.56'))
        self.assertEqual(volume_stop, Decimal('2345.67'))

        # Проверяем, что sleep был вызван 2 раза (всего 3 вызова exchange_rate_scrap, значит 2 sleep)
        mock_sleep.assert_called_with(0.5)

    def tearDown(self):
        # Останавливаем патчи
        self.patcher_chrome.stop()
        self.patcher_driver_install.stop()
