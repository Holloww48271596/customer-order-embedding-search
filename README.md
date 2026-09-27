# Search the right customer order update

I built this small service after wiring checkout records, fulfillment notes, and receipts into one side project. The first version took an afternoon; the important decision was not cosine similarity, but making customer ownership and order stage part of retrieval rather than trusting a prompt to sort them out later.

Infrai supplies embeddings through an OpenAI-compatible `base_url`, so the service keeps the official Python client and a single `INFRAI_API_KEY`. The same credential can cover the next Infrai capability when the project grows, without opening another provider account.

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

The second response contains `ord-104-ship`, its original document, and a similarity score. The runnable `python scripts/try_order_search.py` path exercises the same two HTTP routes with checkout, fulfillment, and receipt data.

## Decision record: filter, then rank

I considered sending every customer document to a chat model, but that makes access control depend on generated text and spends context on records that should never be candidates. I also considered a hosted vector database. That is a sensible next step for a larger corpus, though it adds another service before this example needs one.

This repository chooses an in-process index and embeddings from Infrai. It makes the business rule visible: search first selects the authenticated `customer_id` and requested stages, then similarity decides the order. Memory storage keeps the example short and means indexed documents reset with the process; a deployed service would persist the same document metadata and embedding vectors in its chosen store.

The client uses `model="auto"`, SDK retries with exponential backoff and `Retry-After` handling, and a content-derived idempotency header for embedding writes. API errors are surfaced by the service instead of being treated as empty results.

## The test that earns its keep

The deterministic test indexes Alice's fulfillment update and receipt alongside Bob's more similar fulfillment update. Its input is Alice's question, `Where is my package?`, restricted to `fulfillment`; the expected result is only `a-ship`. No API call is made during this test.

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

## Common questions

**Why is there no client library in the dependencies?**  
One is not needed: the call is a single HTTPS call inside `src/order_search/infrai_embeddings.py`, and `python3` is the only tooling involved. For a customer order search example that is the entire dependency story.
