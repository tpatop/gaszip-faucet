import os
import sys
from loguru import logger

# Настройка логирования Loguru
LOG_DIR = "src/data/log"
LOG_FILE = os.path.join(LOG_DIR, "logs.txt")
os.makedirs(LOG_DIR, exist_ok=True)

logger.remove()  # Удаляем стандартный handler
logger.add(
    LOG_FILE,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level="INFO",
    rotation="10 MB",  # Логи будут ротироваться по 10MB
    compression="zip",  # Сжатие старых логов
    encoding="utf-8"
)

# Цветной вывод в консоли
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level} | {message}</level>",
    level="INFO"
)

