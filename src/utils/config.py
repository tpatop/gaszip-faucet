import os
from typing import List

class Config:
    BRIDGE_ALL = False                  # Использовать весь баланс для работы
    AMOUNT_TO_REFUEL = [0.0005, 0.001]  # Диапазон отправки токенов
    TARGET_TX = 100                     # Количество транзакций к выполнению на каждом аккаунте
    MAX_RETRIES = 5                     # Количество повторных попыток в случае ошибки
    SEMAPHORE_LIMIT = 5                 # Ограничение на количество одновременных транзакций
    SLEEP_AFTER_TX = [5, 10]            # Сон после каждой транзакции в секундах


def _get_dir_keys(base_dir: str):
    # Путь к src/data
    data_dir = os.path.join(base_dir, "src", "data")  
    # Пути к файлам
    private_keys_file = os.path.join(data_dir, "private_keys.txt")
    return private_keys_file

def _get_dir_proxies(base_dir: str):
    # Путь к src/data
    data_dir = os.path.join(base_dir, "src", "data")  
    # Пути к файлам
    proxies_file = os.path.join(data_dir, "proxies.txt")
    return proxies_file

def read_private_keys(base_dir: str) -> List[str]:
    """Чтение приватных ключей из файла."""
    file_path = _get_dir_keys(base_dir)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} not found.")
    
    with open(file_path, "r") as file:
        private_keys = [line.strip() for line in file if line.strip()]
    
    if not private_keys:
        raise ValueError(f"No private keys found in {file_path}.")
    return private_keys

def read_proxies(base_dir: str) -> List[str]:
    """Чтение прокси из файла."""
    file_path = _get_dir_proxies(base_dir)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} not found.")
    
    with open(file_path, "r") as file:
        proxies = [line.strip() for line in file if line.strip()]
    
    if not proxies:
        return None
    return proxies