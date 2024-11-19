import re
import json
from collections import OrderedDict
from kivy.compat import PY2

_register = OrderedDict()

if not PY2: unichr = chr

def create_fontdict_file(css_fname, output_fname, prefix='fa-'):
    with open(css_fname, 'r') as f:
        data = f.read()
        res = _parse(data, prefix)
        with open(output_fname, 'w') as o:
            print('ici')
            for key, value in res.items():
                print('>>>', key)
                o.write(f'{key}={value}\r\n')
        return res

def _parse(data, prefix):
    pat_start = re.compile('}.+content:', re.DOTALL)
    rules_start = [x for x in re.finditer(pat_start, data)][0].start()
    data = data[rules_start:]
    data = data.replace("\\", '0x')
    data = data.replace("'", '"')
    pat_keys = re.compile('[a-zA-Z0-9_-]+:before')
    res = dict()
    for i in re.finditer(pat_keys, data):
        start = i.start()
        end = data.find('}', start)
        key = i.group().replace(':before', '').replace(prefix, '')
        try:
            value = data[start:end].split('"')[1].encode('unicode_escape')
        except (IndexError, ValueError):
            continue
        res[key] = value
        print(f'{key}={value}')
    return res

create_fontdict_file('hugeicons.css', 'hugeicons.map', 'hgi-')