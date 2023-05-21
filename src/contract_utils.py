import json
import base58
import hashlib
import pandas as pd
from aiohttp import ClientConnectorError
from ipfshttpclient import Client as IPFSClient
from typing import Optional

from cyber_sdk.client.lcd import LCDClient
from cyber_sdk.client.lcd.api.tx import CreateTxOptions
from cyber_sdk.core import Coins
from cyber_sdk.key.mnemonic import MnemonicKey
from cyber_sdk.core.bank import MsgMultiSend
from cyber_sdk.core.bank.msgs import MultiSendInput, MultiSendOutput
from cyberutils.bash import execute_bash
from cyberutils.contract import execute_contract as execute_contract_cyberutils

from config import NODE_RPC_URL, CHAIN_ID, LCD_CLIENT


def Error_Handler(func):
    def Inner_Function(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except (EOFError, IndexError, KeyError, TimeoutError, ClientConnectorError) as e:
            print(f'Error: {e}')
        except Exception as e:
            print(f'Error: {e}')

    return Inner_Function


def instantiate_contract(init_query: str, contract_code_id: str, contract_label: str,
                         contract_admin: Optional[str] = None, amount: str = '', from_address: str = '$WALLET',
                         display_data: bool = False) -> str:
    _init_output, _init_error = execute_bash(
        f'''INIT='{init_query}' \
            && cyber tx wasm instantiate {contract_code_id} "$INIT" --from={from_address} \
            {'--amount=' + amount + 'boot' if amount else ''} --label="{contract_label}" \
            {'--admin=' + contract_admin if contract_admin else '--no-admin'} \
            -y --gas=3500000 --broadcast-mode=block -o=json --chain-id={CHAIN_ID} --node={NODE_RPC_URL}''',
        shell=True)
    if display_data:
        try:
            print(json.dumps(json.loads(_init_output), indent=4, sort_keys=True))
        except json.JSONDecodeError:
            print(_init_output)
    if _init_error:
        print(_init_error)
    _init_json = json.loads(_init_output)
    return [event['attributes'][0]['value']
            for event in _init_json['logs'][0]['events']
            if event['type'] == 'instantiate'][0]


def execute_contract_bash(execute_query: str, contract_address: str, from_address: str = '$WALLET', gas: int = 300000,
                          display_data: bool = False) -> str:
    _execute_output, _execute_error = execute_bash(
        f'''EXECUTE='{execute_query}' \
            && CONTRACT="{contract_address}" \
            && cyber tx wasm execute $CONTRACT "$EXECUTE" --from={from_address} --broadcast-mode=block -o=json -y \
            --gas={gas} --chain-id={CHAIN_ID} --node={NODE_RPC_URL}''',
        shell=True)
    if display_data:
        try:
            print(json.dumps(json.loads(_execute_output), indent=4, sort_keys=True))
        except json.JSONDecodeError:
            print(_execute_output)
    if _execute_error:
        print(_execute_error)
    return _execute_output


def query_contract(query: str, contract_address: str, display_data: bool = False) -> json:
    _execute_output, _execute_error = execute_bash(
        f'''QUERY='{query}' \
            && cyber query wasm contract-state smart {contract_address} "$QUERY" -o=json \
            --chain-id={CHAIN_ID} --node={NODE_RPC_URL}''',
        shell=True)
    try:
        if display_data:
            print(json.dumps(json.loads(_execute_output), indent=4, sort_keys=True))
        return json.loads(_execute_output)
    except json.JSONDecodeError:
        print(_execute_output)
        if _execute_error:
            print(_execute_error)
        return json.loads(_execute_output)


def instantiate_contract_unsigned_tx(
        init_query: str, contract_code_id: str, contract_label: str, amount: str = '',
        from_address: str = '$WALLET', display_data: bool = False) -> bool:
    tx_file_name = f'txs/code_{contract_code_id}_{contract_label.replace(" ", "_")}.json'
    signed_tx_file_name = f'txs/signed_code_{contract_code_id}_{contract_label.replace(" ", "_")}.json'
    _init_output, _init_error = execute_bash(
        f'''INIT='{init_query}' \
            && cyber tx wasm instantiate {contract_code_id} "$INIT" --from={from_address} \
            --admin={from_address} {'--amount=' + amount + 'boot' if amount else ''} \
            --label="{contract_label}" -y --gas=3500000 --chain-id={CHAIN_ID} --node={NODE_RPC_URL} \
            --generate-only > {tx_file_name}''',
        shell=True)
    print(f'{tx_file_name}'
          f'\n\n\tcyber tx sign {tx_file_name} --from={from_address} '
          f'--output-document={signed_tx_file_name} '
          f'--chain-id={CHAIN_ID} --ledger --node={NODE_RPC_URL}'
          f'\n\n\tcyber tx broadcast {signed_tx_file_name} --chain-id={CHAIN_ID} '
          f'--broadcast-mode=block --node={NODE_RPC_URL}\n')
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


def execute_contract_unsigned_tx(
        execute_query: str, contract_address: str, tx_unsigned_file_name: str, tx_signed_file_name: str,
        from_address: str = '$WALLET', gas: int = 400000, display_data: bool = False) -> str:
    _execute_output, _execute_error = execute_bash(
        f'''EXECUTE='{execute_query}' \
            && CONTRACT="{contract_address}" \
            && cyber tx wasm execute $CONTRACT "$EXECUTE" --from={from_address} -y \
            --gas={gas} --chain-id={CHAIN_ID} --node={NODE_RPC_URL} --generate-only > {tx_unsigned_file_name}''',
        shell=True)
    print(f'{tx_unsigned_file_name}'
          f'\n\n\tcyber tx sign {tx_unsigned_file_name} --from={from_address} '
          f'--output-document={tx_signed_file_name} '
          f'--chain-id={CHAIN_ID} --ledger --node={NODE_RPC_URL}'
          f'\n\n\tcyber tx broadcast {tx_signed_file_name} --chain-id={CHAIN_ID} '
          f'--broadcast-mode=block --node={NODE_RPC_URL}\n')
    if display_data:
        try:
            with open(tx_unsigned_file_name, 'r') as tx_file:
                print(json.dumps(json.loads(tx_file.read()), indent=4, sort_keys=True))
        except json.JSONDecodeError:
            print(_execute_output)
    if _execute_error:
        print(_execute_error)
    return _execute_output


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


def get_proofs(input_file: str,
               output_file: str,
               start_index: int = 1,
               end_index: int = -1) -> bool:
    _root_and_proofs_output, _root_and_proofs_error = execute_bash(
        f'export NODE_OPTIONS=--max_old_space_size=4096 && cd generate_merkle_proofs &&'
        f'yarn start --input ../{input_file} --output ../{output_file} --start_index {start_index} --end_index {end_index}')
    if _root_and_proofs_output:
        print(_root_and_proofs_output)
        return True
    else:
        print(_root_and_proofs_error)
        return False


class ContractUtils:

    def __init__(self, address_dict: dict,
                 lcd_client: LCDClient = LCD_CLIENT, ipfs_client: Optional[IPFSClient] = None):
        self.address_dict = address_dict
        self.name_dict = {v: k for k, v in address_dict.items()}
        self.ipfs_client = ipfs_client
        self.lcd_client = lcd_client

    def set_address_dict(self, address_dict):
        self.address_dict = address_dict
        self.name_dict = {v: k for k, v in address_dict.items()}

    def send_coins(self, from_seed: str, to_addresses: list, amounts: list, gas: int = 70999, denom: str = 'boot',
                   display_data: bool = False) -> str:
        _mk = MnemonicKey(mnemonic=from_seed)
        _wallet = self.lcd_client.wallet(key=_mk)

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
        return self.lcd_client.tx.broadcast(_tx).to_json()

    # def query_contract(self, query_msg: dict, contract_address: str) -> json:
    #     return self.lcd_client.wasm.contract_query(contract_address=contract_address, query_msg=query_msg)

    def execute_contract(self, execute_msg: json, contract_address: str, mnemonic: str,
                         gas: int = 500000, fee_amount: int = 0, fee_denom: str = 'boot',
                         display_data: bool = False) -> str:
        _key = MnemonicKey(mnemonic=mnemonic)
        _wallet = self.lcd_client.wallet(key=_key)
        return execute_contract_cyberutils(
            execute_msgs=[execute_msg], wallet=_wallet, contract_address=contract_address,
            lcd_client=self.lcd_client, gas=gas, fee_amount=fee_amount, fee_denom=fee_denom).to_json()

    def create_passport(self, claim_row: pd.Series, display_data: bool = False):
        return self.execute_contract(
            execute_msg={"create_passport": {"avatar": claim_row["avatar"], "nickname": claim_row["nickname"]}},
            contract_address=self.name_dict['Passport Contract'],
            mnemonic=claim_row['cosmos_seed'],
            gas=500000,
            display_data=display_data)

    def proof_address(self, claim_row: pd.Series, network: str = 'ethereum', display_data: bool = False):
        return self.execute_contract(
            execute_msg={
                "proof_address": {"address": claim_row[network + "_address"], "nickname": claim_row["nickname"],
                                  "signature": claim_row[network + "_message_signature"]}},
            contract_address=self.name_dict['Passport Contract'],
            mnemonic=claim_row['cosmos_seed'],
            gas=400000,
            display_data=display_data)

    def claim(self, claim_row: pd.Series, network: str = 'ethereum', display_data: bool = False):
        return self.execute_contract(
            execute_msg={
                "claim": {"nickname": claim_row['nickname'], "gift_claiming_address": claim_row[network + "_address"],
                          "gift_amount": str(claim_row['amount']), "proof": claim_row[network + "_proof"]}},
            contract_address=self.name_dict['Gift Contract'],
            mnemonic=claim_row['cosmos_seed'],
            gas=500000,
            display_data=display_data)

    def release(self, claim_row: pd.Series, network: str = 'ethereum', display_data: bool = False):
        return self.execute_contract(
            execute_msg={"release": {"gift_address": claim_row[network + "_address"]}},
            contract_address=self.name_dict['Gift Contract'],
            mnemonic=claim_row['cosmos_seed'],
            gas=400000,
            display_data=display_data)

    def transfer_passport(self, claim_row: pd.Series, token_id: str, to_address: str = '', display_data: bool = False):
        if to_address == '':
            to_address = claim_row['bostrom_address']
        return self.execute_contract(
            execute_msg={"transfer_nft": {"recipient": to_address, "token_id": str(token_id)}},
            contract_address=self.name_dict['Passport Contract'],
            mnemonic=claim_row['cosmos_seed'],
            gas=500000,
            display_data=display_data)

    def burn_passport(self, claim_row: pd.Series, token_id: str, display_data: bool = False):
        return self.execute_contract(
            execute_msg={"burn": {"token_id": token_id}},
            contract_address=self.name_dict['Passport Contract'],
            mnemonic=claim_row['cosmos_seed'],
            gas=400000,
            display_data=display_data)

    def update_name(self, claim_row: pd.Series, new_nickname: str, display_data: bool = False):
        return self.execute_contract(
            execute_msg={'update_name': {'new_nickname': new_nickname, 'old_nickname': claim_row['nickname']}},
            contract_address=self.name_dict['Passport Contract'],
            mnemonic=claim_row['cosmos_seed'],
            gas=500000,
            display_data=display_data)

    def update_avatar(self, claim_row: pd.Series, new_avatar: str, display_data: bool = False):
        return self.execute_contract(
            execute_msg={'update_avatar': {'new_avatar': new_avatar, 'nickname': claim_row['nickname']}},
            contract_address=self.name_dict['Passport Contract'],
            mnemonic=claim_row['cosmos_seed'],
            gas=500000,
            display_data=display_data)

    def remove_address(self, claim_row: pd.Series, removed_address: str, display_data: bool = False):
        return self.execute_contract(
            execute_msg={'remove_address': {'address': removed_address, 'nickname': claim_row['nickname']}},
            contract_address=self.name_dict['Passport Contract'],
            mnemonic=claim_row['cosmos_seed'],
            gas=500000,
            display_data=display_data)

    def get_contract_name(self, contract_address: str) -> str:
        try:
            return self.address_dict[contract_address]
        except KeyError:
            return contract_address

    def get_name_from_cid(self, ipfs_hash: str, row: Optional[pd.Series] = None) -> str:
        if row is None or self.ipfs_client is None:
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
