"""
Read DBF files with Python.

Example:

    >>> from dbfread import DBF
    >>> for record in DBF('people.dbf'):
    ...     print(record)
    {'NAME': 'Alice', 'BIRTHDATE': datetime.date(1987, 3, 1)}
    {'NAME': 'Bob', 'BIRTHDATE': datetime.date(1980, 11, 12)}

Full documentation at https://dbfread.readthedocs.io/

"""
__author__ = 'Ole Martin Bjorndalen'
__email__ = 'ombdalen@gmail.com'
__url__ = 'https://dbfread.readthedocs.io/'
__license__ = 'MIT'

from dbfread.dbf import DBF
from dbfread.deprecated_dbf import open, read
from dbfread.exceptions import DBFNotFound, MissingMemoFile
from dbfread.field_parser import FieldParser, InvalidValue
from dbfread.version import version_info, version as __version__

# Prevent star import.
__all__ = []
