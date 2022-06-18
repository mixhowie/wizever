import abc
import logging
from functools import wraps

importers = {}


def importer(name: str):
    def inner(clazz):
        importers[name] = clazz

        @wraps(clazz)
        def wrapper(*args, **kwargs):
            clazz(*args, **kwargs)

        return wrapper

    return inner


class Importer(abc.ABC):
    @abc.abstractmethod
    def run(self):
        ...


@importer(name='evernote')
class EvernoteImporter(Importer):
    def __init__(self) -> None:
        super().__init__()

    def run(self):
        logging.info('run evernote importer')
