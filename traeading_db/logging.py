import logging.config
from pathlib import Path

# Укажите путь, где будет сохраняться лог-файл
LOG_FILE_PATH = Path(__file__).resolve().parent / 'parser_thread.log'

# Конфигурация логирования
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        },
    },
    'handlers': {
        'console': {
            'level': 'ERROR',  # Меняем уровень на ERROR
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
        'file': {
            'level': 'ERROR',  # Меняем уровень на ERROR
            'class': 'logging.FileHandler',
            'filename': LOG_FILE_PATH,
            'formatter': 'default',
            'encoding': 'utf-8',
        },
    },
    'loggers': {
        '': {  # root logger
            'handlers': ['console', 'file'],
            'level': 'ERROR',  # Меняем уровень на ERROR
            'propagate': True,
        },
        'parser': {  # Логгер для парсера
            'handlers': ['file'],
            'level': 'ERROR',  # Меняем уровень на ERROR
            'propagate': False,
        },
    },
}

# Инициализация конфигурации логирования
logging.config.dictConfig(LOGGING)
