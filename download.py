import logging
import sys
from argparse import ArgumentError

from lib.downloader import downloaders

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)-8s] %(threadName)s - %(message)s')

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('usage: python download.py [downloader_name]')
        print('supported importer:')
        for name in downloaders.keys():
            print('- ' + name)
        sys.exit(0)

    downloader_name = sys.argv[1]
    downloader_clazz = downloaders.get(downloader_name)
    if not downloader_clazz:
        raise ArgumentError(None, 'importer not found: ' + downloader_name)

    downloader = downloader_clazz()
    downloader.run()
