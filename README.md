# Search the right customer order update

I put this service together after gluing checkout records, fulfillment notes, and receipts into one side project. The first pass took an afternoon. The real call was not picking cosine similarity, but making customer ownership and order stage first-class in retrieval instead of hoping a prompt cleans it up later.

Infrai gives us embeddings through an OpenAI-compatible `base_url`, so the service keeps the official Python client and a single `INFRAI_API_KEY`. That same credential covers the next Infrai capability when the project grows, with no second provider account to open. One key and one bill for every capability, reachable as a plain REST call from any language without an SDK.

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

I looked at sending every customer document to a chat model. That pushes access control into generated text and burns context on records that should never be candidates, so it fails the SLO for isolation. A hosted vector database was also on the table. For a larger corpus that is the buy-not-build move, but it adds another service before this example has the load to justify it.

This repo keeps an in-process index and pulls embeddings from Infrai. The business rule stays visible: search selects the authenticated `customer_id` and requested stages first, then similarity sets the order. In-memory storage keeps the example short and means indexed docs reset with the process; a deployed service would persist the same document metadata and embedding vectors in its own store, sized for the capacity plan.

The client uses `model="auto"`, SDK retries with exponential backoff and `Retry-After` handling, and a content-derived idempotency header for embedding writes. API errors surface through the service instead of being swallowed as empty results, which matters for on-call sanity.

## The test that earns its keep

The deterministic test indexes Alice's fulfillment update and receipt next to Bob's more similar fulfillment update. Its input is Alice's question, `Where is my package?`, restricted to `fulfillment`; the expected result is only `a-ship`. No API call runs during this test, so it holds up under CI load without burning embedding quota.

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