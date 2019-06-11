from datetime import datetime
from decimal import Decimal

from lxml import etree
from lxml.builder import ElementMaker

from converter.model import Invoice, Company, InvoiceItem


class BaseExporter:
    def __init__(self, invoice: Invoice):
        self._invoice = invoice

    def export(self) -> str:
        raise NotImplementedError


class PohodaExporter(BaseExporter):
    DAT_NSMAP = {
        'dat': 'http://www.stormware.cz/schema/version_2/data.xsd'
    }
    INV_NSMAP = {
        'typ': 'http://www.stormware.cz/schema/version_2/type.xsd',
        'inv': 'http://www.stormware.cz/schema/version_2/invoice.xsd',
    }

    DAT = ElementMaker(namespace=DAT_NSMAP['dat'], nsmap=DAT_NSMAP)
    INV = ElementMaker(namespace=INV_NSMAP['inv'], nsmap=INV_NSMAP)
    TYP = ElementMaker(namespace=INV_NSMAP['typ'], nsmap=INV_NSMAP)

    def export(self) -> str:
        return etree.tostring(
            self.DAT.dataPack(
                self.DAT.dataPackItem(
                    self._make_invoice(),
                    version='2.0',
                    id='Usr01 (001)',
                ),
                version='2.0',
                id="Usr01",
                ico=self._invoice.supplier.company_id,
                key="66d62ac0-293d-42ee-b61a-d9347c5f7567",
                programVersion="12108.3 (3.5.2019)",
                application="Transformace",
                note="Užívateľský export",
            ),
            encoding='utf-8', pretty_print=True, xml_declaration='<?xml version="1.0" encoding="UTF-8"?>'
        ).decode('utf-8')

    def _make_invoice(self):
        return self.INV.invoice(
            self._make_header(),
            self.INV.invoiceDetail(
                *(self._make_invoice_item(item) for item in self._invoice.items),
            ),
            self._make_summary(),
            version="2.0",
        )

    def _make_header(self):
        return self.INV.invoiceHeader(
            self.INV.invoiceType('issuedInvoice'),
            self.INV.number(
                self.TYP.numberRequested(self._invoice.number),
            ),
            self.INV.symVar(self._invoice.payment.variable_symbol),
            self.INV.date(self._convert_date(self._invoice.dates.issue)),
            self.INV.dateTax(self._convert_date(self._invoice.dates.supply)),
            self.INV.dateAccounting(self._convert_date(self._invoice.dates.supply)),
            self.INV.dateDue(self._convert_date(self._invoice.dates.due)),
            self.INV.accounting(
                self.TYP.ids('311/604'),
            ),
            self.INV.classificationVAT(
                self.TYP.ids('UDpdp'),
            ),
            self.INV.classificationKVDPH(
                self.TYP.ids('A2CN'),
            ),
            self.INV.text('Faktúrujeme Vám:'),
            self.INV.partnerIdentity(
                self._make_company(self._invoice.client),
                self.TYP.shipToAddress(
                    self.TYP.company(),
                    self.TYP.city(),
                    self.TYP.street(),
                ),
                                ),
            self.INV.myIdentity(
                self._make_company(self._invoice.supplier),
            ),
            self._make_payment_method(),
            self._make_bank_account(),
            self.INV.symConst('0308'),
            self.INV.liquidation(
                self.TYP.amountHome(str(sum((item.total for item in self._invoice.items), Decimal(0)))),
            ),
            self.INV.markRecord('true'),
        )

    @staticmethod
    def _convert_date(date_string):
        try:
            return datetime.strptime(date_string, '%d.%m.%Y').date().isoformat()
        except ValueError:
            return date_string

    def _make_company(self, company: Company):
        return self.TYP.address(
            self.TYP.company(company.name),
            self.TYP.city(company.address.city),
            self.TYP.street(company.address.street_and_number),
            self.TYP.zip(company.address.zip),
            self.TYP.ico(company.company_id),
            self.TYP.dic(company.tax_id),
            self.TYP.icDph(company.vat_id),
        )

    def _make_payment_method(self):
        if 'príkaz' in self._invoice.payment.type.lower():
            ids, typ = 'Príkazom', 'draft'
        elif 'hotovos' in self._invoice.payment.type.lower():
            ids, typ = 'V hotovosti', 'cash'
        elif 'Plat.kartou' in self._invoice.payment.type.lower():
            ids, typ = 'V hotovosti', 'creditcard'
        else:
            ids, typ = self._invoice.payment.type, self._invoice.payment.type
        return self.INV.paymentType(
            self.TYP.ids(ids),
            self.TYP.paymentType(typ),
        )

    def _make_bank_account(self):
        bank, account = self._invoice.payment.bank, self._invoice.payment.account
        if account.endswith(' / 8330'):
            bank = 'FIO'
            account = account[:-len(' / 8330')]
        return self.INV.account(
            self.TYP.ids(bank),
            self.TYP.accountNo(account),
        )

    def _make_invoice_item(self, item: InvoiceItem):
        if item.vat == 0:
            vat_type = 'none'
        elif item.vat == 10:
            vat_type = 'low'
        elif item.vat == 20:
            vat_type = 'high'
        else:
            raise ValueError(f'Neznáma sadzba DPH {item.vat} v položke {item.name}')

        if vat_type == 'none':
            args = (
                self.INV.classificationKVDPH(self.TYP.ids('A2CN')),
                self.INV.PDP('true'),
                self.INV.CodePDP(item.code[:4]),
            )
        else:
            args = (
                self.INV.classificationVAT(self.TYP.ids('UD')),
                self.INV.classificationKVDPH(self.TYP.ids('A1')),
                self.INV.PDP('false'),
            )

        unit = 'm' if item.unit == 'bm' else item.unit

        return self.INV.invoiceItem(
            self.INV.text(item.name),
            self.INV.quantity(str(item.quantity)),
            self.INV.unit(unit),
            self.INV.coefficient('1.0'),
            self.INV.payVAT('false'),
            self.INV.rateVAT(vat_type),
            self.INV.discountPercentage('0.0'),
            self.INV.homeCurrency(
                self.TYP.unitPrice(str(item.unit_price)),
                self.TYP.price(str(item.total_no_vat)),
                self.TYP.priceVAT(str(item.total - item.total_no_vat)),
                self.TYP.priceSum(str(item.total)),
            ),
            self.INV.foreignCurrency(
                self.TYP.unitPrice('0'),
                self.TYP.price('0'),
                self.TYP.priceVAT('0'),
                self.TYP.priceSum('0'),
            ),
            self.INV.code(item.code),
            *args,
        )

    def _make_summary(self):
        no_vat_total = sum((item.total for item in self._invoice.items if item.vat == 0), Decimal(0))
        low_vat_total_no_vat = sum((item.total_no_vat for item in self._invoice.items if item.vat == 10), Decimal(0))
        low_vat_total = sum((item.total for item in self._invoice.items if item.vat == 10), Decimal(0))
        high_vat_total_no_vat = sum((item.total_no_vat for item in self._invoice.items if item.vat == 20), Decimal(0))
        high_vat_total = sum((item.total for item in self._invoice.items if item.vat == 20), Decimal(0))
        return self.INV.invoiceSummary(
            self.INV.roundingDocument('none'),
            self.INV.roundingVAT('noneEveryRate'),
            self.INV.homeCurrency(
                self.TYP.priceNone(str(no_vat_total)),
                self.TYP.priceLow(str(low_vat_total_no_vat)),
                self.TYP.priceLowVAT(str(low_vat_total - low_vat_total_no_vat)),
                self.TYP.priceLowSum(str(low_vat_total)),
                self.TYP.priceHigh(str(high_vat_total_no_vat)),
                self.TYP.priceHighVAT(str(high_vat_total - high_vat_total_no_vat)),
                self.TYP.priceHighSum(str(high_vat_total)),
                self.TYP.price3('0'),
                self.TYP.price3VAT('0'),
                self.TYP.price3Sum('0'),
                self.TYP.round(
                    self.TYP.priceRound('0'),
                ),
            ),
        )
