import json
import base58
import hashlib
import pandas as pd
from subprocess import Popen, PIPE

from aiohttp import ClientConnectorError
from cyber_sdk.client.lcd import LCDClient
from cyber_sdk.client.lcd.api.tx import CreateTxOptions
from cyber_sdk.core import AccAddress, Coins
from cyber_sdk.core.wasm import MsgExecuteContract
from cyber_sdk.key.mnemonic import MnemonicKey
from cyber_sdk.core.bank import MsgMultiSend
from cyber_sdk.core.bank.msgs import MultiSendInput, MultiSendOutput

NODE_URL = 'https://rpc.bostrom.cybernode.ai:443'
LCD_URL = 'https://lcd.bostrom.cybernode.ai/'
NETWORK = 'bostrom'


def Error_Handler(func):
    def Inner_Function(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except (EOFError, IndexError, KeyError, TimeoutError, ClientConnectorError) as e:
            print(f'Error: {e}')
        except Exception as e:
            print(f'Error: {e}')
    return Inner_Function


def execute_bash(bash_command: str, display_data: bool = False) -> [str, str]:
    _output, _error = Popen(bash_command, shell=True, stdout=PIPE, stderr=PIPE).communicate()
    if _error:
        display_data = True
    if display_data:
        print(bash_command)
        if _output:
            try:
                print(json.dumps(json.loads(_output.decode('utf-8')), indent=4, sort_keys=True))
            except json.JSONDecodeError:
                print(_output)
        if _error:
            print(_error)
    return _output.decode('utf-8'), _error.decode('utf-8')


def instantiate_contract(init_query: str, contract_code_id: str, contract_label: str, amount: str = '',
                         from_address: str = '$WALLET', display_data: bool = False) -> bool:
    tx_file_name = f'txs/code_{contract_code_id}_{contract_label.replace(" ", "_")}.json'
    signed_tx_file_name = f'txs/signed_code_{contract_code_id}_{contract_label.replace(" ", "_")}.json'
    _init_output, _init_error = execute_bash(
        f'''INIT='{init_query}' \
            && cyber tx wasm instantiate {contract_code_id} "$INIT" --from {from_address} \
            --admin {from_address} {'--amount ' + amount + 'boot' if amount else ''} \
            --label "{contract_label}" -y --gas 3500000 --chain-id={NETWORK} --node={NODE_URL} \
            --generate-only > {tx_file_name}''')
    print(f'{tx_file_name}'
          f'\n\n\tcyber tx sign {tx_file_name} --from={from_address} '
          f'--output-document={signed_tx_file_name} '
          f'--chain-id=bostrom --ledger --node {NODE_URL}'
          f'\n\n\tcyber tx broadcast {signed_tx_file_name} --chain-id=bostrom '
          f'--broadcast-mode block --node {NODE_URL}\n')
    if display_data:
        try:
            with open(tx_file_name, 'r') as tx_file:
                print(json.dumps(json.loads(tx_file.read()), indent=4, sort_keys=True))
        except json.JSONDecodeError:
            print(_init_output)
    if _init_error:
        print(_init_error)
        return False
    return True


def execute_contract_bash(execute_query: str, contract_address: str, from_address: str = '$WALLET', gas: int = 300000,
                          action_name: str = 'execute', display_data: bool = False) -> str:
    tx_file_name = f'txs/{contract_address[-4:]}_{action_name}.json'
    signed_tx_file_name = f'txs/signed_{contract_address[-4:]}_{action_name}.json'
    _execute_output, _execute_error = execute_bash(
        f'''EXECUTE='{execute_query}' \
            && CONTRACT="{contract_address}" \
            && cyber tx wasm execute $CONTRACT "$EXECUTE" --from {from_address} -y \
            --gas={gas} --chain-id={NETWORK} --node={NODE_URL} --generate-only > {tx_file_name}''')
    print(f'{tx_file_name}'
          f'\n\n\tcyber tx sign {tx_file_name} --from={from_address} '
          f'--output-document={signed_tx_file_name} '
          f'--chain-id=bostrom --ledger --node {NODE_URL}'
          f'\n\n\tcyber tx broadcast {signed_tx_file_name} --chain-id=bostrom '
          f'--broadcast-mode block --node {NODE_URL}\n')
    if display_data:
        try:
            with open(tx_file_name, 'r') as tx_file:
                print(json.dumps(json.loads(tx_file.read()), indent=4, sort_keys=True))
        except json.JSONDecodeError:
            print(_execute_output)
    if _execute_error:
        print(_execute_error)
    return _execute_output


def query_contract(query: str, contract_address: str, display_data: bool = False) -> json:
    _execute_output, _execute_error = execute_bash(
        f'''QUERY='{query}' \
            && cyber query wasm contract-state smart {contract_address} "$QUERY" -o json \
            --chain-id={NETWORK} --node={NODE_URL}''')
    try:
        if display_data:
            print(json.dumps(json.loads(_execute_output), indent=4, sort_keys=True))
        return json.loads(_execute_output)
    except json.JSONDecodeError:
        print(_execute_output)
        if _execute_error:
            print(_execute_error)
        return json.loads(_execute_output)


def get_ipfs_cid_from_str(source_str: str) -> str:
    """
    Use only for getting valid CIDs.
    Return is incorrect CID.
    :param source_str: string for uploading as file into IPFS
    :return IPFS CID (valid but !incorrect!)"""
    assert type(source_str) == str
    _source_hash = hashlib.sha256(str.encode(source_str)).hexdigest()
    _source_hash_bytes = bytes.fromhex(_source_hash)
    _length = bytes([len(_source_hash_bytes)])
    _hash = b'\x12' + _length + _source_hash_bytes
    return base58.b58encode(_hash).decode('utf-8')


class ContractUtils:

    def __init__(self, ipfs_client, address_dict: dict, url: str = LCD_URL, chain_id: str = NETWORK):
        self.ipfs_client = ipfs_client
        self.address_dict = address_dict
        self.name_dict = {v: k for k, v in address_dict.items()}
        self.bostrom_lcd_client = LCDClient(
            url=url,
            chain_id=chain_id
        )

    def set_address_dict(self, address_dict):
        self.address_dict = address_dict
        self.name_dict = {v: k for k, v in address_dict.items()}

    def send_coins(self, from_seed: str, to_addresses: list, amounts: list, gas: int = 70999, denom: str = 'boot',
                   display_data: bool = False) -> str:
        _mk = MnemonicKey(mnemonic=from_seed)
        _wallet = self.bostrom_lcd_client.wallet(key=_mk)

        _msg = MsgMultiSend(
            inputs=[
                MultiSendInput(address=_wallet.key.acc_address, coins=Coins(boot=_amount))
                for _amount in amounts
            ],
            outputs=[
                MultiSendOutput(address=_to_address, coins=Coins(boot=_amount))
                for _to_address, _amount in zip(to_addresses, amounts)
            ],
        )

        _tx = _wallet.create_and_sign_tx(
            CreateTxOptions(
                msgs=[_msg],
                gas_prices="0.1boot",
                gas=str(gas),
                fee_denoms=["boot"],
            )
        )
        if display_data:
            print(_msg)
            print('\n', _tx)
        return self.bostrom_lcd_client.tx.broadcast(_tx).to_json()

    # def query_contract(self, query_msg: dict, contract_address: str) -> json:
    #     return self.bostrom_lcd_client.wasm.contract_query(contract_address=contract_address, query_msg=query_msg)

    def execute_contract(self, execute_msg: json, contract_address: str, mnemonic: str,
                         gas: int = 500000, gas_price: int = 0, display_data: bool = False) -> str:
        _key = MnemonicKey(mnemonic=mnemonic)
        _wallet = self.bostrom_lcd_client.wallet(key=_key)

        _msg = MsgExecuteContract(
            sender=_wallet.key.acc_address,
            contract=AccAddress(contract_address),
            execute_msg=execute_msg)

        _tx = _wallet.create_and_sign_tx(
            CreateTxOptions(
                msgs=[_msg],
                gas_prices=str(gas_price) + 'boot',
                gas=str(gas)
            )
        )
        if display_data:
            print(_msg)
            print(_tx)
        return self.bostrom_lcd_client.tx.broadcast(_tx).to_json()

    def get_contract_name(self, contract_address: str) -> str:
        try:
            return self.address_dict[contract_address]
        except KeyError:
            return contract_address

    def get_name_from_cid(self, ipfs_hash: str, row=None) -> str:
        if row is None:
            return ipfs_hash
        cid_name_dict = {
            row['avatar']: 'Avatar',
            self.ipfs_client.add_str(row['nickname']): 'Nickname',
            self.ipfs_client.add_str(row['ethereum_address']): 'Ethereum Address',
            self.ipfs_client.add_str(row['cosmos_address']): 'Cosmos Address',
            self.ipfs_client.add_str(row['bostrom_address']): 'Passport Owner Address',
            self.ipfs_client.add_str('cyberhole'): 'cyberhole'}
        try:
            return cid_name_dict[ipfs_hash]
        except KeyError:
            return ipfs_hash

    @Error_Handler
    def parse_contract_execution_json(self, contract_execution_json: str, row=None) -> None:
        print('\nEvents')
        _contract_execution_json = json.loads(contract_execution_json)
        _logs = _contract_execution_json['logs']
        if _logs is None or len(_logs) == 0:
            print(_contract_execution_json['raw_log'])
        else:
            for log_item in _logs:
                for event_item in log_item['events']:
                    print('')
                    if event_item['type'] == 'message':
                        if len(event_item["attributes"]) == 3:
                            print(
                                f'message from {self.get_contract_name(event_item["attributes"][-1]["value"])} '
                                f'{event_item["attributes"][1]["value"]} {event_item["attributes"][0]["value"]}')
                        else:
                            print(event_item)
                    elif event_item['type'] == 'execute':
                        print('execute')
                        for attr_item in event_item["attributes"]:
                            if attr_item["key"] == '_contract_address':
                                print(f'\texecute contract: {self.get_contract_name(attr_item["value"])}')
                            else:
                                print(f'\t{attr_item["key"]}: {self.get_contract_name(attr_item["value"])}')
                    elif event_item['type'] == 'reply':
                        print('reply')
                        for attr_item in event_item["attributes"]:
                            if attr_item["key"] == '_contract_address':
                                print(f'\treply contract: {self.get_contract_name(attr_item["value"])}')
                            else:
                                print(f'\t{attr_item["key"]}: {self.get_contract_name(attr_item["value"])}')
                    elif event_item['type'] == 'cyberlink':
                        print('cyberlinks')
                        for i, attr_item in enumerate(event_item['attributes']):
                            if attr_item['key'] == 'particleFrom':
                                print(
                                    f'\t{self.get_name_from_cid(attr_item["value"], row=row)} -> '
                                    f'{self.get_name_from_cid(event_item["attributes"][i + 1]["value"], row=row)}')
                            elif attr_item['key'] == 'particleTo':
                                pass
                            elif attr_item['key'] == 'neuron':
                                print(f'\tneuron: {self.get_contract_name(attr_item["value"])}\n')
                            else:
                                print(f'\t{attr_item["key"]}: {self.get_contract_name(attr_item["value"])}')
                    elif event_item['type'] == 'coin_received':
                        print('coin received')
                        for attr_item in event_item["attributes"]:
                            print(f'\t{attr_item["key"]}: {self.get_contract_name(attr_item["value"])}')
                    elif event_item['type'] == 'coin_spent':
                        print('coin spent')
                        for attr_item in event_item["attributes"]:
                            print(f'\t{attr_item["key"]}: {self.get_contract_name(attr_item["value"])}')
                    elif event_item['type'] == 'wasm':
                        print('wasm')
                        for attr_item in event_item["attributes"]:
                            if attr_item["key"] == 'amount':
                                print(f'\t{attr_item["key"]}: {int(attr_item["value"]):>,}')
                            else:
                                print(f'\t{attr_item["key"]}: {self.get_contract_name(attr_item["value"])}')
                    elif event_item['type'] == 'transfer':
                        print('transfer')
                        for attr_item in event_item["attributes"]:
                            print(f'\t{attr_item["key"]}: {self.get_contract_name(attr_item["value"])}')
                    else:
                        print(event_item)
        print(f"Gas used: {int(_contract_execution_json['gas_used']):>,}")
        print(f"Tx hash: {_contract_execution_json['txhash']}")
