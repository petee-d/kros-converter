import codecs
import csv
import io


class KrosConverter:
    def __init__(self, file):
        data = codecs.EncodedFile(file, 'utf-8').read().decode('utf-8')
        dialect = csv.Sniffer().sniff(data[:1024])
        self.reader = csv.reader(io.StringIO(data), delimiter=',', dialect=dialect)

    def convert(self):
        header = next(self.reader)
        print(header)

        data = []
        for row in self.reader:
            a, b, c = row
            data.append({
                'a': a,
                'b': b,
                'c': c,
            })

        print(data)
        return {
            'rows': data,
        }
