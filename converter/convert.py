import codecs
import csv
import io
from collections import OrderedDict
from decimal import Decimal


class FormatError(ValueError):
    pass


def convert_decimal(value):
    return Decimal(value.replace(' ', '').replace(',', '.'))


class KrosConverter:
    csv_separator = ';'
    row_invoice = 24
    table_start = 'kombinovanej'
    row_code = 3
    row_quantity = 17
    row_type = 20
    row_vat = 24
    row_total = 31

    def __init__(self, file):
        data = codecs.EncodedFile(file, 'utf-8').read().decode('utf-8')
        dialect = csv.Sniffer().sniff(data[:1024])
        self.reader = csv.reader(io.StringIO(data), delimiter=self.csv_separator, dialect=dialect)

    def get_invoice_no(self):
        try:
            row = next(self.reader)
        except StopIteration:
            raise FormatError('CSV je prazdne')

        if len(row) != 34:
            raise FormatError('Nespravny pocet stlpcov')
        return row[self.row_invoice]

    def to_data(self):
        for row in self.reader:
            if len(row) != 34:
                raise FormatError('Nespravny pocet stlpcov')
            if self.table_start in row[self.row_code]:
                break
        else:
            raise FormatError('Nebol najdeny zaciatok tabulky poloziek')

        for row in self.reader:
            if len(row) != 34:
                raise FormatError('Nespravny pocet stlpcov')
            if not row[self.row_type]:
                break
            yield {
                'code': row[self.row_code],
                'quantity': convert_decimal(row[self.row_quantity]),
                'type': row[self.row_type],
                'vat': convert_decimal(row[self.row_vat]),
                'total': convert_decimal(row[self.row_total]),
            }

    def filter_irrelevant(self, items):
        for item in items:
            if not item['code']:
                continue
            if item['vat'] != 0:
                continue
            yield item

    def aggregate_items(self, items):
        aggregates = OrderedDict()
        for item in items:
            key = (item['code'][0:4], item['type'])
            aggregate = aggregates.setdefault(key, {
                'code': item['code'][0:4],
                'quantity': Decimal(0),
                'type': item['type'],
                'total': Decimal(0),
            })
            aggregate['quantity'] += item['quantity']
            aggregate['total'] += item['total']
        return aggregates.values()

    def get_total(self, items):
        return sum(item['total'] for item in items)

    def convert(self):
        invoice_no = self.get_invoice_no()
        items = self.to_data()
        aggregates = self.aggregate_items(self.filter_irrelevant(items))
        total = self.get_total(aggregates)
        return {
            'invoice': invoice_no,
            'items': aggregates,
            'total': total,
        }
