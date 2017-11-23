#!/usr/bin/python3
# -*- coding: utf8 -*-
"""Helper script to add osisRef attributes to reference tags in osis files."""
from __future__ import print_function, unicode_literals
import sys
import argparse
import os.path
from collections import OrderedDict
import re

# -------------------------------------------------------------------------- #

# NOTES AND KNOWN LIMITATIONS:
#
#   REQUIRES the presence of toc2 and toc3 tags. If these are not
#   present, there won't be any way to determine the book part for
#   the osisRef attribute.
#
#   If the references use abbreviations or book names not specified
#   in any of the toc2 or toc3 tags, then the processing of the
#   reference WILL fail.
#
#   Only works for chapters and verses that are specified using
#   arabic numerals. (0-9). Any other character will cause the
#   reference to not be processed.
#
#   It expects multiple references to be separated by a semicolon(;).
#
#   Does not process reference ranges that cross chapter boundaries.
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


def processreferences(text, abbr, abbr2):
    """Process cross references in osis text."""
    crossrefnote = re.compile(
        r'(<note type="crossReference">)(.*?)(</note>)', re.U)
    reftag = re.compile(
        r'(<reference>)(.*?)(</reference>)', re.U)

    lines = text.split('\n')

    def simplerepl(match):
        """Simple regex replacement helper function."""
        text = match.group(2)
        osisrefs = getosisrefs(text, abbr, abbr2)

        # process reference tags
        if match.group(1) == '<reference>':
            outtext = r'<reference osisRef="{}">{}</reference>'.format(
                osisrefs, text)
        else:
            # only process references if no reference tag is present in text.
            if '<reference ' not in text:
                outtext = r'<note type="crossReference">{}</note>'.format(
                    '<reference osisRef="{}">{}</reference>'.format(osisrefs,
                                                                    text))
            else:
                outtext = r'<note type="crossReference">{}</note>'.format(
                    text)
        return outtext

    # process reference tags in document
    for i in (_ for _ in range(len(lines)) if "<reference>" in lines[_]):
        lines[i] = reftag.sub(simplerepl, lines[i], 0)

    # insert reference tags in cross reference notes
    for i in (_ for _ in range(len(lines)) if "crossReference" in lines[_]):
        lines[i] = crossrefnote.sub(simplerepl, lines[i], 0)

    return '\n'.join(lines)


def getosisrefs(text, abbr, abbr2):
    """Attempt to get a list of osis refs from a line of text."""
    # skip reference processing if there is already a reference tag present.
    if "<reference" in text:
        return text

    # --- normalize verse reference ranges
    for i in SEPRNORM:
        text = text.replace(i, SEPR)

    # --- break multiple references part
    newtext = text.split(SEPM)
    if not isinstance(newtext, list):
        newtext = [newtext]
    newtext = [_.strip() for _ in newtext]

    # --- process book part of references
    lastbook = None
    for i in reversed(abbr):
        tag = BTAG.format(abbr[i][0])

        for j in enumerate(newtext):
            try:
                if tag[0] not in newtext[j[0]]:
                    newtext[j[0]] = newtext[j[0]].replace(abbr[i][1], tag)
                    newtext[j[0]] = newtext[j[0]].replace(abbr[i][2], tag)
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
            print("{} {}".format("WARNING: (book) Reference not processed…",
                                 newtext[i[0]]),
                  file=sys.stderr)
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
        chap = chapverse[0]
        vrs = chapverse[2]

        # verses separated by commas
        if SEPP in vrs:
            vrs = vrs.split(SEPP)
            for j in vrs:
                if SEPR in j:
                    if SEPC not in vrs:
                        rng = j.split(SEPR)
                        try:
                            for num in range(int(rng[0]), int(rng[1]) + 1):
                                refs.append("{}.{}.{}".format(abbr2[bkref],
                                                              chap,
                                                              str(num)))
                        except ValueError:
                            print("{}… {} {}".format(
                                "WARNING: Reference not processed",
                                abbr2[bkref],
                                bcv[2]),
                                  file=sys.stderr)
                    else:
                        print("{}… {} {}".format(
                            "WARNING: Reference not processed",
                            abbr2[bkref],
                            bcv[2]),
                              file=sys.stderr)
                else:
                    if " " in j:
                        tmp = j.split(" ")
                        if len(tmp) > 2:
                            print("{}… {} {}".format(
                                "WARNING: Reference not processed",
                                abbr2[bkref],
                                bcv[2]),
                                  file=sys.stderr)
                        else:
                            refs.append("{}:{}.{}.{}".format(
                                tmp[1],
                                abbr2[bkref],
                                chap,
                                tmp[0]))
                    else:
                        refs.append("{}.{}.{}".format(abbr2[bkref], chap, j))
        # verse not separated by commas
        else:
            if SEPR in vrs:
                rng = vrs.split(SEPR)
                if SEPC not in vrs:
                    try:
                        for num in range(int(rng[0]), int(rng[1]) + 1):
                            refs.append("{}.{}.{}".format(abbr2[bkref],
                                                          chap,
                                                          str(num)))
                    except ValueError:
                        print("{}… {} {}".format(
                            "WARNING: Reference not processed",
                            abbr2[bkref],
                            bcv[2]),
                              file=sys.stderr)
                else:
                    print("{}… {} {}".format(
                        "WARNING: Reference not processed",
                        abbr2[bkref],
                        bcv[2]),
                          file=sys.stderr)
            else:
                if " " in vrs:
                    tmp = vrs.split(" ")
                    if len(tmp) > 2:
                        print("{}… {} {}".format(
                            "WARNING: Reference not processed",
                            abbr2[bkref],
                            bcv[2]),
                              file=sys.stderr)
                    else:
                        refs.append("{}:{}.{}.{}".format(
                            tmp[1],
                            abbr2[bkref],
                            chap,
                            tmp[0]))
                else:
                    refs.append("{}.{}.{}".format(abbr2[bkref], chap, vrs))

    # --- return joined references
    return " ".join(refs)

# -------------------------------------------------------------------------- #


def processfile(args):
    """Process osis file."""
    with open(args.i, "r") as ifile:
        if args.v:
            print("Reading input file {} ...".format(args.i))
        text = ifile.read()

    if args.v:
        print("Getting book names and abbreviations from osis file...")
    bookabbrevs, bookabbrevs2 = getabbrevs(text)
    if args.v:
        print("Processing cross references...")
    text = processreferences(text, bookabbrevs, bookabbrevs2)

    with open(args.o, "wb") as ofile:
        if args.v:
            print("Writing output to {} ".format(args.o))
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
    args = parser.parse_args()

    if not os.path.isfile(args.i):
        print("ERROR: input file is not present or is not a normal file.",
              file=sys.stderr)
        sys.exit()

    processfile(args)


if __name__ == "__main__":
    main()
