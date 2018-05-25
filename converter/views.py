import os

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import HttpResponse, HttpRequest, HttpResponseNotAllowed, HttpResponseBadRequest
from django.shortcuts import render

from converter.convert import KrosConverter


def index(request: HttpRequest):
    return render(request, 'index.html')


def convert(request: HttpRequest):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    if 'file' not in request.FILES:
        return HttpResponseBadRequest('No file was uploaded!')

    file: InMemoryUploadedFile = request.FILES['file']
    data = KrosConverter(file).convert()
    return render(request, 'output.html', data)


def health(request: HttpRequest):
    return HttpResponse('ok')
