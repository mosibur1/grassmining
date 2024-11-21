import asyncio
import random
import ssl
import json
import time
import uuid
import requests
import shutil
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent

async def connect_to_wss(socks5_proxy, user_id):
    user_agent = UserAgent(os=['windows', 'macos', 'linux'], browsers='chrome')
    random_user_agent = user_agent.random
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy))
    logger.info(device_id)
    while True:
        try:
            await asyncio.sleep(random.randint(1, 10) / 10)
            custom_headers = {
                "User-Agent": random_user_agent,
            }
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            urilist = ["wss://proxy2.wynd.network:4444/", "wss://proxy2.wynd.network:4650/"]
            uri = random.choice(urilist)
            server_hostname = "proxy2.wynd.network"
            proxy = Proxy.from_url(socks5_proxy)
            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                     extra_headers=custom_headers) as websocket:
                async def send_ping():
                    while True:
                        send_message = json.dumps({
                            "id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}
                        })
                        logger.debug(send_message)
                        await websocket.send(send_message)
                        await asyncio.sleep(5)

                await asyncio.sleep(1)
                asyncio.create_task(send_ping())

                while True:
                    response = await websocket.recv()
                    message = json.loads(response)
                    logger.info(message)
                    if message.get("action") == "AUTH":
                        auth_response = {
                            "id": message["id"],
                            "origin_action": "AUTH",
                            "result": {
                                "browser_id": device_id,
                                "user_id": user_id,
                                "user_agent": custom_headers['User-Agent'],
                                "timestamp": int(time.time()),
                                "device_type": "desktop",
                                "version": "4.28.2",
                            }
                        }
                        logger.debug(auth_response)
                        await websocket.send(json.dumps(auth_response))

                    elif message.get("action") == "PONG":
                        pong_response = {"id": message["id"], "origin_action": "PONG"}
                        logger.debug(pong_response)
                        await websocket.send(json.dumps(pong_response))
        except Exception as e:
            proxy_to_remove = socks5_proxy
            with open('auto_proxies.txt', 'r') as file:
                lines = file.readlines()
            updated_lines = [line for line in lines if line.strip() != proxy_to_remove]
            with open('auto_proxies.txt', 'w') as file:
                file.writelines(updated_lines)
            print(f"Proxy '{proxy_to_remove}' has been removed from the file.")

def fetch_proxies():
    """Fetches proxies from the API and saves them to 'auto_proxies.txt'."""
    api_url = "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=protocolipport&format=text"
    try:
        response = requests.get(api_url, stream=True)
        if response.status_code == 200:
            proxies = response.text.strip().splitlines()
            if proxies:
                with open('auto_proxies.txt', 'w') as f:
                    f.writelines([proxy + '\n' for proxy in proxies])
                print(f"Fetched and saved {len(proxies)} proxies to 'auto_proxies.txt'.")
            else:
                print("No proxies found from the API.")
                return False
        else:
            print(f"Failed to fetch proxies. Status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error fetching proxies: {e}")
        return False
    return True

async def main():
    try:
        with open('user_id.txt', 'r') as f:
            _user_id = f.read().strip()
        if not _user_id:
            print("No user ID found in 'user_id.txt'.")
            return
        print(f"User ID read from file: {_user_id}")
    except FileNotFoundError:
        print("Error: 'user_id.txt' file not found.")
        return

    # Fetch and save proxies to 'auto_proxies.txt'
    if not fetch_proxies():
        print("No proxies available. Exiting script.")
        return

    try:
        with open('auto_proxies.txt', 'r') as file:
            auto_proxy_list = file.read().splitlines()
            if not auto_proxy_list:
                print("No proxies found in 'auto_proxies.txt'. Exiting script.")
                return
            print(f"Proxies read from file: {auto_proxy_list}")
    except FileNotFoundError:
        print("Error: 'auto_proxies.txt' file not found.")
        return

    tasks = [asyncio.ensure_future(connect_to_wss(i, _user_id)) for i in auto_proxy_list]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
