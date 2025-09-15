from parsy import regex, seq, string, whitespace


def make_tuple(key, val):
    return (key, val)


padding = (string('\t') | string(' ')).many()
eol = padding << string('\n')
equal = whitespace.many() >> string('=') >> whitespace.many()
semicolon = string(';')
colon = string(':')
singlequote = string("'")
spaceOrTab = whitespace | string('\t')

filetypes = string('MULTI_PHYS_TABLE')
filetype = string('FILE_TYPE') >> equal >> filetypes << semicolon << eol
class_tag = string('CLASS')
part = string('PART')

classes = string('IC') | string('DISCRETE') | string('Discrete') | string('discrete') | string('IO') | string('MECHANICAL') | string('')

part_name = part >> whitespace.many() >> singlequote >> regex("[0-9a-zA-Z-_+]+") << singlequote << eol
class_name = class_tag >> equal >> singlequote.optional() >> classes << singlequote.optional() << spaceOrTab.many()
header = colon >> regex(".+?(?=;)") << semicolon << eol

row = padding >> regex("(?!END_PART).*") << eol
rows = row.many()

end_part = padding >> string('END_PART') << eol
end = padding >> singlequote.optional() >> string('END.') << eol.optional()

key_val = seq(regex("[A-Z_-]+") << equal, regex("[0-9a-zA-Z_| ='\t)(,><-]+") << eol).combine(make_tuple)
