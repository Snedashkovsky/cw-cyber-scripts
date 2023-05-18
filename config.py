from dotenv import dotenv_values

from cyber_sdk.client.lcd import LCDClient


IPFS_HOST = dotenv_values(".env")['IPFS_HOST']

WALLET_ADDRESS = dotenv_values('.env')['WALLET_ADDRESS']
WALLET_SEED = dotenv_values('.env')['WALLET_SEED']

BASH_TIMEOUT = 20

GRAPHQL_URL = 'https://index.bostrom.cybernode.ai/v1/graphql'

NODE_RPC_URL = 'https://rpc.bostrom.cybernode.ai:443'
NODE_LCD_URL = 'https://lcd.bostrom.cybernode.ai/'
CHAIN_ID = 'bostrom'
LCD_CLIENT = LCDClient(url=NODE_LCD_URL, chain_id=CHAIN_ID)
BASE_COIN_DENOM = 'boot'

CYBERLINK_CREATION_QUERY = './src/create_cyberlink.sh'
