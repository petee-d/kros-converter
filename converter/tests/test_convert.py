import os

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase


class ViewTest(SimpleTestCase):
    maxDiff = None

    def test_index(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'id="upload"')

    def _test_convert(self, input_csv, expected):
        upload = SimpleUploadedFile('file.csv', input_csv, content_type='text/csv')
        resp = self.client.post('/convert', {'file': upload})
        if resp.status_code != 200:
            print(resp.content.decode('utf-8'))
        self.assertEqual(resp.status_code, 200)
        response_json = resp.json()
        for key in expected:
            self.assertEqual(response_json[key], expected[key])

    @staticmethod
    def _load_file(file_name, encoding=None):
        example_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'examples', file_name)
        with open(example_path, 'r', encoding=encoding) as f:
            return f.read()

    def test_convert_1_utf_8(self):
        self._test_convert(self._load_file('1-input-utf-8.csv', 'utf-8').encode('utf-8'), {
            'invoice_number': '180001',
            'table': self._load_file('1-output-table.html', 'utf-8'),
            'pohoda_xml': self._load_file('1-output-pohoda.xml', 'utf-8'),
        })

    def test_convert_2_windows_1250(self):
        self._test_convert(self._load_file('2-input-windows-1250.csv', 'windows-1250').encode('windows-1250'), {
            'invoice_number': '181234',
            'table': self._load_file('2-output-table.html', 'utf-8'),
            'pohoda_xml': self._load_file('2-output-pohoda.xml', 'utf-8'),
        })

    def test_convert_3_windows_1250(self):
        self._test_convert(self._load_file('3-input-windows-1250.csv', 'windows-1250').encode('windows-1250'), {
            'invoice_number': '190111',
            'table': self._load_file('3-output-table.html', 'utf-8'),
            'pohoda_xml': self._load_file('3-output-pohoda.xml', 'utf-8'),
        })

    def test_convert_error_csv(self):
        upload = SimpleUploadedFile('file.csv', b'a;b;c\n1;2', content_type='text/csv')
        resp = self.client.post('/convert', {'file': upload})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('Súbor nie je v korektnom formáte CSV', resp.content.decode('utf-8'))

    def test_convert_error_columns(self):
        upload = SimpleUploadedFile('file.csv', b'a,b,c\n1,2,3', content_type='text/csv')
        resp = self.client.post('/convert', {'file': upload})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('Nesprávny počet stĺpcov', resp.content.decode('utf-8'))
