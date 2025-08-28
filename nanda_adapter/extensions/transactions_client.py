import os, requests

TX = os.getenv("TRANSACTIONS_BASE_URL")  # e.g., http://127.0.0.1:8080 or https://tx.your.com
ADDR = os.getenv("WALLET_ADDRESS")
KEY  = os.getenv("WALLET_PRIVATE_KEY")   # demo only

def pay_for_service(service_id: str, qty: int):
    # quote
    q = requests.post(f"{TX}/quote", json={"serviceId": service_id, "qty": qty, "agent": ADDR}).json()
    # invoice
    inv = requests.post(f"{TX}/invoice", json={
        "providerAgentId": "provider-urn-or-id",
        "payerAgentId": "payer-urn-or-id",
        "items": [{"serviceId": service_id, "qty": qty, "price": q["price"]}]
    }).json()
    # pay
    return requests.post(f"{TX}/pay", json={"invoiceId": inv["id"], "privateKey": KEY}).json()