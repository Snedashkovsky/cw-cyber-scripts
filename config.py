from dotenv import dotenv_values
import ipfshttpclient
from multiaddr import Multiaddr
from cyber_sdk.client.lcd import LCDClient


IPFS_HOST = dotenv_values(".env")['IPFS_HOST']
ipfs_client = ipfshttpclient.connect(addr=Multiaddr(IPFS_HOST))

WALLET_ADDRESS = dotenv_values('.env')['WALLET_ADDRESS']
WALLET_SEED = dotenv_values('.env')['WALLET_SEED']

BASH_TIMEOUT = 20

GRAPHQL_URL = 'https://index.bostrom.cybernode.ai/v1/graphql'

BOSTROM_NODE_RPC_URL = 'https://rpc.bostrom.cybernode.ai:443'
BOSTROM_NODE_LCD_URL = 'https://lcd.bostrom.cybernode.ai/'
BOSTROM_CHAIN_ID = 'bostrom'
BOSTROM_LCD_CLIENT = LCDClient(
    url="https://lcd.bostrom.cybernode.ai/",
    chain_id="bostrom",
)
BASE_COIN_DENOM = 'boot'
