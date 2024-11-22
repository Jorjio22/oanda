import unittest
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, WebDriverException
from unittest.mock import patch, MagicMock
import pytz
from django.utils.timezone import localtime
from parser.pars import TradingParser
from datetime import datetime
from decimal import Decimal


class TestTradingParser(unittest.TestCase):

    def setUp(self):
        import django
        import os
        os.environ['DJANGO_SETTINGS_MODULE'] = 'traeading_db.settings'
        django.setup()

        self.delays = [Decimal(0), Decimal(5)]
        self.candle_data = (
            [
                [Decimal('1.12345'), '2024-11-21 10:00:55'],
                [Decimal('1.12400'), '2024-11-21 10:01:00'],
            ],
            1000, 2000
        )

    @patch('parser.pars.TradingParser.get_driver')
    def test_initialize_driver(self, mock_get_driver):
        """Тестируем инициализацию драйвера"""
        mock_driver = MagicMock()
        mock_get_driver.return_value = mock_driver
        parser = TradingParser()
        self.assertIsNotNone(parser.driver)
        mock_get_driver.assert_called_once()

    @patch('parser.pars.timezone.now')
    @patch('parser.pars.TradingParser.get_driver')
    def test_should_run_parser_working_day(self, mock_get_driver, mock_now):
        """Тестируем, когда день рабочий и время с 8:00 до 24:00"""

        # Устанавливаем время на 10:00 в понедельник (рабочий день)
        mock_now.return_value = datetime(
            2024, 11, 21, 10, 0, 0, tzinfo=pytz.timezone('Europe/Kyiv')
        )

        # Создаем поддельный драйвер, чтобы избежать реального инициализирования
        mock_driver = MagicMock()
        mock_get_driver.return_value = mock_driver  # Возвращаем мок для get_driver

        parser = TradingParser()
        result = parser.should_run_parser()

        self.assertTrue(result)

    @patch('parser.pars.timezone.now')
    @patch('parser.pars.TradingParser.get_driver')
    def test_should_run_parser_weekend(self, mock_get_driver, mock_now):
        """Тестируем, когда день выходной"""

        # Устанавливаем время на 10:00 в субботу (выходной день)
        mock_now.return_value = datetime(
            2024, 11, 23, 10, 0, 0, tzinfo=pytz.timezone('Europe/Kyiv')
        )

        mock_driver = MagicMock()
        mock_get_driver.return_value = mock_driver

        parser = TradingParser()
        result = parser.should_run_parser()

        self.assertFalse(result)

    @patch('parser.pars.timezone.now')
    @patch('parser.pars.TradingParser.get_driver')
    def test_should_run_parser_night_time(self, mock_get_driver, mock_now):
        """Тестируем, когда время с 24:00 до 8:00"""

        # Устанавливаем время на 3:00 ночи в понедельник (рабочий день, но время вне диапазона)
        mock_now.return_value = datetime(
            2024, 11, 21, 3, 0, 0, tzinfo=pytz.timezone('Europe/Kyiv')
        )

        mock_driver = MagicMock()
        mock_get_driver.return_value = mock_driver

        parser = TradingParser()
        result = parser.should_run_parser()

        self.assertFalse(result)

    def test_correct_convert_the_value_to_decimal(self):
        """Тестируем правильное преобразование строки в Decimal"""

        exchange_rate_text = "100,25"
        expected_result = Decimal('100.25')
        result = TradingParser.convert_the_value_to_decimal(exchange_rate_text)

        self.assertEqual(result, expected_result)

    def test_incorrect_convert_the_value_to_decimal(self):
        """Тестируем некорректное преобразование строки в Decimal"""

        exchange_rate_text = ""
        expected_result = None

        result = TradingParser.convert_the_value_to_decimal(exchange_rate_text)

        self.assertEqual(result, expected_result)

    @patch('parser.pars.logger')
    def test_none_in_convert_the_value_to_decimal(self, mock_logger):
        """Тестируем передачу None вместо строки"""

        exchange_rate_none = None
        expected_result = None

        result = TradingParser.convert_the_value_to_decimal(exchange_rate_none)

        self.assertEqual(result, expected_result)
        mock_logger.error.assert_called_once_with("В метод convert_the_value_to_decimal передано None")

    @patch('parser.pars.TradingParser.get_driver')
    def test_extract_data_success(self, mock_get_driver):
        """Тестируем извлечение данных, когда элемент найден"""

        mock_element = MagicMock()
        mock_element.text = "166,37k"

        mock_driver = MagicMock()
        mock_get_driver.return_value = mock_driver
        mock_driver.find_element.return_value = mock_element

        parser = TradingParser()
        xpath = "//some/xpath"
        result = parser.extract_data(xpath)

        self.assertEqual(result, "166,37k")
        mock_driver.find_element.assert_called_once_with("xpath", xpath)

    @patch('parser.pars.TradingParser.get_driver')
    def test_extract_data_no_such_element_exception(self, mock_get_driver):
        """Тестируем исключение NoSuchElementException"""

        mock_driver = MagicMock()
        mock_get_driver.return_value = mock_driver

        mock_driver.find_element.side_effect = NoSuchElementException("Элемент не найден")

        parser = TradingParser()
        xpath = "//some/xpath"
        result = parser.extract_data(xpath)

        self.assertIsNone(result)
        mock_driver.find_element.assert_called_once_with("xpath", xpath)

    @patch('parser.pars.TradingParser.get_driver')
    def test_extract_data_stale_element_reference_exception(self, mock_get_driver):
        """Тестируем исключение StaleElementReferenceException"""

        mock_driver = MagicMock()
        mock_get_driver.return_value = mock_driver

        mock_driver.find_element.side_effect = StaleElementReferenceException("Ссылка на элемент устарела")

        parser = TradingParser()
        xpath = "//some/xpath"
        result = parser.extract_data(xpath)

        self.assertIsNone(result)
        mock_driver.find_element.assert_called_once_with("xpath", xpath)

    @patch('parser.pars.TradingParser.get_driver')
    def test_extract_data_web_driver_exception(self, mock_get_driver):
        """Тестируем исключение WebDriverException"""

        mock_driver = MagicMock()
        mock_get_driver.return_value = mock_driver

        mock_driver.find_element.side_effect = WebDriverException("Ошибка веб-драйвера")

        parser = TradingParser()
        xpath = "//some/xpath"
        result = parser.extract_data(xpath)

        self.assertIsNone(result)
        mock_driver.find_element.assert_called_once_with("xpath", xpath)

    @patch('parser.pars.TradingParser.get_driver')
    @patch('parser.pars.TradingParser.extract_data')
    @patch('parser.pars.TradingParser.convert_the_value_to_decimal')
    def test_wen_exchange_rate_text_is_none_collection_of_currency_and_time_rates(
            self, mock_convert, mock_extract, mock_get_driver
    ):
        """Тестируем, когда extract_data возвращает None"""

        mock_get_driver.return_value = MagicMock()
        mock_extract.return_value = None
        timestamp = localtime()
        current_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        parser_instance = TradingParser()

        result = parser_instance.collection_of_currency_and_time_rates()
        self.assertEqual(result, [None, current_time])
        mock_extract.assert_called_once()

    @patch('parser.pars.TradingParser.get_driver')
    @patch('parser.pars.TradingParser.extract_data')
    @patch('parser.pars.TradingParser.convert_the_value_to_decimal')
    def test_when_exchange_rate_text_is_valid_collection_of_currency_and_time_rates(
            self, mock_convert, mock_extract, mock_get_driver
    ):
        """Тестируем, когда extract_data возвращает корректное значение"""

        mock_get_driver.return_value = MagicMock()
        mock_extract.return_value = "123.45"
        mock_convert.return_value = Decimal("123.45")

        timestamp = localtime()
        current_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")

        parser_instance = TradingParser()

        result = parser_instance.collection_of_currency_and_time_rates()

        self.assertEqual(result, [Decimal("123.45"), current_time])
        mock_convert.assert_called_once_with("123.45")

    @patch('parser.pars.TradingParser.get_driver')
    @patch('parser.pars.TradingParser.extract_data')
    def test_sales_volume_scrap_returns_none_when_no_data(self, mock_extract, mock_get_driver):
        """Тестируем, когда extract_data возвращает None"""

        mock_get_driver.return_value = MagicMock()
        mock_extract.return_value = None

        parser_instance = TradingParser()

        result = parser_instance.sales_volume_scrap()
        self.assertIsNone(result)
        mock_extract.assert_called_once()

    @patch('parser.pars.TradingParser.get_driver')
    @patch('parser.pars.TradingParser.extract_data')
    def test_sales_volume_scrap_returns_correct_volume(self, mock_extract, mock_get_driver):
        """Тестируем, когда extract_data возвращает корректное значение"""

        mock_get_driver.return_value = MagicMock()
        mock_extract.return_value = "218,29"

        parser_instance = TradingParser()

        result = parser_instance.sales_volume_scrap()
        self.assertEqual(result, 218290)
        mock_extract.assert_called_once()

    @patch('parser.pars.TradingParser.get_driver')
    @patch('parser.pars.TradingParser.extract_data')
    def test_sales_volume_scrap_handles_invalid_data(self, mock_extract, mock_get_driver):
        """Тестируем, когда extract_data возвращает некорректное значение"""

        mock_get_driver.return_value = MagicMock()
        mock_extract.return_value = ""

        parser_instance = TradingParser()

        result = parser_instance.sales_volume_scrap()
        self.assertIsNone(result)

    @patch('parser.pars.timezone.localtime')
    @patch('parser.pars.TradingParser.sales_volume_scrap')
    @patch('parser.pars.TradingParser.collection_of_currency_and_time_rates')
    @patch('parser.pars.time.sleep', return_value=None)
    @patch('parser.pars.TradingParser.get_driver')
    def test_creating_a_one_minute_candle_single_iteration(
            self, mock_get_driver, mock_sleep, mock_collection, mock_sales_volume, mock_localtime):
        """Тестируем метод создания свечи на 1 минуту (1 итерация)"""

        # Мок для метода sales_volume_scrap
        mock_sales_volume.side_effect = [1000, 2000]  # Объем в начале и конце

        # Мок для collection_of_currency_and_time_rates
        mock_collection.side_effect = [
            [Decimal('1.12300'), '2024-11-21 10:00:55:00'],
            [Decimal('1.12400'), '2024-11-21 10:00:56:00'],
            [Decimal('1.12500'), '2024-11-21 10:00:57:00'],
            [Decimal('1.12500'), '2024-11-21 10:00:58:00'],
            [Decimal('1.12500'), '2024-11-21 10:00:59:00'],
            [Decimal('1.12500'), '2024-11-21 10:01:00:00'],
            [Decimal('1.12500'), '2024-11-21 10:01:01:00']
        ]

        # Мок для localtime
        mock_localtime.side_effect = [
            datetime(2024, 11, 21, 10, 0, 55),
            datetime(2024, 11, 21, 10, 0, 56),
            datetime(2024, 11, 21, 10, 0, 57),
            datetime(2024, 11, 21, 10, 0, 58),
            datetime(2024, 11, 21, 10, 0, 59),
            datetime(2024, 11, 21, 10, 1, 0),
            datetime(2024, 11, 21, 10, 1, 1)
        ]

        # Мок для get_driver
        mock_get_driver.return_value = MagicMock()

        # Создаем экземпляр класса TradingParser
        parser_instance = TradingParser()

        # Вызываем метод
        result = parser_instance.creating_a_one_minute_candle()

        # Ожидаемый результат
        expected_candles = [
            [Decimal('1.12300'), '2024-11-21 10:00:55:00'],
            [Decimal('1.12400'), '2024-11-21 10:00:56:00'],
            [Decimal('1.12500'), '2024-11-21 10:00:57:00']
        ]
        expected_volume_start = 1000
        expected_volume_stop = 2000

        # Проверяем результаты
        self.assertEqual(result[0], expected_candles)
        self.assertEqual(result[1], expected_volume_start)
        self.assertEqual(result[2], expected_volume_stop)

        # Проверяем, что mock_localtime был вызван хотя бы 1 раз
        self.assertGreater(mock_localtime.call_count, 0)

        # Проверяем, что collection_of_currency_and_time_rates был вызван хотя бы 1 раз
        self.assertGreater(mock_collection.call_count, 0)

        # Проверяем, что sales_volume_scrap был вызван хотя бы 1 раз
        self.assertGreater(mock_sales_volume.call_count, 0)

        # Проверяем, что get_driver был вызван хотя бы 1 раз
        self.assertGreater(mock_get_driver.call_count, 0)

    def test_open_price(self):
        result = TradingParser.open_price(self.candle_data)
        self.assertEqual(result, {'open_price': Decimal('1.12345')})

    def test_high_price(self):
        result = TradingParser.high_price(self.candle_data)
        self.assertEqual(result, {"high_price": Decimal('1.12400')})

    def test_low_price(self):
        result = TradingParser.low_price(self.candle_data)
        self.assertEqual(result, {"low_price": Decimal('1.12345')})

    def test_average_value(self):
        result = TradingParser.average_value(self.candle_data)
        self.assertEqual(result, {"average_value": Decimal('1.123725')})

    def test_absolute_volatility(self):
        result = TradingParser.absolute_volatility(
            high_price={'high_price': self.candle_data[0][1][0]},
            low_price={'low_price': self.candle_data[0][0][0]}
        )
        self.assertEqual(result,{"absolute_volatility": Decimal('0.00055')})

    def test_percentage_volatility_open(self):
        result = TradingParser.percentage_volatility_open(
            absolute_volatility={"absolute_volatility": Decimal('0.00055')},
            open_price={'open_price': Decimal('1.12345')}
        )
        self.assertEqual(result, {"percentage_volatility_open": Decimal('0.04895633984601005830255018025')})

    def test_percentage_volatility_low(self):
        result = TradingParser.percentage_volatility_low(
            absolute_volatility={"absolute_volatility": Decimal('0.00055')},
            low_price={"low_price": Decimal('1.12345')}
        )
        self.assertEqual(
            result,
            {"percentage_volatility_low": Decimal('0.04895633984601005830255018025')})

    def test_close_price(self):
        result = TradingParser.close_price(self.candle_data)
        self.assertEqual(result, {"close_price": Decimal('1.12400')})

    def test_number_of_changes(self):
        result = TradingParser.number_of_changes(self.candle_data)
        self.assertEqual(result, {"number_of_changes": 1})

    def test_candle_time_intervals(self):
        result = TradingParser.candle_time_intervals(self.candle_data)
        self.assertEqual(result, [5])

    def test_max_delay(self):
        result = TradingParser.max_delay(self.delays)
        self.assertEqual(result, {"max_delay": 5})

    def test_min_delay(self):
        result = TradingParser.min_delay(self.delays)
        self.assertEqual(result, {"min_delay": 0})

    def test_average_delay(self):
        result = TradingParser.average_delay(self.delays)
        self.assertEqual(result, {"average_delay": Decimal("2.5")})

    def test_volume_start(self):
        result = TradingParser.volume_start(self.candle_data)
        self.assertEqual(result, {"volume_start": Decimal("1000")})

    def test_volume_stop(self):
        result = TradingParser.volume_stop(self.candle_data)
        self.assertEqual(result, {"volume_stop": Decimal("2000")})

    def test_volume_delta(self):
        result = TradingParser.volume_delta(
            volume_stop={"volume_stop": Decimal("2000")},
            volume_start={"volume_start": Decimal("1000")}
        )
        self.assertEqual(result, {"volume_delta": Decimal("1000")})

    def test_volume_percent_change(self):
        result = TradingParser.volume_percent_change(
            volume_delta={"volume_delta": Decimal("1000")},
            volume_start={"volume_start": Decimal("1000")}
        )
        self.assertEqual(result, {"volume_percent_change": Decimal("100")})

    def test_volume_average_per_minute(self):
        result = TradingParser.volume_average_per_minute({"volume_delta": Decimal("1000")})
        self.assertEqual(result, {"volume_average_per_minute": Decimal("16.66666666666666666666666667")})

    @patch('parser.pars.TradingParser.get_driver')
    @patch('parser.pars.TradingParser.creating_a_one_minute_candle')
    def test_collect_candle_data_if_len_candle_less_than_three(
            self,
            mock_creating_a_one_minute_candle,
            mock_get_driver
    ):
        """Проверка на недостаточность данных в candle_data"""

        mock_get_driver.return_value = MagicMock()
        mock_creating_a_one_minute_candle.return_value = [
            [1.12345, "2024-11-21 10:00:55"],
            1000
        ]

        instance = TradingParser()
        result = instance .collect_candle_data()
        self.assertEqual(result, {})

    def test_collect_candle_data_normal_candle_data(self):
        """Проверка на создание полноценной свечи"""

        with patch('parser.pars.TradingParser.get_driver') as mock_get_driver, \
                patch('parser.pars.TradingParser.creating_a_one_minute_candle') as mock_creating_a_one_minute_candle, \
                patch('parser.pars.TradingParser.candle_time_intervals') as mock_candle_time_intervals, \
                patch('parser.pars.TradingParser.open_price') as mock_open_price, \
                patch('parser.pars.TradingParser.high_price') as mock_high_price, \
                patch('parser.pars.TradingParser.low_price') as mock_low_price, \
                patch('parser.pars.TradingParser.close_price') as mock_close_price, \
                patch('parser.pars.TradingParser.number_of_changes') as mock_number_of_changes, \
                patch('parser.pars.TradingParser.average_value') as mock_average_value, \
                patch('parser.pars.TradingParser.absolute_volatility') as mock_absolute_volatility, \
                patch('parser.pars.TradingParser.percentage_volatility_open') as mock_percentage_volatility_open, \
                patch('parser.pars.TradingParser.percentage_volatility_low') as mock_percentage_volatility_low, \
                patch('parser.pars.TradingParser.max_delay') as mock_max_delay, \
                patch('parser.pars.TradingParser.min_delay') as mock_min_delay, \
                patch('parser.pars.TradingParser.average_delay') as mock_average_delay, \
                patch('parser.pars.TradingParser.volume_start') as mock_volume_start, \
                patch('parser.pars.TradingParser.volume_stop') as mock_volume_stop, \
                patch('parser.pars.TradingParser.volume_delta') as mock_volume_delta, \
                patch('parser.pars.TradingParser.volume_percent_change') as mock_volume_percent_change, \
                patch('parser.pars.TradingParser.volume_average_per_minute') as mock_volume_average_per_minute:

                mock_get_driver.return_value = MagicMock()
                mock_creating_a_one_minute_candle.return_value = self.candle_data
                mock_candle_time_intervals.return_value = self.delays
                mock_open_price.return_value = {'open_price': Decimal('1.12345')}
                mock_high_price.return_value = {"high_price": Decimal('1.12400')}
                mock_low_price.return_value = {"low_price": Decimal('1.12345')}
                mock_close_price.return_value = {"close_price": Decimal('1.12400')}
                mock_number_of_changes.return_value = {"number_of_changes": 1}
                mock_average_value.return_value = {"average_value": Decimal('1.123725')}
                mock_absolute_volatility.return_value = {"absolute_volatility": Decimal('0.00055')}
                mock_percentage_volatility_open.return_value = {
                    "percentage_volatility_open": Decimal('0.04895633984601005830255018025')
                }
                mock_percentage_volatility_low.return_value = {
                    "percentage_volatility_low": Decimal('0.04895633984601005830255018025')
                }
                mock_max_delay.return_value = {"max_delay": 5}
                mock_min_delay.return_value = {"min_delay": 0}
                mock_average_delay.return_value = {"average_delay": Decimal("2.5")}
                mock_volume_start.return_value = {"volume_start": Decimal("1000")}
                mock_volume_stop.return_value = {"volume_stop": Decimal("2000")}
                mock_volume_delta.return_value = {"volume_delta": Decimal("1000")}
                mock_volume_percent_change.return_value = {"volume_percent_change": Decimal("100")}
                mock_volume_average_per_minute.return_value = {
                    "volume_average_per_minute": Decimal("16.66666666666666666666666667")
                }

                instance = TradingParser()

                result = instance.collect_candle_data()

                expected_result = {
                    "open_price": Decimal("1.12345"),
                    "high_price": Decimal("1.12400"),
                    "low_price": Decimal("1.12345"),
                    "close_price": Decimal("1.12400"),
                    "number_of_changes": 1,
                    "average_value": Decimal("1.123725"),
                    "absolute_volatility": Decimal("0.00055"),
                    "percentage_volatility_open": Decimal("0.04895633984601005830255018025"),
                    "percentage_volatility_low": Decimal("0.04895633984601005830255018025"),
                    "max_delay": 5,
                    "min_delay": 0,
                    "average_delay": Decimal("2.5"),
                    "volume_start": Decimal("1000"),
                    "volume_stop": Decimal("2000"),
                    "volume_delta": Decimal("1000"),
                    "volume_percent_change": Decimal("100"),
                    "volume_average_per_minute": Decimal("16.66666666666666666666666667"),
                }
                self.assertEqual(result, expected_result)

    @patch('parser.pars.TradingParser.get_driver')
    @patch('parser.models.Candle')
    def test_save_candle_data_success(self, MockCandle, mock_get_driver):

        mock_get_driver.return_value = MagicMock()

        data = {
            "open_price": Decimal("1.12345"),
            "high_price": Decimal("1.12400"),
            "low_price": Decimal("1.12345"),
            "average_value": Decimal("1.123725"),
            "absolute_volatility": Decimal("0.00055"),
            "percentage_volatility_open": Decimal("0.048956"),
            "percentage_volatility_low": Decimal("0.048956"),
            "close_price": Decimal("1.12400"),
            "number_of_changes": 1,
            "max_delay": 5,
            "min_delay": 0,
            "average_delay": Decimal("2.5"),
            "volume_start": Decimal("1000"),
            "volume_stop": Decimal("2000"),
            "volume_delta": Decimal("1000"),
            "volume_percent_change": Decimal("100"),
            "volume_average_per_minute": Decimal("16.666666")
        }

        # Мокируем создание объекта и его сохранение
        mock_candle_instance = MagicMock()
        MockCandle.return_value = mock_candle_instance

        # Создаем объект TradingParser и вызываем метод save_candle_data
        parser = TradingParser()
        parser.save_candle_data(data)

        # Проверяем, что метод save был вызван
        mock_candle_instance.save.assert_called_once()

    @patch('parser.pars.TradingParser.get_driver')
    @patch('parser.models.Candle')
    @patch('parser.pars.logger')
    def test_save_candle_data_exception(self, mock_logger, MockCandle, mock_get_driver):
        """Тестируем исключения"""
        mock_get_driver = MagicMock()

        # Моделируем исключение при сохранении
        MockCandle.side_effect = Exception("Test Exception")

        # Подготавливаем данные
        data = {
            "open_price": Decimal("1.12345"),
            "high_price": Decimal("1.12400"),
            "low_price": Decimal("1.12345"),
            "average_value": Decimal("1.123725"),
            "absolute_volatility": Decimal("0.00055"),
            "percentage_volatility_open": Decimal("0.048956"),
            "percentage_volatility_low": Decimal("0.048956"),
            "close_price": Decimal("1.12400"),
            "number_of_changes": 1,
            "max_delay": 5,
            "min_delay": 0,
            "average_delay": Decimal("2.5"),
            "volume_start": Decimal("1000"),
            "volume_stop": Decimal("2000"),
            "volume_delta": Decimal("1000"),
            "volume_percent_change": Decimal("100"),
            "volume_average_per_minute": Decimal("16.666666")
        }

        # Создаем объект TradingParser и вызываем метод save_candle_data
        parser = TradingParser()

        # Проверяем, что исключение было выброшено
        with self.assertRaises(Exception):
            parser.save_candle_data(data)

        # Проверяем, что ошибка была залогирована
        mock_logger.error.assert_called_once_with('Ошибка при сохранении данных свечи: Test Exception')

    @patch('parser.pars.TradingParser.get_driver')
    @patch('parser.pars.TradingParser.should_run_parser')
    @patch('parser.pars.logger')
    @patch('time.sleep', return_value=None)
    @patch('parser.pars.timezone.localtime')
    def test_run_parser(self, mock_localtime, mock_sleep, mock_logger, mock_should_run_parser, mock_get_driver):
        mock_get_driver = MagicMock()
        # Создаём объект парсера
        parser = TradingParser()

        # Мокаем should_run_parser, чтобы он возвращал True, а затем False, чтобы выйти из цикла
        mock_should_run_parser.side_effect = [True, True, False]  # Первые два вызова True, потом False


        # Прерываем цикл после 3 итераций
        try:
            parser.run_parser()  # Запускаем парсер
        except:
            pass

        # Проверяем, что логгер записал информацию о запуске парсера
        mock_logger.info.assert_any_call("########## Starting TradingParser ##########")

        # Проверяем, что логгер записал информацию о том, что парсер не работает (когда should_run_parser = False)
        mock_logger.info.assert_any_call(
            f"Парсер не работает. Ожидание начала работы с ПН по ПТ с 8-00 до 24-00."
        )

        # Проверяем, что sleep был вызван хотя бы один раз
        self.assertGreater(mock_sleep.call_count, 0)
