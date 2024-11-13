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
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': LOG_FILE_PATH,
            'formatter': 'default',
        },
    },
    'loggers': {
        '': {  # root logger
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'parser': {  # Логгер для парсера
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Инициализация конфигурации логирования
logging.config.dictConfig(LOGGING)
