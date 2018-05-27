import codecs
import csv
import io
import re
from collections import OrderedDict
from decimal import Decimal


WHITESPACE_RE = re.compile(r'\s', re.UNICODE)


class FormatError(ValueError):
    pass


def convert_decimal(value):
    return Decimal(WHITESPACE_RE.sub('', value).replace(',', '.'))


class KrosConverter:
    csv_separator = ';'
    col_invoice = 24
    table_start = 'kombinovanej'
    col_code = 3
    col_quantity = 17
    col_type = 20
    col_vat = 24
    col_total = 31
    min_columns = 32

    def __init__(self, file):
        raw_data = file.read()
        for encoding in ['utf-8', 'windows-1250']:
            try:
                data = raw_data.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise FormatError('Nesprávne kódovanie, musí byť UTF-8 alebo Windows 1250')
        dialect = csv.Sniffer().sniff(data[:1024])
        self.reader = csv.reader(io.StringIO(data), delimiter=self.csv_separator, dialect=dialect)

    def _expect_col_count(self, row):
        if len(row) < self.min_columns:
            raise FormatError(f'Nesprávny počet stĺpcov, očakáva sa {self.min_columns} alebo viac')

    def get_invoice_no(self):
        try:
            row = next(self.reader)
        except StopIteration:
            raise FormatError('CSV súbor je prázdny')

        self._expect_col_count(row)
        return row[self.col_invoice]

    def to_data(self):
        for row in self.reader:
            self._expect_col_count(row)
            if self.table_start in row[self.col_code]:
                break
        else:
            raise FormatError('Nebol nájdený začiatok tabuľky položiek faktúry')

        for row in self.reader:
            self._expect_col_count(row)
            if not row[self.col_type]:
                break
            yield {
                'code': row[self.col_code],
                'quantity': convert_decimal(row[self.col_quantity]),
                'type': row[self.col_type],
                'vat': convert_decimal(row[self.col_vat]),
                'total': convert_decimal(row[self.col_total]),
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
