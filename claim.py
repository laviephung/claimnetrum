import os
import time
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

RPC_URL = os.getenv("RPC_URL", "https://mainnet.base.org")
PRIVATE_KEYS = [pk.strip() for pk in os.getenv("PRIVATE_KEYS", "").split(",") if pk.strip()]
CLAIM_CONTRACT = os.getenv("CLAIM_CONTRACT")
CLAIM_VALUE_WEI = int(os.getenv("CLAIM_VALUE_WEI", "20000000000000"))  # 0.00002 ETH

if not CLAIM_CONTRACT or not PRIVATE_KEYS:
    print("⚠️ Thiếu CLAIM_CONTRACT hoặc PRIVATE_KEYS trong .env")
    exit(1)

w3 = Web3(Web3.HTTPProvider(RPC_URL))

# ABI tối thiểu
abi = [
    {
        "inputs": [],
        "name": "claimTokens",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "user", "type": "address"},
            {"indexed": False, "name": "amount", "type": "uint256"},
            {"indexed": False, "name": "fee", "type": "uint256"},
        ],
        "name": "TokensClaimed",
        "type": "event",
    },
]

contract = w3.eth.contract(address=Web3.to_checksum_address(CLAIM_CONTRACT), abi=abi)


def claim_for_wallet(pk, idx):
    acct = w3.eth.account.from_key(pk)
    address = acct.address
    print(f"[{idx}] Ví {address} bắt đầu claim...")

    balance = w3.eth.get_balance(address)
    if balance < CLAIM_VALUE_WEI:
        print(f"[{idx}] ❌ Không đủ ETH để trả fee. Balance: {w3.from_wei(balance,'ether')} ETH")
        return

    nonce = w3.eth.get_transaction_count(address)
    tx = contract.functions.claimTokens().build_transaction({
        "from": address,
        "value": CLAIM_VALUE_WEI,
        "nonce": nonce,
        "gas": 200000,   # có thể chỉnh
        "gasPrice": w3.eth.gas_price,
    })

    signed = w3.eth.account.sign_transaction(tx, private_key=pk)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)  # ✅ web3.py v6 dùng raw_transaction
    print(f"[{idx}] ⏳ Gửi tx: {tx_hash.hex()}")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    logs = contract.events.TokensClaimed().process_receipt(receipt)

    if logs:
        ev = logs[0]["args"]
        print(f"[{idx}] ✅ Claim thành công! amount={w3.from_wei(ev['amount'],'ether')} | fee={ev['fee']}")
    else:
        print(f"[{idx}] ⚠️ Tx mined nhưng không thấy event TokensClaimed (có thể ví này đã claim rồi).")


if __name__ == "__main__":
    # Lặp vô hạn, cứ 10 ngày claim lại một lần
    while True:
        print("🔄 Bắt đầu vòng claim...")
        for i, pk in enumerate(PRIVATE_KEYS):
            try:
                claim_for_wallet(pk, i)
                time.sleep(1.5)  # nghỉ nhẹ giữa các ví
            except Exception as e:
                print(f"[{i}] ❌ Lỗi: {e}")

        print("✅ Hoàn tất lượt claim. Chờ 10 ngày để chạy lại...")
        time.sleep(864000)  # ngủ 10 ngày
