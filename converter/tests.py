import os

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase


EXPECTED_RESPONSE_1 = """
<h3>Pomocná tabuľka výpočtov pre kontrolný výkaz za faktúru 180001:</h3>

<table>
  <thead>
  <tr>
    <th class="header-code">Kód KN</th>
    <th class="header-quantity">Množstvo</th>
    <th class="header-type">Merná jednotka</th>
    <th class="header-total">Suma</th>
  </tr>
  </thead>
  <tbody>
  
  <tr>
    <td class="data-code">7314</td>
    <td class="data-quantity">3</td>
    <td class="data-type">ks</td>
    <td class="data-total">40.08</td>
  </tr>
  
  <tr>
    <td class="data-code">7308</td>
    <td class="data-quantity">20</td>
    <td class="data-type">ks</td>
    <td class="data-total">141.47</td>
  </tr>
  
  <tr>
    <td class="data-code">7314</td>
    <td class="data-quantity">195</td>
    <td class="data-type">bm</td>
    <td class="data-total">301.75</td>
  </tr>
  
  <tr>
    <td class="data-code">7217</td>
    <td class="data-quantity">50</td>
    <td class="data-type">ks</td>
    <td class="data-total">80.90</td>
  </tr>
  
  <tr>
    <td class="data-code">7217</td>
    <td class="data-quantity">50</td>
    <td class="data-type">kg</td>
    <td class="data-total">50.50</td>
  </tr>
  
  </tbody>
  <tfoot>
  <tr>
    <th colspan="3">Celková suma tovarov s prenesenou DP:</th>
    <td class="data-grand-total">614.70</td>
  </tr>
  </tfoot>
</table>
""".strip()


class ViewTest(SimpleTestCase):
    maxDiff = None

    def test_index(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'id="upload"')

    def test_convert(self):
        example_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'examples', 'faktura.csv')
        with open(example_path, 'r', encoding='utf-8') as f:
            upload = SimpleUploadedFile('file.csv', f.read().encode('utf-8'), content_type='text/csv')
        resp = self.client.post('/convert', {'file': upload})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content.decode('utf-8').strip(), EXPECTED_RESPONSE_1)

    def test_convert_error_columns(self):
        upload = SimpleUploadedFile('file.csv', b'a,b,c\n1,2,3', content_type='text/csv')
        resp = self.client.post('/convert', {'file': upload})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('Nesprávny počet stĺpcov', resp.content.decode('utf-8'))
