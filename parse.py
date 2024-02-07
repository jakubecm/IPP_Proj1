# @Author Milan Jakubec, 2 BIT FIT VUT
# @Date 7.2. 2024
# @file parse.py

# Dev notes:
# - Skript nesmi spoustet zadne dalsi procesy ci prikazy operacniho systemy
# - Veskera chybova hlaseni, varovani a ladici vypisy smeruji na stderr, jinak nedodrzeni zadani
# - Skript ktery dobehne bez chyby vraci 0
# - Skript ktery neprobehne bez chyby vraci chyby nasledovne:
#   10 - chubejici parametr skriptu (je-li treba) nebo pouziti nedovolene kombinace parametru
#   11 - chyba pri otevirani vstupnich souboru (neexistence, nedostacujici opravneni atd atd)
#   12 - chyba pri otevirani vystypnich soboru pro zapis (nedostacujici opravneni, chyba pri zapisu atd atd)
#   20 az 69 - navratove kody chyb specifickych pro jednotlive skripty 
#   99 - interni chyba (neovlivnena integraci, vstupnimi soubory nebo paramery CLI)
# - Veskere vstupy a vystupy v kodovani UTF-8 LC_ALL=cs_CZ.UTF-8
# - Pomocne skripty nebo knihovny povoleny, pripona dle zvyklosti v prg jazyce
# Predinstalovane knihovny povolene, jine je nutne konzultovat
# Doporucene naprogramovat si vlastni testy
# Pro navrat chyboveho kodu pouzivat sys.exit, ne return
# Rozparsovat vstup do XML stromu
# Při tvorbě analyzátoru doporučujeme kombinovat konečně-stavové řízení a regulární výrazy a pro generování výstupního XML využít vhodnou knihovnu.

# ------------- PARAMETRY ------------- #
# Obecne kombinovatelne parametry skriptu jsou oddelene aspon jednim whitespacem a pokud neni receno jinak, mohou byt v libovolnem poradi.
# Testovane vzdy budou dlouhe verze parametru, nicmene je mozne implementovat zastupne zkracene (jedna pomlcka) parametry
# Je-li soucasti parametru i soubor (pr. --source=file nebo --source="file") anebo cesta, muze byt ten soubor/cesta zadany relativni cestou nebo absolutni cestou,
# vyskyt znaku uvozovek nemusime uvazovat, stejne tak rovnitko. Cesty/jmena souboru mohou obsahovat Unicode UTF-8 znaky.
#
# --help : Vypise na standartni vystup napovedu skriptu (nenacita vstup), napovedu lze prevzit ze zadani a vrati 0.
#          Help nelze kombinovat s zadnym dalsi parametrem, jinak skript vraci 10.
#
# -------------------------------------#

#------- POPIS FUNKCE -------#
# - Nacte ze standartniho vstupu zdrojovy kod v IPP-Code24, zkontroluje lexikalni a syntaktickou spravnost kodu
# - Pokud je vse ok, vypise na standartni vystup XML reprezentaci programu dle specifikace v sekci 3.1. zadani
#----------------------------#

#------ SPECIFICKE CHYBOVE VYSTUPY -----#
# 21 - chybna nebo chubejici hlavicka zdrojoveho kodu zapsanem v IPPcode24
# 22 - neznamy nebo chybny operacni kod ve zdrojovem kodu napsanem v IPPcode24
# 23 - jina lexikalni nebo sytakticka chuba zdrojoveho kodu zapsaneho v IPPcode24
#---------------------------------------#

# XML snippet
#<?xml version="1.0" encoding="utf-8"?>
#<program language="IPPcode21">
  #<instruction order="1" opcode="DEFVAR">
   # <arg1 type="var">GF@counter</arg1>
  #</instruction>
  #<instruction order="2" opcode="MOVE">
   # <arg1 type="var">GF@counter</arg1>
  #  <arg2 type="string"/>
 # </instruction>
#  <instruction order="3" opcode="LABEL">
#    <arg1 type="label">while</arg1>
#  </instruction>


# POSTUP
# Krok 1: Zajistit spravne parsovani argumentu a praci s argumenty
# Krok 2: Tokenizovat zdrojovy kod
# Krok 3: Vytvorit regexy pro matchovani lexikalnich/syntaktickych pravidel
# Krok 4: Zajistit, aby se za behu generoval XML output
# Krok 5: Vratit XML output pokud vse probehne jak ma

import argparse
import re # na praci s regulernimi vyrazy
import sys
from enum import Enum

class ErrorCode(Enum):
    PARAMETER_ERR = 10
    INPUT_FILE_ERR = 11
    OUTPUT_FILE_ERR = 12
    MISSING_OR_WRONG_IPPCODE_HEADER = 21
    UNKNOWN_OPCODE = 22
    OTHER_LEXICAL_OR_SYNTACTICAL_ERR = 23
    INTERNAL_ERR = 99

def print_error_and_exit(error_code):
      error_messages = {
        ErrorCode.PARAMETER_ERR: "Error: missing script parameter or invalid combination of parameters used",
        ErrorCode.INPUT_FILE_ERR: "Error: failed to open input file",
        ErrorCode.OUTPUT_FILE_ERR: "Error: failed to open output file",
        ErrorCode.MISSING_OR_WRONG_IPPCODE_HEADER: "Error: missing or wrong IPPcode24 header in source code",
        ErrorCode.UNKNOWN_OPCODE: "Error: unknown opcode in source code",
        ErrorCode.OTHER_LEXICAL_OR_SYNTACTICAL_ERR: "Error: other lexical or syntactical error detected",
        ErrorCode.INTERNAL_ERR: "Error: internal error"
      }
      
      error_message = error_messages.get(error_code)
      if error_message:
        print(error_message, file=sys.stderr)
        sys.exit(error_code.value)
  
    
def main():
    """The main function"""

    parser = argparse.ArgumentParser(description="Filter-type script; "
                                                "reads the source code written in "
                                                "IPPcode24 from the standard input, " 
                                                "checks the lexical and syntactic "
                                                "correctness of the code and prints "                    
                                                "the XML representation of the "
                                                "program to the standard output.")
    parser.parse_args()

    if(len(sys.argv) == 1):
        print_error_and_exit(ErrorCode.INPUT_FILE_ERR)
    else:
        source_code = sys.stdin.read()
        lex_analysis(source_code)
    

def lex_analysis(source_code):
    print(source_code)
    for line in source_code.splitlines():
        print("Working on line:", line.strip())

    

main()