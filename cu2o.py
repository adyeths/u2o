#!/usr/bin/env python3
"""Program information goes here."""
import logging
from sys import exit
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from tempfile import TemporaryDirectory
from pathlib import Path
from os import path
from typing import Any

from u2o import processfiles, LOG, META, BOOKORDERS, HAVELXML

# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals


def processfiles2(
    fname: str,
    fencoding: str,
    dodebug: bool,
    sortorder: str,
    langcode: str,
    nonormalize: bool,
    novalidate: bool,
    workid: str,
    outputfile: str,
) -> None:
    """Unsplit a single concatenated usfm file for processing."""
    i: Any

    # read file
    LOG.info("Reading filename and splitting into separate files... ")
    with open(fname, "rb") as ifile:
        text = ifile.read()
        textlines = text.decode("utf-8-sig").strip().split("\n")

        # get index of locations for \id tags
        idx = [textlines.index(_) for _ in textlines if _.startswith(r"\id ")]

        # remove duplicate book names
        i = len(idx) - 1
        while i > 0:
            if textlines[idx[i]][4:7] == textlines[idx[i - 1]][4:7]:
                del idx[i]
            i -= 1

        # split into individual books
        books = {}
        i = 0
        while i < len(idx):
            bname = textlines[idx[i]][4:7]
            start = idx[i]
            try:
                end = idx[i + 1]
            except IndexError:
                end = len(textlines)
            books[bname] = "\n".join(textlines[start:end])
            i += 1

        # create temporary files and process
        with TemporaryDirectory() as tmpdir:
            filenames = []
            pth = Path(tmpdir)
            for i in books.items():
                ipth = pth / i[0]
                with open(ipth, "w+", encoding="utf-8") as outfile:
                    outfile.write(i[1])
                    filenames.append(str(ipth))

            processfiles(
                filenames,
                fencoding,
                dodebug,
                sortorder,
                langcode,
                nonormalize,
                novalidate,
                workid,
                outputfile,
            )


# ---------------------------------------------------------------------------#


if __name__ == "__main__":
    PARSER = ArgumentParser(
        formatter_class=ArgumentDefaultsHelpFormatter,
        description="""
            convert USFM bibles to OSIS.
        """,
        epilog=f"""
            * Version: {META['VERSION']} * {META['DATE']} * This script is public domain. *
        """,
    )
    PARSER.add_argument("workid", help="work id to use for OSIS file")
    PARSER.add_argument("-d", help="debug mode", action="store_true")
    PARSER.add_argument(
        "-e",
        help="set encoding to use for USFM files",
        default=None,
        metavar="encoding",
    )
    PARSER.add_argument(
        "-o", help="specify output file", metavar="output_file"
    )
    PARSER.add_argument(
        "-l", help="specify langauge code", metavar="LANG", default="und"
    )
    PARSER.add_argument(
        "-s", help="sort order", choices=BOOKORDERS, default="canonical"
    )
    PARSER.add_argument("-v", help="verbose output", action="store_true")
    PARSER.add_argument(
        "-x",
        help="(deprecated, does nothing) formerly used to disable OSIS validation and reformatting",
        action="store_true",
    )
    PARSER.add_argument(
        "-n", help="disable unicode NFC normalization", action="store_true"
    )
    PARSER.add_argument(
        "file",
        help="file to process",
        metavar="filename",
    )
    ARGS = PARSER.parse_args()

    # make sure we skip OSIS validation if we don't have lxml
    if not ARGS.x and not HAVELXML:
        ARGS.x = True
        LOG.warning("Note:  lxml is not installed. Skipping OSIS validation.")

    if not path.isfile(ARGS.file):
        LOG.error("*** input file not present or not a normal file. ***")
        exit()

    if ARGS.v:
        LOG.setLevel(logging.INFO)
    if ARGS.d:
        LOG.setLevel(logging.DEBUG)
    processfiles2(
        ARGS.file,
        ARGS.e,
        ARGS.d,
        ARGS.s,
        ARGS.l,
        ARGS.n,
        ARGS.x,
        ARGS.workid,
        ARGS.o,
    )
