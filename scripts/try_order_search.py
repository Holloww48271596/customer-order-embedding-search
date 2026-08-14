from fastapi.testclient import TestClient

from order_search.order_search_service import app


client = TestClient(app)
documents = [
    {"document_id": "ord-104-checkout", "customer_id": "cus-7", "order_id": "ord-104", "stage": "checkout", "text": "Order 104 was confirmed and paid by card."},
    {"document_id": "ord-104-ship", "customer_id": "cus-7", "order_id": "ord-104", "stage": "fulfillment", "text": "Order 104 left the warehouse and is due Friday."},
    {"document_id": "ord-104-receipt", "customer_id": "cus-7", "order_id": "ord-104", "stage": "receipt", "text": "Receipt for order 104, paid by card."},
]

indexed = client.post("/documents", json={"documents": documents})
indexed.raise_for_status()
result = client.post("/search", json={"customer_id": "cus-7", "query": "When will my package arrive?", "stages": ["fulfillment"], "limit": 1})
result.raise_for_status()
print(result.json())
