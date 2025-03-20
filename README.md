1. Создать файл src/data/private_keys.txt, формат: 
    0xPRIVATE_KEY_1
    0xPRIVATE_KEY_2
2. Создать файл src/data/proxies.txt, формат:
    http://login:password@ip:port
    login:password@ip:port
    
Прокси должно быть больше приватных ключей, но работает достаточно хорошо и без прокси

Ubuntu:
3. python3 -m venv venv
4. source venv/bin/activate
5. pip install -r requirements.txt
6. python main.py

Windows:
3. install.bat
4. start.bat

в src/utils/config.py есть класс Config:
    1. при выборе "BRIDGE_ALL = True" будут выполнятся транзакции с балансом * 0.85 
    2. при выборе "BRIDGE_ALL = False" будут выполняться транзакции со случайным значением между AMOUNT_TO_REFUEL
