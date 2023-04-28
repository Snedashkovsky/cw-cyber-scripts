import json
from pprint import pprint
from typing import Optional

from cyber_sdk.core.graph import MsgCyberlink
from cyber_sdk.key.mnemonic import MnemonicKey
from cyber_sdk.client.lcd.api.tx import CreateTxOptions, BlockTxBroadcastResult
from cyber_sdk.core.fee import Fee
from cyber_sdk.core import Coin, Coins, AccAddress
from cyber_sdk.exceptions import LCDResponseError
from cyber_sdk.core.wasm import MsgExecuteContract
from cyber_sdk.client.lcd.wallet import Wallet

from config import WALLET_SEED, BOSTROM_LCD_CLIENT, BASE_COIN_DENOM


def create_cls(link_candidates: list[list[str]], account_seed: str = WALLET_SEED, print_message: bool = False,
               min_gas_per_tx: int = 200_000, gas_per_link: int = 40_000, max_gas_per_tx: int = 24_000_000) -> json:
    _key = MnemonicKey(
        mnemonic=account_seed
    )
    _wallet = BOSTROM_LCD_CLIENT.wallet(key=_key)
    _wallet.account_number_and_sequence()

    _msgs = [MsgCyberlink(
        _wallet.key.acc_address,
        link_candidate[0],
        link_candidate[1]
    ) for link_candidate in link_candidates]

    _tx = _wallet.create_and_sign_tx(
        CreateTxOptions(
            msgs=_msgs,
            gas_prices="0boot",
            gas=str(min(min_gas_per_tx + gas_per_link * len(link_candidates), max_gas_per_tx))
        )
    )

    _result = json.loads(BOSTROM_LCD_CLIENT.tx.broadcast(_tx).to_json())
    if print_message:
        pprint(_result)
    return _result


def execute_contract(execute_msgs: list, wallet: Wallet, contract_address: str, gas: int, fee_amount: int,
                     fee_denom: str = BASE_COIN_DENOM, memo: Optional[str] = None) -> Optional[BlockTxBroadcastResult]:

    _create_links_msgs = \
        [MsgExecuteContract(
            sender=wallet.key.acc_address,
            contract=AccAddress(contract_address),
            execute_msg=execute_msg) for execute_msg in execute_msgs]

    _tx_signed = wallet.create_and_sign_tx(
        CreateTxOptions(
            msgs=_create_links_msgs,
            memo=memo,
            fee=Fee(gas, Coins([Coin(amount=fee_amount, denom=fee_denom)]))
        ))

    try:
        _tx_broadcasted = BOSTROM_LCD_CLIENT.tx.broadcast(_tx_signed)
        return _tx_broadcasted

    except LCDResponseError as _e:
        print(f'LCDResponseError: {_e}')
        return None


def create_subgraph_links(link_candidates: list[list[str]], wallet: Wallet, subgraph_contract_address: str,
                          fee_denom: str = BASE_COIN_DENOM, fee_amount: int = 0, memo: Optional[str] = None,
                          gas: int = 5_000_000) -> Optional[BlockTxBroadcastResult]:

    _links = [{"from": _link_candidate[0], "to": _link_candidate[1]} for _link_candidate in link_candidates]
    _execute_msg = {"cyberlink": {"links": _links}}
    return execute_contract(
        execute_msgs=[_execute_msg], wallet=wallet, contract_address=subgraph_contract_address,
        memo=memo, gas=gas, fee_amount=fee_amount, fee_denom=fee_denom)