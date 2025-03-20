import os
import asyncio
import signal
import random
from src.gaszip import Gaszip
from src.utils.config import Config, read_private_keys, read_proxies

MAX_RETRIES = 5  # Количество повторных попыток в случае ошибки
SEMAPHORE_LIMIT = 10  # Ограничение на количество одновременных транзакций

# Глобальная очередь для хранения статистики
transaction_queue = asyncio.Queue()

async def send_transaction(gaszip, attempt=1):
    """Функция для отправки транзакции с повторными попытками"""
    try:
        await gaszip.random_bridge()
        return True  # Успех
    except Exception as e:
        print(f"Ошибка в транзакции: {e}. Попытка {attempt}/{MAX_RETRIES}")
        if attempt < MAX_RETRIES:
            await asyncio.sleep(2**attempt)  # Экспоненциальная задержка (2, 4, 8... сек)
            return await send_transaction(gaszip, attempt + 1)
        return False  # Провал после всех попыток

async def process_account(account_index, private_key, proxy, semaphore):
    """Функция для обработки аккаунта"""
    print(f"Processing account {account_index}...")

    # Инициализация Gaszip
    gaszip = Gaszip(
        account_index=account_index,
        proxy=proxy,
        private_key=private_key,
        config=Config(),
    )

    # Гарантируем выполнение 100 успешных транзакций
    success_count = 0
    while success_count < Config.TARGET_TX:
        async with semaphore:  # Ограничение числа параллельных запросов
            success = await send_transaction(gaszip)
            if success:
                success_count += 1
                print(f"Аккаунт {account_index}: выполнено {success_count}/{Config.TARGET_TX}")
                await transaction_queue.put((account_index, success_count))

        # Сон между транзакциями (5–10 секунд)
        sleep_time = random.uniform(5, 10)
        print(f"Аккаунт {account_index}: пауза {sleep_time:.2f} сек перед следующей транзакцией...")
        await asyncio.sleep(sleep_time)

async def main():
    # Директория, где находится main.py
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Чтение приватных ключей и прокси
    private_keys = read_private_keys(base_dir)
    proxies = read_proxies(base_dir)

    # Проверка, что количество приватных ключей <= количеству прокси
    if proxies is not None and len(private_keys) > len(proxies):
        raise ValueError("Количество прокси должно быть больше или равно количеству приватных ключей.")

    semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)  # Ограничиваем одновременные транзакции

    # Запуск для каждого аккаунта
    tasks = [
        process_account(account_index, private_key, proxy, semaphore)
        for account_index, (private_key, proxy) in enumerate(zip(private_keys, proxies if proxies else [None] * len(private_keys)))
    ]

    # Запускаем все задачи параллельно
    await asyncio.gather(*tasks)

async def shutdown():
    """Выводит статистику транзакций перед завершением"""
    print("\nВыход... Подсчет завершенных транзакций:")
    
    # Собираем данные из очереди
    transaction_counts = {}
    while not transaction_queue.empty():
        account_index, count = await transaction_queue.get()
        transaction_counts[account_index] = count
    
    # Вывод статистики
    for account_index, count in sorted(transaction_counts.items()):
        print(f"\tАккаунт {account_index}: выполнено {count} транзакций.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n\n\t[!] Принудительное завершение! Ожидаем закрытия активных задач...\n\n\n")
        asyncio.run(shutdown())  # Выводим статистику перед завершением
