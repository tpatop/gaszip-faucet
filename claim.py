import os
import json
import asyncio
import aiohttp
from eth_account import Account
from loguru import logger
from src.utils.config import read_private_keys, read_proxies


async def claim_gas(session: aiohttp.ClientSession, address: str, proxy: str) -> dict:
    """Выполняет GET-запрос для claim газа и возвращает результат."""
    url = f"https://backend.gas.zip/v2/monadEligibility/{address}?claim=true&tier=100"
    
    try:
        async with session.get(url, proxy=f"http://{proxy}" if proxy else None) as response:
            if response.status == 200:
                response_data = await response.text()
                return json.loads(response_data)  # Парсим JSON-ответ
            else:
                logger.error(f"[{address}] ❌ HTTP Error: {response.status}")
                return {"error": f"HTTP Error: {response.status}"}
    except Exception as e:
        logger.exception(f"[{address}] ❌ Request failed: {str(e)}")
        return {"error": f"Request failed: {str(e)}"}


async def main():
    """Основная логика скрипта"""

    # Путь до файла
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Чтение приватных ключей и прокси
    private_keys = read_private_keys(base_dir)
    proxies = read_proxies(base_dir)

    if not proxies:
        proxies = [None] * len(private_keys)  # Дополняем список прокси `None`, если их меньше

    logger.info("🚀 Запуск процесса клейма газа...")

    # Создаем сессию aiohttp
    async with aiohttp.ClientSession() as session:
        # Запуск для каждого аккаунта
        tasks = []
        for account_index, (private_key, proxy) in enumerate(zip(private_keys, proxies)):
            # Получаем адрес из приватного ключа
            address = Account.from_key(private_key).address
            logger.info(f"[Аккаунт {account_index}] 🔍 Проверка возможности клейма ({address})...")

            # Добавляем задачу в список
            tasks.append(claim_gas(session, address, proxy))

        # Выполняем все задачи параллельно
        results = await asyncio.gather(*tasks)

        # Выводим результаты
        for account_index, (private_key, result) in enumerate(zip(private_keys, results)):
            address = Account.from_key(private_key).address
            if "eligibility" in result:
                if result["eligibility"] == "CLAIMED":
                    logger.success(f"[Аккаунт {account_index}] ✅ Gas уже был заклеймен ({address}).")
                else:
                    logger.info(f"[Аккаунт {account_index}] 🟢 Gas еще не был заклеймен ({address}).")
            else:
                logger.error(f"[Аккаунт {account_index}] ❌ Ошибка: {result.get('error', 'Unknown error')} ({address})")

if __name__ == "__main__":
    asyncio.run(main())
