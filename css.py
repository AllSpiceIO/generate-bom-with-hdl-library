"""
The css module is used to parse Cadence's css files.
"""

import shlex


class CssElement:
    pass


class CssConnection(CssElement):
    x = 0
    y = 0
    name = ""

    def __init__(self, tokens):
        self.x = int(tokens[0])
        self.y = int(tokens[1])
        self.name = tokens[2]

    def onGrid(self):
        return self.x % 10 == 0 and self.y % 10 == 0


class CssProperty(CssElement):
    name = ""
    value = ""

    def __init__(self, tokens):
        self.name = tokens[0]
        self.value = tokens[1]


class CssLine(CssElement):
    pass


class CssX(CssElement):
    pass


class CssEmpty(CssElement):
    pass


class Factory:

    def parseLine(self, line):
        token = shlex.split(line, posix=False)
        if len(token) == 0:
            return CssEmpty()
        elif token[0] == 'C' and len(token) == 11:
            return CssConnection(token[1:])
        elif token[0] == 'X':
            return CssX()
        elif token[0] == 'L' and len(token) == 7:
            return CssLine()
        elif token[0] == 'P' and len(token) == 16:
            return CssProperty(token[1:])
        else:
            return CssEmpty()
