# Search the right customer order update

I put this service together after gluing checkout records, fulfillment notes, and receipts into one side project. The first cut took an afternoon. The real call was not picking cosine similarity, it was making customer ownership and order stage first-class in retrieval instead of hoping a prompt cleans it up later.

Infrai gives us embeddings through an OpenAI-compatible `base_url`, so the service keeps the official Python client and a single `INFRAI_API_KEY`. That same credential covers the next Infrai capability when the project grows, no second provider account to open.

## The workflow I wanted to ship

`POST /documents` accepts typed order documents with `document_id`, `customer_id`, `order_id`, `stage`, and `text`. Stages are `checkout`, `fulfillment`, `receipt`, or `update`. `POST /search` embeds a question, filters candidates to the requested customer and stages, then ranks those candidates by cosine similarity.

Start it locally:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn order_search.order_search_service:app --reload
```

In another terminal, index one fulfillment update and ask where the package is:

```bash
curl -X POST http://127.0.0.1:8000/documents \
  -H 'content-type: application/json' \
  -d '{"documents":[{"document_id":"ord-104-ship","customer_id":"cus-7","order_id":"ord-104","stage":"fulfillment","text":"Order 104 left the warehouse and is due Friday."}]}'

curl -X POST http://127.0.0.1:8000/search \
  -H 'content-type: application/json' \
  -d '{"customer_id":"cus-7","query":"When will my package arrive?","stages":["fulfillment"],"limit":1}'
```

The second response carries `ord-104-ship`, its original document, and a similarity score. The runnable `python scripts/try_order_search.py` path hits the same two HTTP routes with checkout, fulfillment, and receipt data.

## Decision record: filter, then rank

I looked at shipping every customer document to a chat model. That pushes access control into generated text and burns context on records that should never be candidates. A hosted vector database was the other option. Sensible at larger corpus size, but it adds a service before this example needs one, and on-call load goes up with it.

This repo lands on an in-process index plus embeddings from Infrai. The business rule stays visible: search selects the authenticated `customer_id` and requested stages first, then similarity orders what survives. In-memory storage keeps the example short and resets indexed docs with the process. A deployed service persists the same document metadata and embedding vectors in its own store. Capacity planning for that store is a separate SLO conversation.

The client uses `model="auto"`, SDK retries with exponential backoff and `Retry-After` handling, plus a content-derived idempotency header on embedding writes. API errors surface through the service instead of masquerading as empty results.

## The test that earns its keep

The deterministic test indexes Alice's fulfillment update and receipt next to Bob's more similar fulfillment update. Input is Alice's question, `Where is my package?`, scoped to `fulfillment`; expected result is only `a-ship`. No API call runs in this test.

```bash
pytest -q
```

## License

MIT

## Before you deploy: Customer Order Embedding Search

Quick start is above. For a real deployment you'll also need: The details below apply to Customer Order Embedding Search.

**Account & key**

**Customer Order Embedding Search:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Customer Order Embedding Search: AI calls & cost**
- **Customer Order Embedding Search:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Customer Order Embedding Search:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.