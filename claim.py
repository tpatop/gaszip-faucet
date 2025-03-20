import os
import json
import asyncio
import aiohttp
from eth_account import Account
from loguru import logger
from src.utils.config import read_private_keys, read_proxies


async def claim_gas(session: aiohttp.ClientSession, address: str, proxy: str, tier: int = 100) -> dict:
    """Выполняет GET-запрос для claim газа и возвращает результат."""
    url = f"https://backend.gas.zip/v2/monadEligibility/{address}?claim=true" + (f"&tier={tier}" if tier else "")

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


async def claim_with_fallbacks(session: aiohttp.ClientSession, address: str, proxy: str):
    """
    Запускает процесс клейма газа с поочередным уменьшением tier в случае неудачи.
    """
    tiers = [100, 50, 25, 10, None]  # Последний запрос без tier
    for tier in tiers:
        result = await claim_gas(session, address, proxy, tier)
        
        if "eligibility" in result:
            if result["eligibility"] == "CLAIMED":
                logger.success(f"[{address}] ✅ Gas успешно заклеймен.")
                return result
            else:
                logger.info(f"[{address}] ⚠️ Gas еще не был заклеймен на tier={tier}. Пробуем следующий...")
        else:
            logger.error(f"[{address}] ❌ Ошибка: {result.get('error', 'Unknown error')} на tier={tier}")

    logger.error(f"[{address}] ❌ Не удалось заклеймить gas после всех попыток.")
    return {"error": "All tiers failed"}


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
            tasks.append(claim_with_fallbacks(session, address, proxy))

        # Выполняем все задачи параллельно
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
