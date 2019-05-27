from dataclasses import dataclass, field
from decimal import Decimal
from typing import List


@dataclass
class InvoiceItemAggregate:
    code: str = ''
    quantity: Decimal = Decimal(0)
    unit: str = ''
    vat: Decimal = Decimal(0)
    total: Decimal = Decimal(0)


@dataclass
class InvoiceItem(InvoiceItemAggregate):
    name: str = ''
    unit_price: Decimal = Decimal(0)
    total_no_vat: Decimal = Decimal(0)


@dataclass
class CompanyAddress:
    street_and_number: str = ''
    city: str = ''
    zip: str = ''
    country: str = ''


@dataclass
class Company:
    name: str = ''
    address: CompanyAddress = field(default_factory=CompanyAddress)
    shop_address: List[str] = field(default_factory=list)
    company_id: str = ''
    tax_id: str = ''
    vat_id: str = ''
    register: str = ''


@dataclass
class PaymentInformation:
    type: str = ''
    account: str = ''
    bank: str = ''
    iban: str = ''
    swift: str = ''
    variable_symbol: str = ''


@dataclass
class InvoiceDates:
    issue: str = ''
    supply: str = ''
    due: str = ''


@dataclass
class Invoice:
    number: str = ''
    order: str = ''
    delivery_note: str = ''
    transfer_type: str = ''
    supplier: Company = field(default_factory=Company)
    client: Company = field(default_factory=Company)
    dates: InvoiceDates = field(default_factory=InvoiceDates)
    items: List[InvoiceItem] = field(default_factory=list)
    payment: PaymentInformation = field(default_factory=PaymentInformation)
    total: Decimal = Decimal(0)
    delivery_to: str = ''
    carrying_tax: str = ''
    issued_by: str = ''
