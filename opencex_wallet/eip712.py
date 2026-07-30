"""EIP-712 typed data for non-custodial orders."""

from __future__ import annotations

from typing import Any, Dict


def order_typed_data(
    chain_id: int,
    verifying_contract: str,
    sell_token: str,
    buy_token: str,
    sell_amount: str,
    min_buy_amount: str,
    nonce: int,
    expiry: int,
    trader: str,
) -> Dict[str, Any]:
    return {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "Order": [
                {"name": "trader", "type": "address"},
                {"name": "sellToken", "type": "address"},
                {"name": "buyToken", "type": "address"},
                {"name": "sellAmount", "type": "uint256"},
                {"name": "minBuyAmount", "type": "uint256"},
                {"name": "nonce", "type": "uint256"},
                {"name": "expiry", "type": "uint256"},
            ],
        },
        "primaryType": "Order",
        "domain": {
            "name": "OpenCEX",
            "version": "1",
            "chainId": chain_id,
            "verifyingContract": verifying_contract,
        },
        "message": {
            "trader": trader,
            "sellToken": sell_token,
            "buyToken": buy_token,
            "sellAmount": sell_amount,
            "minBuyAmount": min_buy_amount,
            "nonce": nonce,
            "expiry": expiry,
        },
    }


def recover_signer(typed_data: Dict[str, Any], signature: str) -> str:
    from eth_account import Account
    from eth_account.messages import encode_typed_data

    signable = encode_typed_data(full_message=typed_data)
    return Account.recover_message(signable, signature=signature)
