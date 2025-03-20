from web3 import AsyncWeb3
from eth_account import Account
from typing import Dict, Optional, List, Tuple
import random
import asyncio
from loguru import logger
from src.utils.config import Config
from src.model.gaszip.constants import (
    GASZIP_RPCS, 
    REFUEL_ADDRESS, 
    REFUEL_CALLLDATA,
    GASZIP_EXPLORERS
)

class Gaszip:
    def __init__(
        self,
        account_index: int,
        proxy: str | None,
        private_key: str,
        config: Config,
    ):
        self.account_index = account_index
        self.proxy = self._clean_proxy(proxy) if proxy else None
        self.private_key = private_key
        self.config = config
        self.account = Account.from_key(private_key)
            
    def _clean_proxy(self, proxy: str) -> str:
        """Удаляет 'http://' из прокси, если они уже есть."""
        if proxy.startswith("http://"):
            proxy = proxy[len("http://"):]
        return proxy

    async def get_native_balance(self, network: str) -> float:
        """Get native token balance for a specific network."""
        try:
            # Формирование request_kwargs только если proxy задан
            request_kwargs = {"ssl": False}
            if self.proxy:
                request_kwargs["proxy"] = f"http://{self.proxy}"

            web3 = AsyncWeb3(
                AsyncWeb3.AsyncHTTPProvider(
                    GASZIP_RPCS[network], request_kwargs=request_kwargs
                )
            )
            balance_wei = await web3.eth.get_balance(self.account.address)
            return float(web3.from_wei(balance_wei, "ether"))
        except Exception as e:
            logger.error(f"[{self.account_index}] Failed to get balance for {network}: {str(e)}")
            return 0

    async def get_gas_params(self, web3: AsyncWeb3) -> Dict[str, int]:
        """Get gas parameters for transaction."""
        latest_block = await web3.eth.get_block('latest')
        base_fee = latest_block['baseFeePerGas']
        max_priority_fee = await web3.eth.max_priority_fee
        max_fee = int((base_fee + max_priority_fee) * 1.5)
        
        return {
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": max_priority_fee,
        }

    async def bridge_funds(self, from_network: str, to_network: str, amount: float) -> bool:
        """Bridge funds from one network to another."""
        try:
            # Формирование request_kwargs только если proxy задан
            request_kwargs = {"ssl": False}
            if self.proxy:
                request_kwargs["proxy"] = f"http://{self.proxy}"

            # Получаем Web3 для исходной сети
            web3 = AsyncWeb3(
                AsyncWeb3.AsyncHTTPProvider(
                    GASZIP_RPCS[from_network], request_kwargs=request_kwargs
                )
            )
            
            # Конвертируем сумму в wei
            amount_wei = web3.to_wei(amount, "ether")
            
            # Получаем nonce
            nonce = await web3.eth.get_transaction_count(self.account.address)
            
            # Получаем gas параметры
            gas_params = await self.get_gas_params(web3)
            
            # Создаем транзакцию для моста
            tx = {
                'from': self.account.address,
                'to': REFUEL_ADDRESS,
                'value': amount_wei,
                'data': REFUEL_CALLLDATA[to_network],
                'nonce': nonce,
                'chainId': await web3.eth.chain_id,
                **gas_params
            }
            
            # Оцениваем gas
            gas_estimate = await web3.eth.estimate_gas(tx)
            tx['gas'] = int(gas_estimate * 1.1)  # Добавляем 10% буфер
            
            # Подписываем и отправляем транзакцию
            signed_tx = web3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = await web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            logger.info(f"[{self.account_index}] Waiting for bridge transaction confirmation...")
            receipt = await web3.eth.wait_for_transaction_receipt(tx_hash)
            
            explorer_url = f"{GASZIP_EXPLORERS[from_network]}{tx_hash.hex()}"
            
            if receipt['status'] == 1:
                logger.success(f"[{self.account_index}] Bridge transaction successful! Explorer URL: {explorer_url}")
                return True
            else:
                logger.error(f"[{self.account_index}] Bridge transaction failed! Explorer URL: {explorer_url}")
                return False
                
        except Exception as e:
            logger.error(f"[{self.account_index}] Bridge failed: {str(e)}")
            return False
    
    async def _get_balance(self, from_network, to_network):
        try:
            logger.info(f"[{self.account_index}] Bridging from {from_network} to {to_network}")
            balance = await self.get_native_balance(from_network)
            if balance * 2000 <= 1:
                logger.error(f"[{self.account_index}] Balance is lower in {from_network}. Check another network")
                logger.info(f"[{self.account_index}] Bridging from {to_network} to {from_network}")
                balance = await self.get_native_balance(to_network)
                if balance * 2000 <= 1:
                    logger.error(f"[{self.account_index}] Balance is lower in {to_network}")
                    return False
                else:
                    return balance, to_network, from_network
            return balance, from_network, to_network
        except Exception as e:
            logger.error(f"[{self.account_index}] Bridge failed: {str(e)}")
            return False

        
    async def random_bridge(self) -> bool:
        """Randomly select networks and bridge funds between them."""
        networks = list(GASZIP_RPCS.keys())         

        # Случайным образом выбираем сети для отправки и получения
        from_network, to_network = random.sample(networks, 2)
                
        # Получаем баланс в исходной с заменой, если сеть пуста
        balance, from_network, to_network = await self._get_balance(from_network, to_network)

        if not balance:
            return False
        
        # Определяем сумму для перевода
        if not self.config.BRIDGE_ALL:
            amount = random.uniform(*self.config.AMOUNT_TO_REFUEL)
            if balance * 0.85 <= amount:
                return False
        else:
            amount = balance * 0.85  # Переводим случайную сумму, но оставляем немного на gas
        
        # Выполняем перевод
        for i in range(5):
            tx = await self.bridge_funds(from_network, to_network, amount)
            if tx: return tx