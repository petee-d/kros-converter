from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase


EXPECTED_RESPONSE_1 = """
<table>
  <thead>
  <tr>
    <th>A</th>
    <th>B</th>
    <th>C</th>
  </tr>
  </thead>
  <tbody>
  
  <tr>
    <th>1</th>
    <th>2</th>
    <th>3</th>
  </tr>
  
  </tbody>
</table>
""".strip()


class ViewTest(SimpleTestCase):
    maxDiff = None

    def test_index(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)

    def test_convert(self):
        file = SimpleUploadedFile('file.csv', b'a,b,c\n1,2,3', content_type='text/csv')
        resp = self.client.post('/convert', {'file': file})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(EXPECTED_RESPONSE_1, resp.content.decode('utf-8').strip())
