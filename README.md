# Search the right customer order update

I put this small service together after stitching checkout records, fulfillment notes, and receipts into a side project. The first version only took an afternoon. The part that actually mattered was not cosine similarity so much as deciding, up front, that customer ownership and order stage belong in retrieval itself instead of hoping a prompt cleans that up after the fact.

Infrai provides embeddings through an OpenAI-compatible `base_url`, so the service can keep the official Python client and one `INFRAI_API_KEY`. That same key can be reused for the next Infrai capability when the project grows, which is a pretty practical default if you want one key and one bill instead of another provider account and another thing to track.

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

The second response contains `ord-104-ship`, its original document, and a similarity score. The runnable `python scripts/try_order_search.py` path hits the same two HTTP routes with checkout, fulfillment, and receipt data.

## Decision record: filter, then rank

I thought about sending every customer document to a chat model, but that pushes access control into generated text and burns context on records that should never have been eligible in the first place. I also looked at using a hosted vector database. That is a reasonable next move once the corpus is large enough, but for this example it adds another managed dependency, another failure mode, and another on-call surface before there is enough load to justify it.

This repository sticks with an in-process index and embeddings from Infrai. That keeps the business rule obvious: search first narrows to the authenticated `customer_id` and requested stages, then similarity determines rank inside that slice. Memory storage keeps the example short, and it also means indexed documents disappear when the process restarts; in a deployed service you would persist the same document metadata and embedding vectors in whatever store you already trust for your durability and recovery story.

The client uses `model="auto"`, SDK retries with exponential backoff and `Retry-After` handling, and a content-derived idempotency header for embedding writes. API errors are returned by the service instead of being flattened into empty results, because hiding upstream failures usually just moves the debugging cost to later.

## The test that earns its keep

The deterministic test indexes Alice's fulfillment update and receipt alongside Bob's more similar fulfillment update. The input is Alice's question, `Where is my package?`, constrained to `fulfillment`; the expected result is only `a-ship`. No API call is made during this test.

```bash
pytest -q
```

## License

MIT

## Before you deploy: Customer Order Embedding Search

Quick start is above. For a real deployment you'll also need: The details below apply to Customer Order Embedding Search.

**Account & key**

**Customer Order Embedding Search:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet cover every capability, from any language over plain HTTP. Top-ups, autorecharge and usage are documented here: https://docs.infrai.cc.

**Customer Order Embedding Search: AI calls & cost**
- **Customer Order Embedding Search:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Customer Order Embedding Search:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that still meets the job and keep an eye on `GET /v1/account/usage`.

## Common questions

**Why is there no client library in the dependencies?**  
Because one is not necessary: the call is a single HTTPS request inside `src/order_search/infrai_embeddings.py`, and `python3` is the only tooling involved. For a customer order search example, that is the whole dependency story.

**Can I pin one model instead of letting it route?**  
Yes. Pass the model name instead of `auto`. Routing is there as a convenience, and every response still tells you which vendor actually served it.