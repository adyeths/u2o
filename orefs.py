#!/usr/bin/python3
# -*- coding: utf8 -*-
"""Helper script to add osisRef attributes to reference tags in osis files."""
from __future__ import print_function, unicode_literals
import sys
import argparse
import os.path
import configparser
from collections import OrderedDict
import re

# -------------------------------------------------------------------------- #

# NOTES AND KNOWN LIMITATIONS:
#
#   For automatic determination of book abbreviations, the presence
#   of toc2 and toc3 tags is required. If these are not present, there
#   won't be any way to determine the book part for the osisRef attribute.
#
#   ALTERNATIVELY, a separate config file can be used to manually specify
#   book names and abbreviations. See the README-orefs.md file for more
#   information and example config file contents.
#
#   A beginning config file can be automatically generated now using the
#   following command:
#
#       orefs.py -i OSISFILE -o CONFIGFILE -c create
#

# SPECIAL CHARACTERS USED DURING PROCESSING:
#    uFDEA     - marks start of book abbreviation during processing
#    uFDEB     - marks end of book abbreviation during processing

# VARIABLES THAT CONTROL HOW VERSE REFERENCES ARE PARSED
SEPM = ";"  # separates multiple references
SEPC = ":"  # separates chapter from verse
SEPP = ","  # separates multiple verses or verse ranges
SEPR = "-"  # separates verse ranges
SEPRNORM = ["–", "—"]  # used to normalize verse ranges

# book tag format string
BTAG = "\uFDEA{}\uFDEB"

# list of OSIS bible books
BOOKLIST = [
    'Gen', 'Exod', 'Lev', 'Num', 'Deut', 'Josh', 'Judg', 'Ruth', '1Sam',
    '2Sam', '1Kgs', '2Kgs', '1Chr', '2Chr', 'PrMan', 'Jub', '1En', 'Ezra',
    'Neh', 'Tob', 'Jdt', 'Esth', 'EsthGr', '1Meq', '2Meq', '3Meq', 'Job',
    'Ps', 'AddPs', '5ApocSyrPss', 'Odes', 'Prov', 'Reproof', 'Eccl', 'Song',
    'Wis', 'Sir', 'PssSol', 'Isa', 'Jer', 'Lam', 'Bar', 'EpJer', '2Bar',
    'EpBar', '4Bar', 'Ezek', 'Dan', 'DanGr', 'PrAzar', 'Sus', 'Bel', 'Hos',
    'Joel', 'Amos', 'Obad', 'Jonah', 'Mic', 'Nah', 'Hab', 'Zeph', 'Hag',
    'Zech', 'Mal',
    '1Esd', '2Esd', '4Ezra', '5Ezra', '6Ezra', '1Macc', '2Macc', '3Macc',
    '4Macc',
    'Matt', 'Mark', 'Luke', 'John', 'Acts', 'Rom', '1Cor', '2Cor', 'Gal',
    'Eph', 'Phil', 'Col', '1Thess', '2Thess', '1Tim', '2Tim', 'Titus', 'Phlm',
    'Heb', 'Jas', '1Pet', '2Pet', '1John', '2John', '3John', 'Jude', 'Rev',
    'EpLao'
]


def getabbrevs(text):
    """Get book abbreviations from toc2 and toc3 usfm tags."""
    abbrevs = OrderedDict()
    abbrevs2 = OrderedDict()
    book = ""
    lines = text.split("\n")
    num = 0
    for i in [_ for _ in lines if 'type="book"' in _]:
        num += 1
        bkline = lines.index(i)
        book = i.partition('osisID="')[2].split('"')[0]
        abbrevs[book] = ["{:03}".format(num)]
        abbrevs2["{:03}".format(num)] = book
        for j in range(bkline, bkline + 10):
            if "x-usfm-toc2" in lines[j]:
                abbr = lines[j].partition('n="')[2].split('"')[0]
                abbrevs[book].append(abbr)
            elif "x-usfm-toc3" in lines[j]:
                abbr = lines[j].partition('n="')[2].split('"')[0]
                abbrevs[book].append(abbr)
    return abbrevs, abbrevs2


def readconfig(fname):
    """Read a config file and return the values."""
    # set up config parser and read our config file...
    config = configparser.ConfigParser(allow_no_value=True)
    config.optionxform = str
    config.read(fname)

    # variables used while reading config file
    abbr = OrderedDict()

    # get default part of config...
    for i in ["SEPM", "SEPP", "SEPC", "SEPR", "SEPRNORM"]:
        globals()[i] = config["DEFAULT"][i]
    if globals()["SEPRNORM"] == "":
        globals()["SEPRNORM"] = list(globals()["SEPR"])
    else:
        globals()["SEPRNORM"] = list(globals()["SEPRNORM"])

    # get abbreviations
    for i in BOOKLIST:
        if i in config["ABBR"]:
            abbr[i] = {
                True: config["ABBR"][i],
                False: None
            }[config["ABBR"][i] != ""]

    # fix abbreviation lists
    abbrevs = OrderedDict()
    abbrevs2 = OrderedDict()
    num = 0
    for i in abbr:
        num += 1
        if abbr[i] is not None:
            abbr[i] = [i.strip() for i in abbr[i].split(",")]
            abbr[i] = sorted(abbr[i], key=len, reverse=True)
            abbr[i].insert(0, "{:03}".format(num))
            abbrevs[i] = abbr[i]
            abbrevs2[abbr[i][0]] = i

    # return our abbreviations and configuration
    return abbrevs, abbrevs2


def genconf(text):
    """Generate contents of a config file."""
    # set up config parser
    config = configparser.ConfigParser(allow_no_value=True)
    config.optionxform = str
    for i in (("SEPM", SEPM),
              ("SEPP", SEPP),
              ("SEPC", SEPC),
              ("SEPR", SEPR),
              ("SEPRNORM", "".join(SEPRNORM))):
        config["DEFAULT"][i[0]] = i[1]

    # create ABBR section of config…
    config["ABBR"] = {}
    for i in BOOKLIST:
        config["ABBR"][i] = ""
    abbr1, _ = getabbrevs(text)
    for i in abbr1.keys():
        config["ABBR"][i] = ", ".join(abbr1[i][1:])

    # return our generate configuration
    return config


def processreferences(text, abbr, abbr2):
    """Process cross references in osis text."""
    crossrefnote = re.compile(
        r'(<note type="crossReference">)(.*?)(</note>)', re.U)
    reftag = re.compile(
        r'(<reference[^>]*>)(.*?)(</reference>)', re.U)

    lines = text.split('\n')

    currentbook = ""

    def simplerepl(match):
        """Simple regex replacement helper function."""
        errortext = ""
        text = match.group(2)
        osisrefs, oreferror = getosisrefs(text, currentbook, abbr, abbr2)

        if oreferror:
            errortext = '<!-- orefs - unprocessed reference -->'

        # process reference tags
        if match.group(1).startswith('<reference'):
            reftagstart = match.group(1).replace('>', ' {}>').format(
                'osisRef="{}"'.format(osisrefs))
            outtext = '{}{}{}</reference>'.format(
                reftagstart, text, errortext)
        else:
            # only process references if no reference tag is present in text.
            if '<reference ' not in text:
                outtext = r'<note type="crossReference">{}</note>'.format(
                    '<reference osisRef="{}">{}{}</reference>'.format(
                        osisrefs,
                        text,
                        errortext))
            else:
                outtext = r'<note type="crossReference">{}</note>'.format(
                    text)
        return outtext

    for i in (_ for _ in range(len(lines))):
        if 'div type="book"' in lines[i]:
            currentbook = lines[i].split('osisID="')[1].split('"')[0]
        if "<reference" in lines[i]:
            lines[i] = reftag.sub(simplerepl, lines[i], 0)
        if "crossReference" in lines[i]:
            lines[i] = crossrefnote.sub(simplerepl, lines[i], 0)

    return '\n'.join(lines)


def getosisrefs(text, currentbook, abbr, abbr2):
    """Attempt to get a list of osis refs from a line of text."""
    # skip reference processing if there is already a reference tag present.
    if "<reference" in text:
        return text, False

    # --- helper functions
    def chapchk(num):
        """Chapter number sanity check."""
        try:
            rval = str(int(num))
        except ValueError:
            rval = {
                True: num,
                False: False,
            }[num in "ABCDEFabcdef"]
        return rval

    def vrschk(num):
        """Verse number sanity check."""
        rval = False
        try:
            rval = str(int(num))
        except ValueError:
            try:
                if num[-1] in "ABCDabcd":
                    rval = "{}!{}".format(str(int(num[:-1])), num[-1])
            except ValueError:
                pass
        return rval

    def referror(text, abbr):
        """Print a reference error message."""
        for i in abbr.keys():
            text = text.replace("{}{}{}".format(BTAG[0],
                                                i,
                                                BTAG[-1]),
                                abbr[i])
        print("WARNING: Reference not processed… {}".format(text),
              file=sys.stderr)

    # --- flag used to indicate an error processing references
    oreferror = False

    # --- normalize range separator
    for i in SEPRNORM:
        text = text.replace(i, SEPR)

    # --- filter out directional formatting characters
    for i in ['\u200E', '\u200F', '\u061C', '\u202A', '\u202B', '\u202C',
              '\u202D', '\u202E', '\u2066', '\u2067', '\u2068', '\u2069']:
        text = text.replace(i, '')

    # --- break multiple references part
    newtext = text.split(SEPM)
    if not isinstance(newtext, list):
        newtext = [newtext]
    newtext = [_.strip() for _ in newtext]

    # --- process book part of references
    lastbook = BTAG.format(abbr[currentbook][0])
    for i in reversed(abbr):
        tag = BTAG.format(abbr[i][0])

        for j in enumerate(newtext):
            try:
                if tag[0] not in newtext[j[0]]:
                    for k in abbr[i][1:]:
                        newtext[j[0]] = newtext[j[0]].replace(k, tag)
                    if tag[0] in newtext[j[0]]:
                        lastbook = tag
                if tag[0] in newtext[j[0]]:
                    tmp = newtext[j[0]].partition(" ")
                    try:
                        newtext[j[0]] = " ".join([
                            tmp[0][tmp[0].index(tag[0]):],
                            tmp[2]])
                    except ValueError:
                        newtext[j[0]] = " ".join([tmp[0], tmp[2]])
            except IndexError:
                pass
            # add last book to reference where it was omitted.
            nobook = True
            for k in newtext[j[0]]:
                if k not in list("0123456789:;,.-"):
                    nobook = False
                    break
            if nobook and lastbook is not None:
                newtext[j[0]] = "{} {}".format(lastbook, newtext[j[0]])

    # remove bad book references
    for i in enumerate(newtext):
        chk = i[1].partition(BTAG[-1])
        if chk[2] == "":
            referror(newtext[i[0]], abbr2)
            oreferror = True
            newtext[i[0]] = None
    newtext = [_ for _ in newtext if _ is not None]

    # --- process chapter/verse part of references
    refs = []
    for i in newtext:
        # book part
        bcv = i.partition(BTAG[-1])
        bkref = bcv[0].partition(BTAG[0])[2]

        # chapverse part
        if SEPC in bcv[2]:
            chapverse = bcv[2].lstrip(" ").partition(SEPC)
        else:
            # handle books that only have 1 chapter
            chapverse = "1:{}".format(bcv[2].lstrip(" ")).partition(SEPC)
        chap = chapchk(chapverse[0])
        if chap is False:
            referror(i, abbr2)
            oreferror = True
            continue
        vrs = chapverse[2]

        # split references into multiple parts separated by SEPP
        vrs = vrs.split(SEPP)
        for j in vrs:
            # split on verse ranges
            vrsrange = j.split(SEPR)
            if len(vrsrange) > 1:
                # split 2nd part of verse range at SEPC
                vrsrange2 = vrsrange[1].split(SEPC)
                if len(vrsrange2) > 1:
                    # additional chapter specified
                    vrsrange2[0] = chapchk(vrsrange2[0])
                    vrsrange2[1] = vrschk(vrsrange2[1])
                    if False in vrsrange2:
                        referror(" ".join([abbr2[bkref], j]), abbr2)
                        oreferror = True
                        continue
                    refs.append("{}.{}.{}-{}.{}.{}".format(
                        abbr2[bkref],
                        chap,
                        vrsrange[0],
                        abbr2[bkref],
                        vrsrange2[0],
                        vrsrange2[1]))
                else:
                    # no additional chapter specified
                    vrsrange[0] = vrschk(vrsrange[0])
                    vrsrange[1] = vrschk(vrsrange[1])
                    if False in vrsrange:
                        referror(" ".join([abbr2[bkref], j]), abbr2)
                        oreferror = True
                        continue
                    refs.append("{}.{}.{}-{}.{}.{}".format(
                        abbr2[bkref],
                        chap,
                        vrsrange[0],
                        abbr2[bkref],
                        chap,
                        vrsrange[1]))
            # not a verse range
            else:
                if SEPC in j:
                    chapverse2 = j.split(SEPC)
                    if " " in chapverse2[1]:
                        chapverse2[1] = chapverse2[1].split(" ")[0]
                    chapverse2[0] = chapchk(chapverse2[0])
                    chapverse2[1] = vrschk(chapverse2[1])
                    if False in chapverse2:
                        referror(" ".join([abbr2[bkref], j]), abbr2)
                        oreferror = True
                        continue
                    refs.append("{}.{}.{}".format(abbr2[bkref],
                                                  chapverse2[0],
                                                  chapverse2[1]))
                else:
                    if " " in j:
                        j = j.split(" ")[0]
                    tmp = vrschk(j)
                    if tmp is False:
                        referror(" ".join([abbr2[bkref], j]), abbr2)
                        oreferror = True
                        continue
                    refs.append("{}.{}.{}".format(abbr2[bkref], chap, tmp))

    # --- return joined references
    return " ".join(refs), oreferror

# -------------------------------------------------------------------------- #


def processfile(args):
    """Process osis file."""
    with open(args.i, "r") as ifile:
        if args.v:
            print("Reading input file {} ...".format(args.i))
        text = ifile.read()

    if args.v:
        print("Getting book names and abbreviations...")
    if args.c is not None:
        if args.c == "create":
            if args.v:
                print("Creating config file...")
            generatedconf = genconf(text)
        else:
            if args.v:
                print("Using config file for abbreviations...")
            bookabbrevs, bookabbrevs2 = readconfig(args.c)
    else:
        if args.v:
            print("Extracting book names and abbreviations from osis file...")
        bookabbrevs, bookabbrevs2 = getabbrevs(text)
    if args.c != "create":
        if args.v:
            print("Processing cross references...")
        text = processreferences(text, bookabbrevs, bookabbrevs2)

    if args.v:
        print("Writing output to {} ".format(args.o))
    if args.c == "create":
        with open(args.o, "w") as ofile:
            generatedconf.write(ofile)
    else:
        with open(args.o, "wb") as ofile:
            ofile.write(text.encode("utf8"))

    if args.v:
        print("Done.")

# -------------------------------------------------------------------------- #


def main():
    """
    Main routine.

    Process our command line arguments and pass the options
    along to subroutine that processes the file.

    """
    parser = argparse.ArgumentParser(
        description="""
            Process cross references.
        """
    )
    parser.add_argument("-v",
                        help="verbose output",
                        action="store_true")
    parser.add_argument("-i",
                        help="name of input file",
                        required=True, metavar="FILE")
    parser.add_argument("-o",
                        help="name of output file",
                        required=True, metavar="FILE")
    parser.add_argument("-c",
                        help="\n".join([
                            "config file to use.",
                            "create means to generate a config file."]),
                        metavar="FILE|create")
    args = parser.parse_args()

    if not os.path.isfile(args.i):
        print("ERROR: input file is not present or is not a normal file.",
              file=sys.stderr)
        sys.exit()

    processfile(args)


if __name__ == "__main__":
    main()
