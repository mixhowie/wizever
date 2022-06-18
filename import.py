import logging
import sys
from argparse import ArgumentError

from lib.importer import importers

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)-8s] %(threadName)s - %(message)s')

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
