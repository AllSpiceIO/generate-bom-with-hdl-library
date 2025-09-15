from parsy import seq, ParseError
import logging
from combinators import part_name, class_name, header, rows, end_part, end, key_val, filetype
import os
import re
from dataclasses import dataclass

def sanitize_lines(lines: list[str]) -> list[str]:
    # if the line doesn't start by { the whole line is not a comment
    # thus, remove only what's in between {} to prevent from misclassifying as comment.
    lines = [re.sub(r"\{[^}]*\}", "", line) if not re.match(r"^\s*{.*?$", line) else line for line in lines]
    return list(filter(lambda line: not (_is_blank(line) or _is_comment(line)), lines))

def _is_blank(line) -> bool:
    return 0 == len(line.strip())

def _is_comment(line) -> bool:
    return re.match("^\\s*{.*?$", line) or re.match("^.*?}\\s*$", line)

class Header:
    def __init__(self, keys: list[str], derived: list[str] = []):
        self.keyProperties = []
        self.derivedProperties = []

        self._defineProperties(keys, derived)

    def _sanitize(self, value: str) -> str:
        return value.split(":")[0].strip(" '\"")

    def _defineProperties(self, keys, derived) -> None:
        for column in keys:
            column = self._sanitize(column)
            columnMatch = re.search(r"(.*)(\(OPT.*)", column)
            if columnMatch:
                self.keyProperties.append(ColumnHeader(column=columnMatch.group(1), optional=columnMatch.group(2)))
            else:
                self.keyProperties.append(ColumnHeader(column=column))
        for column in derived:
            self.derivedProperties.append(ColumnHeader(column=self._sanitize(column)))

    def appendFixProperties(self) -> None: #TODO: not sure how to approach this case
        fixedProperties = ['DESCRIPTION', 'AML', 'MANUFACTURER','STATUS', 'ORACLE_LINK']
        for prop in fixedProperties:
            if prop not in self.getValuesDerivedProperties():
                self.derivedProperties.append(ColumnHeader(column=prop))

    def __str__(self):
        return " | ".join(self.getValuesProperties())

    def assignPadding(self, max_padding: list[str]):
        for index, prop in enumerate(self.properties):
            prop.padding = max_padding[index] - len(str(prop))

    def format(self):
        keyschunk = " | ".join([prop.format() for prop in self.keyProperties])
        derivedchunk = " | ".join([prop.format() for prop in self.derivedProperties])

        return ": " + keyschunk + "= " + derivedchunk + ";"

    @property
    def properties(self)->list:
        return self.keyProperties + self.derivedProperties
    @property
    def numKeyProperties(self) -> int:
        return len(self.keyProperties)

    @property
    def numDerivedProperties(self) -> int:
        return len(self.derivedProperties)

    @property
    def numProperties(self) -> int:
        return self.numKeyProperties + self.keyProperties

    def getValuesProperties(self)-> list[str]:
        return [str(prop) for prop in self.properties]

    def getValuesKeyProperties(self)-> list[str]:
        return [str(prop) for prop in self.keyProperties]

    def getValuesDerivedProperties(self)-> list[str]:
        return [str(prop) for prop in self.derivedProperties]

class Row:
    def __init__(self, rowRaw: str, header: Header):
        self.keyProperties = []
        self.derivedProperties = []
        self.nameSpec = ''

        self._defineProperties(rowRaw, header)

    def _sanitize(self, value: str) -> str:
        """
        Cleans up string by removing extra properties (after :),
        and unwanted characters.
        """
        value = re.split(r'(?<!https):', value)[0]
        value = value.strip(" \"")
        value = re.sub(r"(?<!')\t(?!')", '', value) #re.sub(r'\t', '', value)
        return value

    def _defineProperties(self, row, header: Header):
        """
        Split row by the = symbol:
            - keyProperties (on the left of the row)
            - derivedProperties (on the right)
        Then,
        split by pipe symbol |. Each element is a property.
        Contemplate nameSpec, which is in the last element of keyProperties.
        """
        rowSplit = re.split(r'=', row, maxsplit=1) # splits ONLY the first appearance
        keys = re.split(r'\|', rowSplit[0])
        derived = []

        if len(rowSplit) > 1:
            derived = re.split(r'\|', rowSplit[1])

        if len(keys) == header.numKeyProperties and len(derived) == header.numDerivedProperties:
            for i, prop in enumerate(keys):
                self.keyProperties.append(ColumnRow(column=header.keyProperties[i].column,
                                                    value=self._sanitize(prop)))

            for i, prop in enumerate(derived):
                self.derivedProperties.append(ColumnRow(column=header.derivedProperties[i].column,
                                                    value=self._sanitize(prop)))
            # How to extract the namespec:
            # Cases:
            # 1. 'DEF' (~CON6P_1R2M-HEADER,5284426,Y)
            # 2. 'DEF' (!)
            # Matching patterns:
            # ('.*?') --> '....'
            # \s* --> none or spaces
            # (\(.*\)) --> '(....)'
            matchNameSpec = re.search(r"(.*?)\s*(\(.*\))", self.keyProperties[-1].value)
            if matchNameSpec:
                self.keyProperties[-1].value = matchNameSpec.group(1)
                self.nameSpec = matchNameSpec.group(2)

        else:
            raise Exception("Number of properties in header don't match the number of properties in the row: \n" \
                f"Header: {header.keyProperties} = {header.derivedProperties} \n" \
                f"Row: {keys} = {derived}")

    def editProperty(self, nameProperty: str, newValue: str) -> None:
        """
        using "in" instead of == due to cases such as: PART_NUMBER (OPT)
        if searching PART_NUMBER, with == it wouldn't find it due to the space in between
        the column name and the optional value.
        """
        for prop in self.properties:
            if nameProperty in prop.column:
                prop.value = newValue
                return

    def containsValue(self, value: str)->bool:
        value = value.upper()
        for prop in self.properties:
            if value in prop.value.upper():
                return True
        return False

    def getProperty(self, nameProperty: str) -> str:
        nameProperty = nameProperty.upper()
        for prop in self.properties:
            if nameProperty in prop.column.upper():
                return prop.value
        return ''

    def appendFixProperties(self) -> None:
        fixedProperties = ['DESCRIPTION', 'AML', 'MANUFACTURER', 'STATUS', 'ORACLE_LINK']
        columns = [derivedProp.column for derivedProp in self.derivedProperties]
        for prop in fixedProperties:
            if prop not in columns:
                self.derivedProperties.append(ColumnRow(prop, "''"))

    def getValuesProperties(self)->list[str]:
        return [str(prop) for prop in self.properties]

    def getValuesKeyProperties(self)->list[str]:
        return [str(prop) for prop in self.keyProperties]

    def getValuesDerivedProperties(self)->list[str]:
        return [str(prop) for prop in self.derivedProperties]

    def assignPadding(self, max_padding: list[str])-> None:
        for index, prop in enumerate(self.properties):
            prop.padding = max_padding[index] - len(prop.value)

    def format(self) -> None:
        keyschunk = " | ".join([prop.format() for prop in self.keyProperties])
        derivedchunk = " | ".join([prop.format() for prop in self.derivedProperties])

        if self.nameSpec:
            return " "*2 + keyschunk[:-len(self.nameSpec)] + self.nameSpec + "= " + derivedchunk
        else:
            return " "*2 + keyschunk + " (!)= " + derivedchunk

    @property
    def properties(self)->list:
        return self.keyProperties + self.derivedProperties

    @property
    def partNumber(self):
        return self.getProperty("PART_NUMBER").replace("'","")

    @property
    def numProperties(self):
        return len(self.properties)

    @property
    def numKeyProperties(self):
        return len(self.keyProperties)

    def __str__(self):
        keysToString = " | ".join(self.getValuesKeyProperties())
        derivedToString = " | ".join(self.getValuesDerivedProperties())
        return keysToString + " = " + derivedToString

@dataclass
class ColumnHeader:
    column: str
    optional: str = ""
    padding: int = 0

    def __str__(self) -> str:
        if self.optional:
            return f"{self.column}{self.optional}"
        else:
            return f"{self.column}"

    def format(self) -> str:
        return self.__str__() + " " * self.padding

@dataclass
class ColumnRow:
    column: str
    value: str
    padding: int = 0

    def __str__(self):
        return self.value

    def format(self):
        return self.__str__() + " " * self.padding

class PartTable:
    def __init__(self, name: str, class_type: str, header: Header, rows: list[str]):
        self.name = name
        self.class_type = class_type
        self.header = header

        try:
            self.rows = [Row(row, self.header) for row in rows]
        except Exception as e:
            logging.error(f"Error in PartTable: {self.class_type} - {self.name} -> {e}")
            os._exit(-1)

    def format(self):
        padding = self.calculate_max_padding()

        self.header.assignPadding(padding)
        for row in self.rows:
            row.assignPadding(padding)

        part_line = "PART '" + self.name + "'\n"
        class_line = "CLASS=" + self.class_type + "\n"

        header_line = self.header.format() + "\n"
        decorator = "{" + "="*88 + "}\n"

        result = ["\n", part_line, class_line, "\n", decorator, header_line, decorator]
        result.extend([row.format() + "\n" for row in self.rows])
        result.append("\nEND_PART\n")

        return result

    def calculate_max_padding(self):
        max_characters = [len(prop) for prop in self.header.getValuesProperties()]

        for row in self.rows:
            nameSpecPos = row.numKeyProperties - 1
            nameSpec_padding = len(row.nameSpec) + 1 # space between last keyProperty and the nameSpecification
            for index, rowProp in enumerate(row.getValuesProperties()):
                if index == nameSpecPos and nameSpec_padding > 1:
                    max_characters[index] = max(max_characters[index], len(str(rowProp)) + nameSpec_padding)
                else:
                    max_characters[index] = max(max_characters[index], len(str(rowProp)))
        return max_characters

    def build_multi(name: str, class_type: str, headerRaw: str, rows: list[str]):
        headerSplit = re.split(r'(?<!OPT)=', headerRaw)  # split by = only if not preceeded by OPT

        keys = headerSplit[0].split('|')
        derived = headerSplit[1].split('|')

        header = Header(keys, derived)
        return PartTable(name, class_type, header, rows)

    def build_single(name: str, class_type: str, key_vals):
        keys = []
        vals = []

        for key_val in key_vals:
            keys.append(key_val[0])
            vals.append(key_val[1])

        header = Header(keys)

        return PartTable(name, class_type, header, ["|".join(vals)])

    def search(self, value: str): # generator returns a collection of Row class instances
        for row in self.rows:
            if row.containsValue(value):
                yield row

    def find_similar(self) -> list[list[str]]:
        """
        Looks for entries that have all the fields identical but the part number.
        Return one instance for each duplicate found.
        """
        duplicates = []
        existing = set()

        for row in self.rows:
            if row.partNumber:
                row_no_part_number = [str(prop) for prop in row.properties if prop.column != "PART_NUMBER"]
                row_str = ' | '.join(row_no_part_number)
            else:
                row_str = str(row)

            if row_str in existing:
                duplicates.append(row)
                logging.debug("Row data: "+row_str)
            else:
                existing.add(row_str)
        return duplicates

    def find_duplicates(self) -> list[list[str]]:
        """
        Looks for duplicate entries in the part table.
        Return one instance for each duplicate found.
        """
        duplicates = []
        existing = set()
        for row in self.rows:
            row_str = str(row)
            logging.debug("Row data: "+row_str)
            if row_str in existing:
                duplicates.append(row)
            else:
                existing.add(row_str)

        return duplicates

    def find_repeated_partnumbers(self):
        repeated = []
        existing = set()

        for pn in self.part_numbers:
            if pn != "NONE" and pn != "NaN":
                if pn in existing:
                    repeated.append(pn)
                else:
                    existing.add(pn)

        return repeated

    @property
    def part_numbers(self) -> list[str]:
        return [row.partNumber for row in self.rows]
    @property
    def jedec_types(self) -> list[str]:
        return [row.getProperty("JEDEC_TYPE") for row in self.rows]

class PartTableFile:
    path = ""
    def __init__(self, filetype, partTables):
        self.filetype = filetype
        self.partTables = partTables
        self.format()

    def format(self):
        file_line = "FILE_TYPE = " + self.filetype + ";\n"
        result = [file_line]
        result.extend([item for pt in self.partTables for item in pt.format()])
        result.append("\nEND.")
        return result

    def build(filetype: str, partTables: list[PartTable]):
        return PartTableFile(filetype, partTables)

    def cell(self):
        (part_table_dir, _) = os.path.split(self.path)
        (cell_dir, _) = os.path.split(part_table_dir)
        (_, cell_name) = os.path.split(cell_dir)
        cell_name = re.sub(r'#2d', '-', cell_name)
        return cell_name.upper()

    def library(self):
        (part_table_dir, _) = os.path.split(self.path)
        (cell_dir, _) = os.path.split(part_table_dir)
        (library_dir, _) = os.path.split(cell_dir)
        (_, library_name) = os.path.split(library_dir)

        if (library_name == 'project_specific'):
            library_name = "PROJ_SPCF"

        return library_name.upper()

    def parse(path):
        try:
            logging.info("Parsing: "+path)
            f = open(path, encoding='utf_8')
            lines = f.readlines()
            f.close()

            # Filter out blank lines and comments
            lines = sanitize_lines(lines)
            sanitizedFile = "".join(lines)

            part_table = seq(part_name, class_name.optional(""), header, rows << end_part).combine(PartTable.build_multi)
            multi_part_file = seq(filetype, part_table.at_least(1) << end).combine(PartTableFile.build)

            part_attributes = seq(part_name, class_name.optional(""), key_val.many() << end_part).combine(PartTable.build_single)
            single_part_file = seq(filetype, part_attributes.at_least(1) << end).combine(PartTableFile.build)

            file_parser = multi_part_file | single_part_file

            part_table_file = file_parser.parse(sanitizedFile)

            part_table_file.path = path

            return part_table_file
        except FileNotFoundError:
            logging.exception("Parsing " + path)
        except ParseError:
            logging.exception("Parsing " + path)
        except Exception as e:
            print(e, flush=True)
            print(path, flush=True)
            os._exit(-1)
