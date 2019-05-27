from collections import OrderedDict
from decimal import Decimal
from typing import Iterable, List

from converter.model import Invoice, InvoiceItem, InvoiceItemAggregate


class InvoiceAggregator:
    def __init__(self, invoice: Invoice):
        self.aggregates = self._aggregate_items(self.filter_irrelevant(invoice.items))

    @staticmethod
    def filter_irrelevant(items: Iterable[InvoiceItem]) -> Iterable[InvoiceItem]:
        for item in items:
            if not item.code:
                continue
            if item.vat != 0:
                continue
            yield item

    @staticmethod
    def _aggregate_items(items: Iterable[InvoiceItem]) -> List[InvoiceItemAggregate]:
        aggregates = OrderedDict()
        for item in items:
            key = (item.code[0:4], item.unit)
            aggregate = aggregates.setdefault(key, InvoiceItemAggregate(
                code=item.code[0:4],
                quantity=Decimal(0),
                unit=item.unit,
                vat=None,
                total=Decimal(0),
            ))
            aggregate.quantity += item.quantity
            aggregate.total += item.total
        return list(aggregates.values())

    @property
    def total(self) -> Decimal:
        return sum((item.total for item in self.aggregates), Decimal(0))
