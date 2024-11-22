from typing import List, Union, Tuple, Dict

from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, WebDriverException
import time
from django.utils import timezone
from datetime import datetime
import re
from decimal import Decimal, InvalidOperation
from django.db import transaction
import logging

logger = logging.getLogger('parser')


class TradingParser:
    def __init__(self) -> None:
        logger.info("Start: __init__")
        self.driver = None
        self.initialize_driver()

    def initialize_driver(self) -> None:
        """Проверка и инициализация драйвера"""
        logger.info("Start: initialize_driver")

        if self.driver is None:
            self.driver = self.get_driver()

    def get_driver(self) -> WebDriver:
        """Создание и настройка драйвера"""
        logger.info("Start: get_driver")

        options = Options()
        options.add_argument("--window-size=1920,1680")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.3"
        )
        options.add_argument("--headless")  # Режим без графического интерфейса
        options.add_argument("--disable-gpu")  # Отключение GPU

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get("https://ru.tradingview.com/symbols/EURUSD/?exchange=OANDA")
        return driver

    def should_run_parser(self) -> bool:
        """Проверяем, что день рабочий и время с 8-00 до 24-00"""
        logger.info("Start: should_run_parser")

        now_kiev = timezone.localtime(timezone.now())
        return now_kiev.weekday() < 5 and 8 <= now_kiev.hour < 24

    @staticmethod
    def convert_the_value_to_decimal(exchange_rate_text: str | None) -> Decimal | None:
        """Преобразовываем строковое значение в децимал"""

        if exchange_rate_text is None:
            logger.error("В метод convert_the_value_to_decimal передано None")
            return None

        try:
            exchange_rate_decimal = Decimal(exchange_rate_text.replace(',', '.'))
            return exchange_rate_decimal
        except (InvalidOperation, ValueError) as e:
            logger.error(f"Не удалось преобразовать обменный курс в Decimal: {exchange_rate_text}, ошибка: {e}")
            return None

    def extract_data(self, xpath: str) -> str | None:
        """Общий метод для извлечения данных со страницы"""

        try:
            element = self.driver.find_element("xpath", xpath).text
            return element
        except (NoSuchElementException, StaleElementReferenceException, WebDriverException) as e:
            logger.error(f"Ошибка при извлечении данных с XPath {xpath}: {e}")
            return None

    def collection_of_currency_and_time_rates(self) -> List[Union[Decimal, None, str]]:
        """Собираем информацию о курсе и времени"""

        timestamp = timezone.localtime()
        formatted_timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        xpath = "//span[@class='last-JWoJqCpY js-symbol-last']"

        exchange_rate_text = self.extract_data(xpath)
        if exchange_rate_text is None:
            return [None, formatted_timestamp]

        exchange = self.convert_the_value_to_decimal(exchange_rate_text)
        return [exchange, formatted_timestamp]

    def sales_volume_scrap(self) -> int | None:
        """Получаем значение объёма продаж"""
        logger.info("Start: sales_volume_scrap")
        xpath = "//div[@class='apply-overflow-tooltip value-GgmpMpKr'][1]"

        volume_text = self.extract_data(xpath)
        if volume_text is None:
            return None

        try:
            volume = Decimal(re.sub(r"[^\d,]", "", volume_text).replace(",", ".")) * 1000
            return int(volume)
        except (ValueError, InvalidOperation) as e:
            logger.error(f"Ошибка преобразования объёма продаж: {volume_text}, ошибка: {e}")
            return None

    def creating_a_one_minute_candle(self) -> Tuple[List[List[Decimal | None | str]], int | None, int | None]:
        """Создаём свечу в 1 минуту"""
        logger.info("Start: creating_a_one_minute_candle")
        logger.info(f"Start of information collection: {timezone.localtime().strftime('%Y-%m-%d %H:%M')}")
        candles_data = []
        volume_start = self.sales_volume_scrap()
        end_time = timezone.localtime().replace(second=59, microsecond=999999)

        while timezone.localtime() < end_time:
            one_second = self.collection_of_currency_and_time_rates()
            exchange = one_second[0]

            if not candles_data or candles_data[-1][0] != exchange:
                candles_data.append(one_second)
            time.sleep(0.5)

        logger.info(f"Stop of information collection: {timezone.localtime().strftime('%Y-%m-%d %H:%M')}")
        volume_stop = self.sales_volume_scrap()
        logger.info(f"###creating_a_one_minute_candle### Return: {candles_data, volume_start, volume_stop}")
        return candles_data, volume_start, volume_stop

    @staticmethod
    def open_price(candle_data: Tuple[List[List[Decimal | None | str]], int | None, int | None]) -> dict:
        """Цена открытия свечи"""
        logger.info("Start: open_price")
        return {"open_price": candle_data[0][0][0]}

    @staticmethod
    def high_price(candle_data: Tuple[List[List[Decimal | None | str]], int | None, int | None]) -> dict:
        """Самая высокая цена свечи"""
        logger.info("Start: high_price")
        return {"high_price": max(Decimal(candle[0]) for candle in candle_data[0])}

    @staticmethod
    def low_price(candle_data: Tuple[List[List[Decimal | None | str]], int | None, int | None]) -> dict:
        """Самая низкая цена свечи"""
        logger.info("Start: low_price")
        return {"low_price": min(Decimal(candle[0]) for candle in candle_data[0])}

    @staticmethod
    def average_value(candle_data: Tuple[List[List[Decimal | None | str]], int | None, int | None]) -> dict:
        """Средняя цена свечи"""
        logger.info("Start: average_value")
        return {"average_value": sum(Decimal(candle[0]) for candle in candle_data[0]) / len(candle_data[0])}

    @staticmethod
    def absolute_volatility(high_price: Dict[str, Decimal], low_price: Dict[str, Decimal]) -> dict:
        """Абсолютная волатильность свечи"""
        logger.info("Start: absolute_volatility")
        return {"absolute_volatility": high_price["high_price"] - low_price["low_price"]}

    @staticmethod
    def percentage_volatility_open(absolute_volatility: Dict[str, Decimal], open_price: Dict[str, Decimal]) -> dict:
        """Волатильность свечи относительно цены открытия в процентах"""
        logger.info("Start: percentage_volatility_open")
        return {"percentage_volatility_open": (
                                                      absolute_volatility["absolute_volatility"] / open_price[
                                                  "open_price"]
                                              ) * 100}

    @staticmethod
    def percentage_volatility_low(absolute_volatility: Dict[str, Decimal], low_price: Dict[str, Decimal]) -> dict:
        """Волатильность свечи в процентах относительно самой низкой цены"""
        logger.info("Start: percentage_volatility_low")
        return {
            "percentage_volatility_low": (absolute_volatility["absolute_volatility"] / low_price["low_price"]) * 100}

    @staticmethod
    def close_price(candle_data: Tuple[List[List[Decimal | None | str]], int | None, int | None]) -> dict:
        """Цена закрытия свечи"""
        logger.info("Start: close_price")
        return {"close_price": candle_data[0][-1][0]}

    @staticmethod
    def number_of_changes(candle_data: Tuple[List[List[Decimal | None | str]], int | None, int | None]) -> dict:
        """Кол-во изменений курса свечи"""
        logger.info("Start: number_of_changes")
        return {"number_of_changes": len(candle_data[0]) - 1}

    @staticmethod
    def candle_time_intervals(
            candle_data: Tuple[List[List[Decimal | None | str]], int | None, int | None]
    ) -> List[Decimal]:
        """Рассчитываем задержку изменения курса свечи в секундах"""

        logger.info("Start: candle_time_intervals")

        # Извлекаем строки с датами
        times = [candle[1] for candle in candle_data[0]]

        # Конвертируем строки в объекты datetime
        time_objects = [datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S') for time_str in times]

        # Вычисляем разницу во времени между изменениями курса
        delays = []
        for i in range(len(time_objects) - 1):
            delta = time_objects[i + 1] - time_objects[i]
            delays.append(Decimal(delta.total_seconds()))

        return delays

    @staticmethod
    def max_delay(delays: List[Decimal]) -> dict:
        """Максимальный промежуток в секундах между изменениями курса свечи"""
        logger.info("Start: max_delay")
        return {"max_delay": max(delays) if delays else Decimal(0)}

    @staticmethod
    def min_delay(delays: List[Decimal]) -> dict:
        """Минимальный промежуток в секундах между изменениями курса свечи"""
        logger.info("Start: min_delay")
        return {"min_delay": min(delays) if delays else Decimal(0)}

    @staticmethod
    def average_delay(delays: List[Decimal]) -> dict:
        """Средний промежуток в секундах между изменениями курса свечи"""
        logger.info("Start: average_delay")
        return {"average_delay": Decimal(sum(delays)) / Decimal(len(delays)) if delays else Decimal(0)}

    @staticmethod
    def volume_start(candle_data: Tuple[List[List[Decimal | None | str]], int | None, int | None]) -> dict:
        """Начальный объём продаж"""
        logger.info("Start: volume_start")
        return {"volume_start": Decimal(candle_data[1])}

    @staticmethod
    def volume_stop(candle_data: Tuple[List[List[Decimal | None | str]], int | None, int | None]) -> dict:
        """Конечный объём продаж"""
        logger.info("Start: volume_stop")
        return {"volume_stop": Decimal(candle_data[2])}

    @staticmethod
    def volume_delta(volume_stop: Dict[str, Decimal], volume_start: Dict[str, Decimal]) -> dict:
        """Объём продаж свечи"""
        logger.info("Start: volume_delta")
        logger.info(f"volume_stop: {volume_stop}")
        logger.info(f"volume_start: {volume_start}")
        return {"volume_delta": volume_stop["volume_stop"] - volume_start["volume_start"]}

    @staticmethod
    def volume_percent_change(volume_delta: Dict[str, Decimal], volume_start: Dict[str, Decimal]) -> dict:
        """Волатильность объёма продаж свечи"""
        logger.info("Start: volume_percent_change")
        return {"volume_percent_change":
                    (volume_delta["volume_delta"] / volume_start["volume_start"]) * 100
                    if volume_delta["volume_delta"] != Decimal(0) else Decimal(0)
                }

    @staticmethod
    def volume_average_per_minute(volume_delta: Dict[str, Decimal]) -> dict:
        """Средний объём продаж свечи за секунду"""
        logger.info("Start: volume_average_per_minute")
        return {"volume_average_per_minute": volume_delta["volume_delta"] / Decimal(60)}

    def collect_candle_data(self) -> dict:
        """Вычисляем конечные данные для одной минутной свечи."""
        logger.info("Start: collect_candle_data")
        candle_data = self.creating_a_one_minute_candle()

        # Проверяем входные данные
        if not candle_data or len(candle_data) < 3:
            logger.error("Недостаточно данных для формирования свечи.")
            return {}

        delays = self.candle_time_intervals(candle_data)
        open_price = self.open_price(candle_data)
        high_price = self.high_price(candle_data)
        low_price = self.low_price(candle_data)
        close_price = self.close_price(candle_data)
        number_of_changes = self.number_of_changes(candle_data)
        average_value = self.average_value(candle_data)
        absolute_volatility = self.absolute_volatility(high_price, low_price)
        percentage_volatility_open = self.percentage_volatility_open(absolute_volatility, open_price)
        percentage_volatility_low = self.percentage_volatility_low(absolute_volatility, low_price)
        max_delay = self.max_delay(delays)
        min_delay = self.min_delay(delays)
        average_delay = self.average_delay(delays)
        volume_start = self.volume_start(candle_data)
        volume_stop = self.volume_stop(candle_data)
        volume_delta = self.volume_delta(volume_stop, volume_start)
        volume_percent_change = self.volume_percent_change(volume_delta, volume_start)
        volume_average_per_minute = self.volume_average_per_minute(volume_delta)

        candle_summary = {
            **open_price,
            **high_price,
            **low_price,
            **close_price,
            **number_of_changes,
            **average_value,
            **absolute_volatility,
            **percentage_volatility_open,
            **percentage_volatility_low,
            **max_delay,
            **min_delay,
            **average_delay,
            **volume_start,
            **volume_stop,
            **volume_delta,
            **volume_percent_change,
            **volume_average_per_minute,
        }

        logger.info(f"Сформированная свеча: {candle_summary}")
        return candle_summary

    def save_candle_data(self, data: dict):
        """Сохраняет собранные данные в базу данных."""
        logger.info("Start: save_candle_data")
        from .models import Candle

        try:
            # Создаем объект Candle с данными из словаря
            candle = Candle(
                open_price=data["open_price"],
                high_price=data["high_price"],
                low_price=data["low_price"],
                average_value=data["average_value"],
                absolute_volatility=data["absolute_volatility"],
                percentage_volatility_open=data["percentage_volatility_open"],
                percentage_volatility_low=data["percentage_volatility_low"],
                close_price=data["close_price"],
                number_of_changes=data["number_of_changes"],
                max_delay=data["max_delay"],
                min_delay=data["min_delay"],
                average_delay=data["average_delay"],
                volume_start=data["volume_start"],
                volume_stop=data["volume_stop"],
                volume_delta=data["volume_delta"],
                volume_percent_change=data["volume_percent_change"],
                volume_average_per_minute=data["volume_average_per_minute"],
            )

            # Сохраняем объект в базу данных
            candle.save()
            logger.info(f"Сохранена свеча: {candle}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении данных свечи: {e}")
            raise

    def run_parser(self):
        logger.info("########## Starting TradingParser ##########")
        while True:
            if self.should_run_parser():
                try:
                    with transaction.atomic():
                        data = self.collect_candle_data()
                        self.save_candle_data(data)
                        logger.info(f"Данные успешно сохранены: {data}")
                except Exception as e:
                    logger.error(f"Ошибка при парсинге: {e}")
            else:
                logger.info(
                    f"Парсер не работает. Ожидание начала работы с ПН по ПТ с 8-00 до 24-00."
                )
                time.sleep(60)  # Ожидаем 1 минуту перед следующей проверкой


def run_parser_in_thread():
    logger.info("Start: run_parser_in_thread")
    parser = TradingParser()
    parser.run_parser()
