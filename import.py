# coding: utf8

#!/bin/env python
# coding: 8tf8


from argparse import ArgumentError
import sys

from lib.importer import importers


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('usage: python import.py [importer_name]')
        print('supported importer:')
        for name in importers.keys():
            print('- ' + name)
        sys.exit(0)

    importer_name = sys.argv[1]
    importer_clazz = importers.get(importer_name)
    if not importer_clazz:
        raise ArgumentError(None, 'importer not found: ' + importer_name)

    importer = importer_clazz()
    importer.run()
