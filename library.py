from cell import PartTableFile
import concurrent.futures
import logging
import os


def list_valid( path ):
    """
    Giving the path to the libraries, this function will return a list of the valid libraries.
    """
    libraries = []
    for library in sub_directories(path):
        if is_valid_library(library):
            libraries.append(library)
    return libraries

def sub_directories(currentDirectory):
    children = os.scandir(currentDirectory)
    return [child for child in children if child.is_dir()]


def is_valid_library(dirEntry) -> bool:
    for invalid in ['obsolete', 'problem_parts', 'nonparts']:
        if invalid in dirEntry.path:
            return False
    return True

def get_part_table_files(libraries) -> list[PartTableFile]:
    """
    Giving a list of libraries, this function will go in each library and collect all the part table files
    It uses multiple threads to go faster.
    """
    partFiles = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = executor.map(find_parttable_files, libraries)
        for future in futures:
            for file in future:
                partFiles.append(file)

        partFiles1 = []
        futures1 = executor.map(PartTableFile.parse, partFiles)
        for future1 in futures1:
            # for file1 in future1:
            partFiles1.append(future1)

        return partFiles1

def find_parttable_files(library) -> list[PartTableFile]:
    """
    Returns all the part table files in a library.
    The part table file is keyed off the content of the master.tag file.
    library: The library to look into.
    """
    partTableFiles = []

    cells = os.scandir(library)
    for cell in cells:
        if (cell.is_dir()):
            master_tag_file = os.path.join(cell.path, "part_table", "master.tag")
            try:
                f = open(master_tag_file)
                partFilename = f.readline().strip()
                f.close()
                filepath = os.path.join(cell.path, "part_table", partFilename)
                if (os.path.isfile(filepath)):
                    partTableFiles.append(filepath)
                else:
                    logging.error("Part table file does not exist:" + filepath)
            except FileNotFoundError:
                continue

    return partTableFiles
