from types import SimpleNamespace

from order_search.infrai_embeddings import InfraiEmbedder
from order_search.order_documents import (
    CustomerOrderIndex,
    OrderDocument,
    OrderStage,
    SearchRequest,
)


class FixedEmbedder:
    vectors = {
        "Where is my package?": [1.0, 0.0],
        "Order A12 left the warehouse and arrives Friday.": [0.9, 0.1],
        "Receipt for order A12: paid by card.": [0.0, 1.0],
        "Order B77 left the warehouse and arrives Thursday.": [1.0, 0.0],
    }

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self.vectors[text] for text in texts]


def test_infrai_embeddings_follow_input_indexes() -> None:
    embedder = InfraiEmbedder.__new__(InfraiEmbedder)
    embedder._client = SimpleNamespace(
        embeddings=SimpleNamespace(
            create=lambda **_kwargs: SimpleNamespace(
                data=[
                    SimpleNamespace(index=1, embedding=[0.0, 1.0]),
                    SimpleNamespace(index=0, embedding=[1.0, 0.0]),
                ]
            )
        )
    )

    assert embedder.embed(["first", "second"]) == [[1.0, 0.0], [0.0, 1.0]]


def test_search_keeps_an_order_update_private_and_stage_specific() -> None:
    index = CustomerOrderIndex(FixedEmbedder())
    index.add(
        [
            OrderDocument(document_id="a-ship", customer_id="alice", order_id="A12", stage=OrderStage.FULFILLMENT, text="Order A12 left the warehouse and arrives Friday."),
            OrderDocument(document_id="a-receipt", customer_id="alice", order_id="A12", stage=OrderStage.RECEIPT, text="Receipt for order A12: paid by card."),
            OrderDocument(document_id="b-ship", customer_id="bob", order_id="B77", stage=OrderStage.FULFILLMENT, text="Order B77 left the warehouse and arrives Thursday."),
        ]
    )

    hits = index.search(SearchRequest(customer_id="alice", query="Where is my package?", stages=[OrderStage.FULFILLMENT]))

    assert [hit.document.document_id for hit in hits] == ["a-ship"]
