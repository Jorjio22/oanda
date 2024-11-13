from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
from django.utils import timezone
import re
from decimal import Decimal, InvalidOperation
from django.db import transaction
import logging


driver = None
logger = logging.getLogger('parser')


class TradingParser:
    def __init__(self):
        global driver
        # Проверка на существование драйвера
        if driver is None:
            driver = self.get_driver()
        self.driver = driver

    # Метод для инициализации драйвера123
    def get_driver(self):
        options = Options()
        options.add_argument("--window-size=1920,1680")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.3"
        )
        options.add_argument("--headless")  # Добавляем headless-режим для сервера

        service = Service(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get("https://ru.tradingview.com/symbols/EURUSD/?exchange=OANDA")
        return driver

    # Метод для проверки необходимости запуска парсера
    def should_run_parser(self):
        now_kiev = timezone.localtime(timezone.now())
        return now_kiev.weekday() < 5 and 8 <= now_kiev.hour < 24

    # Метод для получения обменного курса
    def exchange_rate_scrap(self):
        timestamp = timezone.now()
        formatted_timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")

        # Получаем текст обменного курса с сайта
        exchange_rate_text = self.driver.find_element("xpath", "//span[@class='last-JWoJqCpY js-symbol-last']").text

        # Пробуем преобразовать значение в Decimal, обрабатывая исключения
        try:
            exchange_rate = Decimal(exchange_rate_text.replace(',', '.'))
        except (InvalidOperation, ValueError) as e:
            logger.error(f"Не удалось преобразовать обменный курс в Decimal: {exchange_rate_text}, ошибка: {e}")
            return None

        return [exchange_rate, formatted_timestamp]

    # Метод для получения объема продаж
    def sales_volume_scrap(self):
        volume = self.driver.find_element("xpath", "//div[@class='apply-overflow-tooltip value-GgmpMpKr'][1]").text
        volume = Decimal(re.sub(r"[^\d,]", "", volume).replace(",", ".")) * 1000
        return int(volume)

    # Метод для получения уникальных значений курса
    def unique_course_value(self):
        logger.info(f"Start of information collection: {timezone.now().strftime('%Y-%m-%d %H:%M')}")
        candles_data = []
        volume_start = self.sales_volume_scrap()
        end_time = timezone.now().replace(second=59, microsecond=999999)

        while timezone.now() < end_time:
            one_second = self.exchange_rate_scrap()
            if not candles_data or candles_data[-1][0] != one_second[0]:
                candles_data.append(one_second)
            time.sleep(0.5)

        logger.info(f"Stop of information collection: {timezone.now().strftime('%Y-%m-%d %H:%M')}")
        volume_stop = self.sales_volume_scrap()
        return candles_data, volume_start, volume_stop

    # Метод для формирования свечи
    def candle_formation(self, candles_data):
        from .models import Candle  # Импортируем модель здесь, чтобы избежать ошибки
        candle_param = {}
        if candles_data:
            candle_param["open_price"] = candles_data[0][0][0]
            candle_param["high_price"] = max(Decimal(candle[0]) for candle in candles_data[0])
            candle_param["low_price"] = min(Decimal(candle[0]) for candle in candles_data[0])
            candle_param["average_value"] = sum(Decimal(candle[0]) for candle in candles_data[0]) / len(candles_data[0])

            candle_param["absolute_volatility"] = candle_param["high_price"] - candle_param["low_price"]
            candle_param["percentage_volatility_open"] = (
                                                                 candle_param["absolute_volatility"] / candle_param[
                                                             "open_price"]
                                                         ) * 100
            candle_param["percentage_volatility_low"] = (
                                                                candle_param["absolute_volatility"] / candle_param[
                                                            "low_price"]
                                                        ) * 100
            candle_param["close_price"] = candles_data[0][-1][0]
            candle_param["number_of_changes"] = len(candles_data[0]) - 1

            seconds = [int(candle[1][-2:]) for candle in candles_data[0]]
            delays = [Decimal(seconds[i + 1]) - Decimal(seconds[i]) for i in range(len(seconds) - 1)]
            candle_param["max_delay"] = max(delays) if delays else Decimal(0)
            candle_param["min_delay"] = min(delays) if delays else Decimal(0)
            candle_param["average_delay"] = sum(delays) / len(delays) if delays else Decimal(0)

            candle_param["volume_start"] = Decimal(candles_data[1])
            candle_param["volume_stop"] = Decimal(candles_data[2])
            candle_param["volume_delta"] = candle_param["volume_stop"] - candle_param["volume_start"]

            candle_param["volume_percent_change"] = (
                (candle_param["volume_delta"] / candle_param["volume_start"]) * 100
                if candle_param["volume_start"] != Decimal(0) else Decimal(0)
            )
            candle_param["volume_average_per_minute"] = candle_param["volume_delta"] / Decimal(60)

            logger.info(f"Open price: {candle_param['open_price']}")
            logger.info(f"Close price: {candle_param['close_price']}")
            logger.info(f"High price: {candle_param['high_price']}")
            logger.info(f"Low price: {candle_param['low_price']}")
            logger.info(f"Average price: {candle_param['average_value']}")

            try:
                Candle.objects.create(**candle_param)
            except Exception as e:
                logger.info(f"Ошибка при записи в базу данных: {e}")

    # Основной метод для запуска парсера
    def run_parser(self):
        logger.info("########## Starting TradingParser ##########")
        while True:
            if self.should_run_parser():
                try:
                    with transaction.atomic():
                        candles_data = self.unique_course_value()
                        self.candle_formation(candles_data)
                except Exception as e:
                    logger.info(f"Ошибка при парсинге: {e}")
            else:
                logger.info(
                    f"{timezone.now().strftime('%Y-%m-%d %H:%M')} - Парсер не работает. Ожидание начала работы."
                )
                time.sleep(60)  # Ожидаем 1 минут перед следующей проверкой


def run_parser_in_thread():
    parser = TradingParser()
    parser.run_parser()
