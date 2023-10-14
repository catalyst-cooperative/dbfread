from dbfread.ifiles import ipat, ifnmatch

assert ipat('mixed') == '[Mm][Ii][Xx][Ee][Dd]'
assert ifnmatch('test', 'test') is True
assert ifnmatch('miXEdCaSe', 'mixedcase') is True
assert ifnmatch('CAMELCASE/CamelCase', 'CamelCase/UPPERCASE') is False

# Pattern with
# assert ipat('[A]') == '[[Aa]]'
