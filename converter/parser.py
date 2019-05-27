import codecs
import csv
import io
import re
from collections import OrderedDict
from decimal import Decimal
from typing import Iterable, List, Iterator

from converter.model import InvoiceItem, Invoice

WHITESPACE_RE = re.compile(r'\s', re.UNICODE)


class FormatError(ValueError):
    pass


def convert_decimal(value):
    return Decimal(WHITESPACE_RE.sub('', value).replace(',', '.'))


class KrosParser:
    csv_separator = ';'
    min_columns = 32

    def __init__(self, file):
        raw_data = file.read()
        for encoding in ['utf-8-sig', 'utf-8', 'windows-1250']:
            try:
                data = raw_data.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise FormatError('Nesprávne kódovanie, musí byť UTF-8 alebo Windows 1250')
        try:
            dialect = csv.Sniffer().sniff(data[:1024])
        except Exception:
            raise FormatError('Súbor nie je v korektnom formáte CSV')
        self.reader : Iterator[List[str]] = csv.reader(io.StringIO(data), delimiter=self.csv_separator, dialect=dialect)

    def _expect_col_count(self, row):
        if len(row) < self.min_columns:
            raise FormatError(f'Nesprávny počet stĺpcov, očakáva sa {self.min_columns} alebo viac')

    def _read_row_skipping(self, expected_prefix, expect=False, skip=('', ), column=0):
        while True:
            try:
                row = next(self.reader)
                self._expect_col_count(row)
                if row[column] in skip:
                    continue
                if expect and not row[column].startswith(expected_prefix):
                    raise FormatError(f'V CSV súbore nebola nájdená sekcia "{expected_prefix}" na očakávanom mieste')
                return row
            except StopIteration:
                raise FormatError(f'CSV súbor skončil pred očakávanou sekciou "{expected_prefix}"')

    RE_ZIP_CITY = re.compile(r'^(\d\d\d ?\d\d) +(.+)$')

    def _parse_zip_city(self, zip_with_city: str) -> (str, str):
        match = self.RE_ZIP_CITY.match(zip_with_city)
        if match is None:
            raise FormatError(f'Nepodarilo sa rozpoznať PSČ a mesto "{zip_with_city}"')
        zip_code, city = match.group(1), match.group(2)
        if zip_code[3] != ' ':
            zip_code = zip_code[0:3] + ' ' + zip_code[3:5]
        return zip_code, city

    page_start = 'Strana:'
    supplier_start = 'DODÁVATEĽ:'
    supplier_column = 0
    invoice_number_column = 24

    def _get_invoice_number(self) -> str:
        """Get invoice number, skipping rows before supplier."""
        row = self._read_row_skipping(self.supplier_start, expect=True, skip=('', self.page_start),
                                      column=self.supplier_column)
        return row[self.invoice_number_column]

    order_column = 22
    supplier_company_id_start = 'IČO'
    supplier_company_id_column = 4

    def _read_supplier_and_meta(self, invoice: Invoice):
        row = self._read_row_skipping('názov dodávateľa', skip=('', self.page_start))
        invoice.supplier.name = row[self.supplier_column]

        row = next(self.reader)
        invoice.order = row[self.order_column] or None

        row = next(self.reader)
        invoice.supplier.address.street_and_number = row[self.supplier_column]

        row = next(self.reader)
        invoice.delivery_note = row[self.order_column] or None

        row = next(self.reader)
        invoice.supplier.address.zip, invoice.supplier.address.city = self._parse_zip_city(row[self.supplier_column])

        row = next(self.reader)
        invoice.transfer_type = row[self.order_column].strip() or None

        row = next(self.reader)
        invoice.supplier.address.country = row[self.supplier_column]

        row = next(self.reader)
        invoice.payment.type = row[self.order_column].strip() or None

        row = self._read_row_skipping(self.supplier_company_id_start, expect=True)
        invoice.supplier.company_id = row[self.supplier_company_id_column]

        row = next(self.reader)
        invoice.supplier.tax_id = row[self.supplier_company_id_column] or None

        row = next(self.reader)
        invoice.supplier.vat_id = row[self.supplier_company_id_column] or None

        row = self._read_row_skipping('poznámka o zápise', column=self.supplier_column)
        invoice.supplier.register = row[self.supplier_column]

    issue_date_section_start = 'Dátum vyhotovenia'
    issue_date_section_column = 0
    issue_date_column = 9
    client_name_column = 14
    client_company_id_section_name = 'IČO'
    client_company_id_section_column = 26
    client_company_id_column = 29

    account_number_section_start = 'Číslo účtu:'
    account_number_section_column = 0
    account_number_column = 5
    variable_symbol_section_start = 'VS:'
    variable_symbol_section_column = 10
    variable_symbol_column = 11

    shop_address_section_start = 'Prevádzka'
    shop_address_section_column = 14
    shop_address_column = 19

    def _read_meta_and_client(self, invoice: Invoice):
        row = self._read_row_skipping(self.issue_date_section_start, expect=True, column=self.issue_date_section_column)
        invoice.dates.issue = row[self.issue_date_column]
        if not invoice.dates.issue:
            raise FormatError('Nebol nájdený dátum vyhotovenia na očakávanom mieste')

        row = self._read_row_skipping('dátum dodania', column=self.issue_date_section_column)
        invoice.dates.supply = row[self.issue_date_column]

        row = self._read_row_skipping('názov klienta', column=self.client_name_column)
        invoice.client.name = row[self.client_name_column]

        row = self._read_row_skipping('dátum splatnosti', column=self.issue_date_section_column)
        invoice.dates.due = row[self.issue_date_column]

        row = self._read_row_skipping('adresa klienta', column=self.client_name_column)
        invoice.client.address.street_and_number = row[self.client_name_column]
        if self.client_company_id_section_name not in row[self.client_company_id_section_column]:
            raise FormatError('Sekcia s IČO klienta nebola nájdená na očakávanom mieste')
        invoice.client.company_id = row[self.client_company_id_column]

        row = self._read_row_skipping('adresa klienta', column=self.client_name_column)
        invoice.client.address.zip, invoice.client.address.city  = self._parse_zip_city(row[self.client_name_column])
        invoice.client.tax_id = row[self.client_company_id_column] or None

        row = self._read_row_skipping(self.account_number_section_start, expect=True,
                                      column=self.account_number_section_column)
        invoice.payment.account = row[self.account_number_column]
        if self.variable_symbol_section_start not in row[self.variable_symbol_section_column]:
            raise FormatError('Sekcia s variabilným symbolom nebola nájdená na očakávanom mieste')
        invoice.payment.variable_symbol = row[self.variable_symbol_column]

        row = self._read_row_skipping('adresa klienta', column=self.client_name_column)
        invoice.client.address.country = row[self.client_name_column]
        invoice.client.vat_id = row[self.client_company_id_column] or None

        row = self._read_row_skipping('banka', column=self.account_number_section_column)
        invoice.payment.bank = row[self.account_number_column]

        row = self._read_row_skipping(self.shop_address_section_start, column=self.shop_address_section_column)
        invoice.client.shop_address = row[self.shop_address_column]

        row = self._read_row_skipping('IBAN', column=self.account_number_section_column)
        invoice.payment.iban = row[self.account_number_column]

        row = self._read_row_skipping('SWIFT', column=self.account_number_section_column)
        invoice.payment.swift = row[self.account_number_column]

    items_section_start = 'Faktúrujeme Vám:'
    items_section_column = 0
    items_code_string = 'kombinovanej'
    items_code_column_candidates = [2, 3]
    items_name_column = 7
    items_quantity_column = 17
    items_unit_column = 20
    items_unit_price_column = 23
    items_vat_column = 24
    items_total_no_vat_column = 28
    items_total_column = 31

    def _locate_code_column(self) -> int:
        for row in self.reader:
            self._expect_col_count(row)
            for col in self.items_code_column_candidates:
                if self.items_code_string in row[col]:
                    return col
        else:
            raise FormatError('Nebol nájdený začiatok tabuľky položiek faktúry')

    def _read_items(self) -> Iterable[InvoiceItem]:
        self._read_row_skipping(self.items_section_start, expect=True, column=self.items_section_column)
        col_code = self._locate_code_column()

        for row in self.reader:
            self._expect_col_count(row)
            if not row[self.items_unit_column]:
                break
            yield InvoiceItem(
                code=row[col_code],
                name=row[self.items_name_column],
                quantity=convert_decimal(row[self.items_quantity_column]),
                unit=row[self.items_unit_column],
                unit_price=convert_decimal(row[self.items_unit_price_column]),
                vat=convert_decimal(row[self.items_vat_column]),
                total_no_vat=convert_decimal(row[self.items_total_no_vat_column]),
                total=convert_decimal(row[self.items_total_column]),
            )

    carried_tax_start = 'Prenesenie'
    carried_tax_column = 2
    delivery_to_start = 'Tovar prevzal :'
    delivery_to_column = 0
    issued_by_start = 'Vyhotovil:'
    issued_by_column = 0

    def _read_final_meta(self, invoice: Invoice):
        row = self._read_row_skipping(self.carried_tax_start, expect=True, column=self.carried_tax_column)
        invoice.carrying_tax = row[self.carried_tax_column]

        row = self._read_row_skipping(self.delivery_to_start, expect=True, column=self.delivery_to_column)
        invoice.delivery_to = row[self.delivery_to_column][len(self.delivery_to_start):].strip()

        row = self._read_row_skipping(self.issued_by_start, expect=True, column=self.issued_by_column)
        invoice.issued_by = row[self.issued_by_column][len(self.issued_by_start):].strip()

    def parse(self) -> Invoice:
        invoice = Invoice(number=self._get_invoice_number())
        self._read_supplier_and_meta(invoice)
        self._read_meta_and_client(invoice)
        invoice.items = list(self._read_items())
        self._read_final_meta(invoice)
        return invoice
