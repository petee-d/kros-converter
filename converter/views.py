from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import HttpResponse, HttpRequest, HttpResponseNotAllowed, HttpResponseBadRequest, JsonResponse
from django.shortcuts import render
from django.template import loader

from converter.aggregation import InvoiceAggregator
from converter.export import PohodaExporter
from converter.parser import KrosParser, FormatError


def index(request: HttpRequest):
    return render(request, 'index.html')


def convert(request: HttpRequest):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    if 'file' not in request.FILES:
        return HttpResponseBadRequest('No file was uploaded!')

    file: InMemoryUploadedFile = request.FILES['file']

    try:
        invoice = KrosParser(file).parse()
    except FormatError as e:
        return HttpResponseBadRequest(str(e))

    aggregator = InvoiceAggregator(invoice)

    return JsonResponse({
        'invoice_number': invoice.number,
        'table': loader.render_to_string('output.html', {
            'invoice': invoice,
            'aggregates': aggregator.aggregates,
            'total': aggregator.total,
        }),
        'pohoda_xml': PohodaExporter(invoice).export(),
    })


def health(request: HttpRequest):
    return HttpResponse('ok')
