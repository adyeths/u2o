#!/usr/bin/env python3

r"""
Convert usfm bibles to osis.

Notes:
   * better handling of osisID's is probably needed.

   * no attempt has been made to process any x- attributes in this script

   * I can think of scenarios where this script may not work properly. However,
     it works fine for all of the usfm bibles that I have access to at this
     time.

   * jmp, xop, and sd# need better handling.

   * There may be better ways to handle lh and lf

   * table cell column spanning is not implemented

Alternative Book Ordering:
    To have the books output in an order different from the built in canonical
    book order you will have to create a simple text file.

    FIRST, put the OSIS ID's for the books in the order you want, one per line,
    in a plain text file. Example:
        Gen
        Exod
        Lev
        ...
        Rev

    SECOND, name the file as follows:   order-SomeOrderYouWant.txt

    THIRD, place that file in the directory where you will be running
    the script. This new book order will be automatically detected and
    available.

    Examples can be provided. Simple send me an email and ask me for them.

    NOTE: I should probably change this so that there's a more central
          location for these alternative book orderings.

This script is public domain. You may do whatever you want with it.

"""

#
#    uFDD0     - used to mark line breaks during processing
#    uFDD1     - used to preserve line breaks during wj processing
#
#    uFDD2     - used at start of footnotes to help process \fp markers
#    uFDD3     - used at end of footnotes to help process \fp markers
#
#    uFDD4     - mark end of cl and sp tags
#    uFDD5     - mark end of cp tags
#
#    uFDDF     - used to mark separation between files when read from storage.
#
#    uFDE0     - used to mark the start of introductions
#    uFDE1     - used to mark the end of introductions
#
#    uFDE2     - used to separate attributes in usfm tags
#

# make pylint happier..
# pylint: disable=too-many-lines
# pylint: disable=too-many-statements
# pylint: disable=too-many-branches
# pylint: disable=too-many-locals
# pylint: disable=too-many-arguments
# pylint: disable=consider-using-f-string

import concurrent.futures
import logging
import os.path
import re
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from codecs import decode, encode, lookup
from datetime import datetime
from functools import partial
from glob import glob
from itertools import chain
from os import getenv
from sys import exit as sysexit
from tempfile import NamedTemporaryFile
from typing import Any
from unicodedata import normalize

et: Any
_: Any

# try to import lxml so that we can validate
# our output against the OSIS schema.
try:
    import lxml.etree as et  # nosec

    HAVELXML = True
except ImportError:
    et = None
    HAVELXML = False

# -------------------------------------------------------------------------- #

META = {
    "USFM": "3.0",  # Targeted USFM version
    "OSIS": "2.1.1",  # Targeted OSIS version
    "VERSION": "0.7",  # THIS SCRIPT version
    "DATE": "2025-04-09",  # THIS SCRIPT revision date
}

# -------------------------------------------------------------------------- #

OSISHEADER = """<?xml version="1.0" encoding="utf-8"?>
<osis xmlns="http://www.bibletechnologies.net/2003/OSIS/namespace"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.bibletechnologies.net/2003/OSIS/namespace
        http://www.bibletechnologies.net/osisCore.2.1.1.xsd">
    <osisText osisIDWork="{}" osisRefWork="Bible" xml:lang="{}">
        <header>
            <revisionDesc resp="{}">
                <date>{}</date>
                <p>Converted from USFM source using u2o.py</p>
            </revisionDesc>
            <work osisWork="{}">
                <title>{}</title>
                {}
                <type type="OSIS">Bible</type>
                <identifier type="OSIS">Bible.{}.{}</identifier>
                <refSystem>Bible</refSystem>
            </work>{}
        </header>\n"""

STRONGSWORK = """
            <work osisWork="strong">
                <refSystem>Dict.Strongs</refSystem>
            </work>"""

OSISFOOTER = """
    </osisText>
</osis>\n"""

# -------------------------------------------------------------------------- #

CANONICALORDER = (
    # Canonical order used by the usfm2osis.py script...
    # minus the extra books that aren't part of usfm at this time.
    "FRONT",
    "INTRODUCTION",
    "Gen",
    "Exod",
    "Lev",
    "Num",
    "Deut",
    "Josh",
    "Judg",
    "Ruth",
    "1Sam",
    "2Sam",
    "1Kgs",
    "2Kgs",
    "1Chr",
    "2Chr",
    "PrMan",
    "Jub",
    "1En",
    "Ezra",
    "Neh",
    "Tob",
    "Jdt",
    "Esth",
    "EsthGr",
    "1Meq",
    "2Meq",
    "3Meq",
    "Job",
    "Ps",
    "AddPs",
    "5ApocSyrPss",
    "Odes",
    "Prov",
    "Reproof",
    "Eccl",
    "Song",
    "Wis",
    "Sir",
    "PssSol",
    "Isa",
    "Jer",
    "Lam",
    "Bar",
    "EpJer",
    "2Bar",
    "EpBar",
    "4Bar",
    "Ezek",
    "Dan",
    "DanGr",
    "PrAzar",
    "Sus",
    "Bel",
    "Hos",
    "Joel",
    "Amos",
    "Obad",
    "Jonah",
    "Mic",
    "Nah",
    "Hab",
    "Zeph",
    "Hag",
    "Zech",
    "Mal",
    "1Esd",
    "2Esd",
    "4Ezra",
    "5Ezra",
    "6Ezra",
    "1Macc",
    "2Macc",
    "3Macc",
    "4Macc",
    "Matt",
    "Mark",
    "Luke",
    "John",
    "Acts",
    "Rom",
    "1Cor",
    "2Cor",
    "Gal",
    "Eph",
    "Phil",
    "Col",
    "1Thess",
    "2Thess",
    "1Tim",
    "2Tim",
    "Titus",
    "Phlm",
    "Heb",
    "Jas",
    "1Pet",
    "2Pet",
    "1John",
    "2John",
    "3John",
    "Jude",
    "Rev",
    "EpLao",
    "XXA",
    "XXB",
    "XXC",
    "XXD",
    "XXE",
    "XXF",
    "XXG",
    "BACK",
    "CONCORDANCE",
    "GLOSSARY",
    "INDEX",
    "GAZETTEER",
    "X-OTHER",
)
# get list of book orders available from external files in the current
# working directory.  Each order file has the following naming pattern:
#    order-SOMEORDER.txt
BOOKORDERS = tuple(
    chain(
        ["canonical"],
        sorted(
            [_.replace("order-", "").replace(".txt", "") for _ in glob("order-*.txt")]
        ),
        ["none"],
    )
)

# -------------------------------------------------------------------------- #

# convert usfm book names
BOOKNAMES = {
    # old testament books
    "GEN": "Gen",
    "EXO": "Exod",
    "LEV": "Lev",
    "NUM": "Num",
    "DEU": "Deut",
    "JOS": "Josh",
    "JDG": "Judg",
    "RUT": "Ruth",
    "1SA": "1Sam",
    "2SA": "2Sam",
    "1KI": "1Kgs",
    "2KI": "2Kgs",
    "1CH": "1Chr",
    "2CH": "2Chr",
    "EZR": "Ezra",
    "NEH": "Neh",
    "EST": "Esth",
    "JOB": "Job",
    "PSA": "Ps",
    "PRO": "Prov",
    "ECC": "Eccl",
    "SNG": "Song",
    "ISA": "Isa",
    "JER": "Jer",
    "LAM": "Lam",
    "EZK": "Ezek",
    "DAN": "Dan",
    "HOS": "Hos",
    "JOL": "Joel",
    "AMO": "Amos",
    "OBA": "Obad",
    "JON": "Jonah",
    "MIC": "Mic",
    "NAM": "Nah",
    "HAB": "Hab",
    "ZEP": "Zeph",
    "HAG": "Hag",
    "ZEC": "Zech",
    "MAL": "Mal",
    # new testament books
    "MAT": "Matt",
    "MRK": "Mark",
    "LUK": "Luke",
    "JHN": "John",
    "ACT": "Acts",
    "ROM": "Rom",
    "1CO": "1Cor",
    "2CO": "2Cor",
    "GAL": "Gal",
    "EPH": "Eph",
    "PHP": "Phil",
    "COL": "Col",
    "1TH": "1Thess",
    "2TH": "2Thess",
    "1TI": "1Tim",
    "2TI": "2Tim",
    "TIT": "Titus",
    "PHM": "Phlm",
    "HEB": "Heb",
    "JAS": "Jas",
    "1PE": "1Pet",
    "2PE": "2Pet",
    "1JN": "1John",
    "2JN": "2John",
    "3JN": "3John",
    "JUD": "Jude",
    "REV": "Rev",
    # other books
    "TOB": "Tob",
    "JDT": "Jdt",
    "ESG": "EsthGr",
    "WIS": "Wis",
    "SIR": "Sir",
    "BAR": "Bar",
    "LJE": "EpJer",
    "S3Y": "PrAzar",
    "SUS": "Sus",
    "BEL": "Bel",
    "1MA": "1Macc",
    "2MA": "2Macc",
    "3MA": "3Macc",
    "4MA": "4Macc",
    "1ES": "1Esd",
    "2ES": "2Esd",
    "MAN": "PrMan",
    "PS2": "AddPs",
    "ODA": "Odes",
    "PSS": "PssSol",
    "EZA": "4Ezra",
    "5EZ": "5Ezra",
    "6EZ": "6Ezra",
    "DAG": "DanGr",
    "PS3": "5ApocSyrPss",
    "2BA": "2Bar",
    "LBA": "EpBar",
    "JUB": "Jub",
    "ENO": "1En",
    "1MQ": "1Meq",
    "2MQ": "2Meq",
    "3MQ": "3Meq",
    "REP": "Reproof",
    "4BA": "4Bar",
    "LAO": "EpLao",
    # private use
    "XXA": "XXA",
    "XXB": "XXB",
    "XXC": "XXC",
    "XXD": "XXD",
    "XXE": "XXE",
    "XXF": "XXF",
    "XXG": "XXG",
    # Peripheral books
    "FRT": "FRONT",
    "INT": "INTRODUCTION",
    "BAK": "BACK",
    "CNC": "CONCORDANCE",
    "GLO": "GLOSSARY",
    "TDX": "INDEX",
    "NDX": "GAZETTEER",
    "OTH": "X-OTHER",
}

# noncanonical book id's
NONCANONICAL = {
    "FRONT": "front",
    "INTRODUCTION": "introduction",
    "XXA": "x-other-a",
    "XXB": "x-other-b",
    "XXC": "x-other-c",
    "XXD": "x-other-d",
    "XXE": "x-other-e",
    "XXF": "x-other-f",
    "XXG": "x-other-g",
    "BACK": "back",
    "CONCORDANCE": "concordance",
    "GLOSSARY": "glossary",
    "INDEX": "index",
    "GAZETTEER": "gazetteer",
    "X-OTHER": "x-other",
}

# list of books with one chapter
ONECHAP = {"Obad", "Phlm", "2John", "3John", "Jude"}


# -------------------------------------------------------------------------- #
# TAG MAPPINGS

# identification tags
IDTAGS = {
    r"\usfm": ("<!-- usfm - ", " -->"),
    r"\sts": ("", '<milestone type="x-usfm-sts" n="{}" />'),
    r"\toc1": ("", '<milestone type="x-usfm-toc1" n="{}" />'),
    r"\toc2": ("", '<milestone type="x-usfm-toc2" n="{}" />'),
    r"\toc3": ("", '<milestone type="x-usfm-toc3" n="{}" />'),
    r"\restore": ("<!-- restore - ", " -->"),
    # the osis 2.1.1 user manual says the value of h h1 h2 and h3 tags should
    # be in the short attribute of a title.
    # ************************************************************************
    # NOTE: These types of titles seem to be problematic when trying to import
    #       bibles for The SWORD Project. So alternative conversions have been
    #       implemented to work around the issue.
    # ************************************************************************
    # r'\h': ('', '<title type="runningHead" short="{}" />'),
    # r'\h1': ('', '<title type="runningHead" n="1" short="{}" />'),
    # r'\h2': ('', '<title type="runningHead" n="2" short="{}" />'),
    # r'\h3': ('', '<title type="runningHead" n="3" short="{}" />')
    # ************************************************************************
    r"\h": ("", '<milestone type="x-usfm-h" n="{}" />'),
    r"\h1": ("", '<milestone type="x-usfm-h1" n="{}" />'),
    r"\h2": ("", '<milestone type="x-usfm-h2" n="{}" />'),
    r"\h3": ("", '<milestone type="x-usfm-h3" n="{}" />'),
}

# the osis 2.1.1 user manual says the value of id, ide, and rem should be
# placed in description tags in the header.
# These are handled in a separate function. That's why they aren't included above.

# title tags
TITLETAGS = {
    # ---------------------------------------------------------
    # ##### SECTION TAGS ##### #
    r"\is": ('<title type="x-introduction">', "</title>"),
    r"\is1": ('<title type="x-introduction">', "</title>"),
    r"\is2": ('<title type="x-introduction">', "</title>"),
    r"\is3": ('<title type="x-introduction">', "</title>"),
    r"\is4": ('<title type="x-introduction">', "</title>"),
    #
    r"\ms": ("<title>", "</title>"),
    r"\ms1": ("<title>", "</title>"),
    r"\ms2": ("<title>", "</title>"),
    r"\ms3": ("<title>", "</title>"),
    r"\ms4": ("<title>", "</title>"),
    #
    r"\s": ("<title>", "</title>"),
    r"\s1": ("<title>", "</title>"),
    r"\s2": ("<title>", "</title>"),
    r"\s3": ("<title>", "</title>"),
    r"\s4": ("<title>", "</title>"),
    # ##### Semantic Whitespace ##### #
    r"\sd": ('<milestone type="x-usfm-sd" />', ""),
    r"\sd1": ('<milestone type="x-usfm-sd1" />', ""),
    r"\sd2": ('<milestone type="x-usfm-sd2" />', ""),
    r"\sd3": ('<milestone type="x-usfm-sd3" />', ""),
    r"\sd4": ('<milestone type="x-usfm-sd4" />', ""),
    # ---------------------------------------------------------
    # ##### INTRODUCTIONS ##### #
    r"\imt": ('<title type="main" subType="x-introduction">', "</title>"),
    r"\imt1": (
        '<title level="1" type="main" subType="x-introduction">',
        "</title>",
    ),
    r"\imt2": (
        '<title level="2" type="main" subType="x-introduction">',
        "</title>",
    ),
    r"\imt3": (
        '<title level="3" type="main" subType="x-introduction">',
        "</title>",
    ),
    r"\imt4": (
        '<title level="4" type="main" subType="x-introduction">',
        "</title>",
    ),
    r"\imt5": (
        '<title level="5" type="main" subType="x-introduction">',
        "</title>",
    ),
    r"\imte": ('<title type="main" subType="x-introduction">', "</title>"),
    r"\imte1": (
        '<title level="1" type="main" subType="x-introduction">',
        "</title>",
    ),
    r"\imte2": (
        '<title level="2" type="main" subType="x-introduction">',
        "</title>",
    ),
    r"\imte3": (
        '<title level="3" type="main" subType="x-introduction">',
        "</title>",
    ),
    r"\imte4": (
        '<title level="4" type="main" subType="x-introduction">',
        "</title>",
    ),
    r"\imte5": (
        '<title level="5" type="main" subType="x-introduction">',
        "</title>",
    ),
    # ##### Normal Title Section ##### #
    r"\mt": ('<title type="main">', "</title>"),
    r"\mt1": ('<title level="1" type="main">', "</title>"),
    r"\mt2": ('<title level="2" type="main">', "</title>"),
    r"\mt3": ('<title level="3" type="main">', "</title>"),
    r"\mt4": ('<title level="4" type="main">', "</title>"),
    r"\mt5": ('<title level="5" type="main">', "</title>"),
    r"\mte": ('<title type="main">', "</title>"),
    r"\mte1": ('<title level="1" type="main">', "</title>"),
    r"\mte2": ('<title level="2" type="main">', "</title>"),
    r"\mte3": ('<title level="3" type="main">', "</title>"),
    r"\mte4": ('<title level="4" type="main">', "</title>"),
    r"\mte5": ('<title level="5" type="main">', "</title>"),
    #
    r"\mr": ('<title type="scope"><reference>', "</reference></title>"),
    r"\sr": ('<title type="scope"><reference>', "</reference></title>"),
    r"\r": (
        '<title type="parallel"><reference type="parallel">',
        "</reference></title>",
    ),
    r"\d": ('<title type="psalm" canonical="true">', "</title>"),
    r"\sp": ("<speaker>", "</speaker>"),
    # ##### chapter cl tags ##### #
    #
    # This is the best way I know how to convert these tags.
    #
    # The osis user manual says to convert these to titles and use chapterLabel
    # for type in the title tag. That type is not allowed according to the osis
    # 2.1.1 schema though. So I use x-chapterLabel for the type instead.
    # NOTE: titles created in this manner don't work with The SWORD Project
    #       sofware and create problems with displaying other titles as well.
    #       So the conversion to titles is disabled for now and milestone
    #       markers are inserted instead.
    # r'\cl': ('<title type="x-chapterLabel" short="', '" />'),
    r"\cl": ('<milestone type="x-chapterLabel" n="', '" />'),
    # ##### chapter cd tags ##### #
    # the osis user manual says cd titles should be in an introduction div.
    r"\cd": (
        '<div type="introduction">\ufdd0<title type="x-description">',
        "</title>\ufdd0</div>",
    ),
    # ##### special features ##### #
    # the osis user manual says this should be in an lg tag of type doxology
    # with an l tag of type refrain.
    r"\lit": (
        '<lg type="doxology">\ufdd0<l type="refrain">',
        "</l>\ufdd0</lg>",
    ),
}

# paragraph and poetry/prose tags
PARTAGS = {
    # INTRODUCTIONS
    r"\iot": (r'<item type="x-head" subType="x-introduction">', r"</item>"),
    r"\io": (r'<item type="x-indent-1" subType="x-introduction">', r"</item>"),
    r"\io1": (
        r'<item type="x-indent-1" subType="x-introduction">',
        r"</item>",
    ),
    r"\io2": (
        r'<item type="x-indent-2" subType="x-introduction">',
        r"</item>",
    ),
    r"\io3": (
        r'<item type="x-indent-3" subType="x-introduction">',
        r"</item>",
    ),
    r"\io4": (
        r'<item type="x-indent-4" subType="x-introduction">',
        r"</item>",
    ),
    r"\ip": (r'<p subType="x-introduction">', r" </p>"),
    r"\im": (r'<p type="x-noindent" subType="x-introduction">', r" </p>"),
    r"\ipq": (r'<p type="x-quote" subType="x-introduction">', r" </p>"),
    r"\imq": (
        r'<p type="x-noindent-quote" subType="x-introduction">',
        r" </p>",
    ),
    r"\ipi": (r'<p type="x-indented" subType="x-introduction">', r" </p>"),
    r"\imi": (
        r'<p type="x-noindent-indented" subType="x-introduction">',
        r" </p>",
    ),
    r"\ili": (
        r'<item type="x-indent-1" subType="x-introduction">',
        r" </item>",
    ),
    r"\ili1": (
        r'<item type="x-indent-1" subType="x-introduction">',
        r" </item>",
    ),
    r"\ili2": (
        r'<item type="x-indent-2" subType="x-introduction">',
        r" </item>",
    ),
    r"\ipr": (r'<p type="x-right" subType="x-introduction">', r" </p>"),
    r"\iq": (r'<l level="1" subType="x-introduction">', r" </l>"),
    r"\iq1": (r'<l level="1" subType="x-introduction">', r" </l>"),
    r"\iq2": (r'<l level="2" subType="x-introduction">', r" </l>"),
    r"\iq3": (r'<l level="3" subType="x-introduction">', r" </l>"),
    r"\iex": (r'<div type="bridge" subType="x-introduction">', r"</div>"),
    r"\ie": (r"<!-- ie -->", r""),
    # ##### PARAGRAPH/POETRY
    r"\p": (r"<p>", r" </p>"),
    r"\m": (r'<p type="x-noindent">', r" </p>"),
    r"\po": (r'<p type="x-usfm-po">', r" </p>"),
    r"\pmo": (r'<p type="x-embedded-opening">', r" </p>"),
    r"\pm": (r'<p type="x-embedded">', r" </p>"),
    r"\pmc": (r'<p type="x-embedded-closing">', r" </p>"),
    r"\pmr": (r'<p type="x-right">', r" </p>"),
    r"\pi": (r'<p type="x-indented">', r" </p>"),
    r"\pi1": (r'<p type="x-indented-1">', r" </p>"),
    r"\pi2": (r'<p type="x-indented-2">', r" </p>"),
    r"\pi3": (r'<p type="x-indented-3">', r" </p>"),
    r"\pi4": (r'<p type="x-indented-4">', r" </p>"),
    r"\mi": (r'<p type="x-noindent-indented">', r" </p>"),
    r"\cls": (r"<closer>", r"</closer>"),
    r"\lh": (r'<p type="x-usfm-lh">', r"</p>"),
    r"\lf": (r'<p type="x-usfm-lf">', r"</p>"),
    r"\li": (r'<item type="x-indent-1">', r" </item>"),
    r"\li1": (r'<item type="x-indent-1">', r" </item>"),
    r"\li2": (r'<item type="x-indent-2">', r" </item>"),
    r"\li3": (r'<item type="x-indent-3">', r" </item>"),
    r"\li4": (r'<item type="x-indent-4">', r" </item>"),
    r"\lim": (r'<item type="x-usfm-lim">', r" </item>"),
    r"\lim1": (r'<item type="x-usfm-lim1">', r" </item>"),
    r"\lim2": (r'<item type="x-usfm-lim2">', r" </item>"),
    r"\lim3": (r'<item type="x-usfm-lim3">', r" </item>"),
    r"\lim4": (r'<item type="x-usfm-lim4">', r" </item>"),
    r"\pc": (r'<p type="x-center">', r" </p>"),
    r"\pr": (r'<p type="x-right">', r" </p>"),
    r"\ph": (r'<item type="x-indent-1">', r" </item>"),
    r"\ph1": (r'<item type="x-indent-1">', r" </item>"),
    r"\ph2": (r'<item type="x-indent-2">', r" </item>"),
    r"\ph3": (r'<item type="x-indent-3">', r" </item>"),
    # POETRY Markers
    r"\q": (r'<l level="1">', r" </l>"),
    r"\q1": (r'<l level="1">', r" </l>"),
    r"\q2": (r'<l level="2">', r" </l>"),
    r"\q3": (r'<l level="3">', r" </l>"),
    r"\q4": (r'<l level="4">', r" </l>"),
    r"\qr": (r'<l type="x-right">', r" </l>"),
    r"\qc": (r'<l type="x-center">', r" </l>"),
    r"\qa": (r'<title type="acrostic">', r"</title>"),
    r"\qd": (r'<l type="x-usfm-qd">', r"</l>"),
    r"\qm": (r'<l type="x-embedded" level="1">', r" </l>"),
    r"\qm1": (r'<l type="x-embedded" level="1">', r" </l>"),
    r"\qm2": (r'<l type="x-embedded" level="2">', r" </l>"),
    r"\qm3": (r'<l type="x-embedded" level="3">', r" </l>"),
    r"\qm4": (r'<l type="x-embedded" level="4">', r" </l>"),
    # sidebar markers... FIXED ELSEWHERE
    r"\esb": (r"<SIDEBAR>", ""),
    r"\esbe": (r"</SIDEBAR>", ""),
}

# other introduction and poetry tags
OTHERTAGS = {
    # selah is handled in a special manner…
    r"\qs ": "<selah>",
    r"\qs*": "</selah>",
    # these tags get special handling…
    r"\ie": "<!-- ie -->",  # handled with partags… may not need here…
    r"\ib ": "<!-- b -->",  # handled exactly like \b
    r"\b ": "<!-- b -->",
    r"\nb ": "<!-- nb -->",
    r"\nb": "<!-- nb -->",
    # translators chunk marker… this probably needs more changes
    r"\ts-s\*": " <!-- ts --> ",
    r"\ts-e\*": " <!-- ts --> ",
    r"\ts-s": " <!-- ts --> ",
    r"\ts-e": " <!-- ts --> ",
    r"\ts\*": " <!-- ts --> ",
    r"\ts": " <!-- ts --> ",
}

# table cell tags
CELLTAGS = {
    # header cells
    r"\th": ('<cell role="label">', "</cell>"),
    r"\th1": ('<cell role="label">', "</cell>"),
    r"\th2": ('<cell role="label">', "</cell>"),
    r"\th3": ('<cell role="label">', "</cell>"),
    r"\th4": ('<cell role="label">', "</cell>"),
    r"\th5": ('<cell role="label">', "</cell>"),
    r"\thr": ('<cell role="label" type="x-right">', "</cell>"),
    r"\thr1": ('<cell role="label" type="x-right">', "</cell>"),
    r"\thr2": ('<cell role="label" type="x-right">', "</cell>"),
    r"\thr3": ('<cell role="label" type="x-right">', "</cell>"),
    r"\thr4": ('<cell role="label" type="x-right">', "</cell>"),
    r"\thr5": ('<cell role="label" type="x-right">', "</cell>"),
    # normal cells
    r"\tc": ("<cell>", "</cell>"),
    r"\tc1": ("<cell>", "</cell>"),
    r"\tc2": ("<cell>", "</cell>"),
    r"\tc3": ("<cell>", "</cell>"),
    r"\tc4": ("<cell>", "</cell>"),
    r"\tc5": ("<cell>", "</cell>"),
    r"\tcr": ('<cell type="x-right">', "</cell>"),
    r"\tcr1": ('<cell type="x-right">', "</cell>"),
    r"\tcr2": ('<cell type="x-right">', "</cell>"),
    r"\tcr3": ('<cell type="x-right">', "</cell>"),
    r"\tcr4": ('<cell type="x-right">', "</cell>"),
    r"\tcr5": ('<cell type="x-right">', "</cell>"),
}

# special text and character style tags.
# \wj tags are handled with a special function. Don't add it here.
SPECIALTEXT = {
    # tags for special text
    r"\add": ('<transChange type="added">', "</transChange>"),
    r"\addpn": (
        '<transChange type="added" subType="x-usfm-addpn">',
        "</transChange>",
    ),
    r"\nd": ("<divineName>", "</divineName>"),
    r"\pn": ("<name>", "</name>"),
    r"\qt": ('<seg type="otPassage">', "</seg>"),
    r"\sig": ("<signed>", "</signed>"),
    r"\ord": ('<hi type="super">', "</hi>"),
    r"\tl": ("<foreign>", "</foreign>"),
    r"\bk": ('<name type="x-usfm-bk">', "</name>"),
    r"\k": ('<seg type="keyword">', "</seg>"),
    r"\dc": ('<transChange type="added" editions="dc">', "</transChange>"),
    r"\sls": ('<foreign type="x-secondaryLanguage">', "</foreign>"),
    r"\+add": (
        '<seg type="x-nested"><transChange type="added">',
        "</transChange></seg>",
    ),
    r"\+addpn": (
        '<seg type="x-nested"><transChange type="added" subType="x-usfm-addpn">',
        "</transChange></seg>",
    ),
    r"\+nd": ('<seg type="x-nested"><divineName>', "</divineName></seg>"),
    r"\+pn": ('<seg type="x-nested"><name>', "</name></seg>"),
    r"\+qt": ('<seg type="x-nested"><seg type="otPassage">', "</seg></seg>"),
    r"\+sig": ('<seg type="x-nested"><signed>', "</signed></seg>"),
    r"\+ord": ('<seg type="x-nested"><hi type="super">', "</hi></seg>"),
    r"\+tl": ('<seg type="x-nested"><foreign>', "</foreign></seg>"),
    r"\+bk": ('<seg type="x-nested"><name type="x-usfm-bk">', "</name></seg>"),
    r"\+k": ('<seg type="x-nested"><seg type="keyword">', "</seg></seg>"),
    r"\+dc": (
        '<seg type="x-nested"><transChange type="added" editions="dc">',
        "</transChange></seg>",
    ),
    r"\+sls": (
        '<seg type="x-nested"><foreign type="x-secondaryLanguage">',
        "</foreign></seg>",
    ),
    # tags for character styles
    r"\em": ('<hi type="emphasis">', "</hi>"),
    r"\bd": ('<hi type="bold">', "</hi>"),
    r"\it": ('<hi type="italic">', "</hi>"),
    r"\bdit": ('<hi type="bold"><hi type="italic">', "</hi></hi>"),
    r"\no": ('<hi type="normal">', "</hi>"),
    r"\sc": ('<hi type="small-caps">', "</hi>"),
    r"\sup": ('<hi type="super">', "</hi>"),
    r"\+em": ('<seg type="x-nested"><hi type="emphasis">', "</hi></seg>"),
    r"\+bd": ('<seg type="x-nested"><hi type="bold">', "</hi></seg>"),
    r"\+it": ('<seg type="x-nested"><hi type="italic">', "</hi></seg>"),
    r"\+bdit": (
        '<seg type="x-nested"><hi type="bold"><hi type="italic">',
        "</hi></hi></seg>",
    ),
    r"\+no": ('<seg type="x-nested"><hi type="normal">', "</hi></seg>"),
    r"\+sc": ('<seg type="x-nested"><hi type="small-caps">', "</hi></seg>"),
    r"\+sup": ('<seg type="x-nested"><hi type="super">', "</hi></seg>"),
    # a few stray list tags that work well being handled in this section.
    r"\lik": ('<seg type="x-usfm-lik">', "</seg>"),
    r"\liv": ('<seg type="x-usfm-liv">', "</seg>"),
    r"\liv1": ('<seg type="x-usfm-liv1">', "</seg>"),
    r"\liv2": ('<seg type="x-usfm-liv2">', "</seg>"),
    r"\liv3": ('<seg type="x-usfm-liv3">', "</seg>"),
    r"\liv4": ('<seg type="x-usfm-liv4">', "</seg>"),
    r"\litl": ('<seg type="x-usfm-litl">', "</seg>"),
    # a few stray introduction and poetry tags that
    # work well being handled in this section.
    r"\ior": ('<reference subType="x-introduction">', "</reference>"),
    r"\iqt": ('<q subType="x-introduction">', "</q>"),
    r"\rq": ('<reference type="source">', "</reference>"),
    r"\qac": ('<hi type="acrostic">', "</hi>"),
    r"\+ior": (
        '<seg type="x-nested"><reference subType="x-introduction">',
        "</reference></seg>",
    ),
    r"\+iqt": (
        '<seg type="x-nested"><q subType="x-introduction">',
        "</q></seg>",
    ),
    r"\+rq": (
        '<seg type="x-nested"><reference type="source">',
        "</reference></seg>",
    ),
    r"\+qac": ('<seg type="x-nested"><hi type="acrostic">', "</hi></seg>"),
    # ca and va tags... because simpler handling was needed...
    r"\ca": ('<milestone type="x-usfm-ca" n="', '" />'),
    r"\va": ('<milestone type="x-usfm-va" n="', '" />'),
    # cp and vp tags... because simpler handling was needed...
    r"\cp": ('<milestone type="x-usfm-cp" n="', '" />'),
    r"\vp": ('<milestone type="x-usfm-vp" n="', '" />'),
}

# special features
# do not add \lit here... that is handled with TITLETAGS.
FEATURETAGS = {
    r"\pro": ('<milestone type="x-usfm-pro" n="', '" /> '),
    r"\rb": ('<milestone type="x-usfm-rb" n="', '" /> '),
    r"\rt": ('<milestone type="x-usfm-rt" n="', '" /> '),
    r"\ndx": ("", '<index index="Index" level1="{}" /> '),
    r"\png": ("", '<index index="Geography" level1="{}" />'),
    r"\w": ("", '<index index="Glossary" level1="{}" />'),
    r"\wa": ("", '<index index="Aramaic" level1="{}" />'),
    r"\wg": ("", '<index index="Greek" level1="{}" />'),
    r"\wh": ("", '<index index="Hebrew" level1="{}" />'),
    r"\+pro": ('<milestone type="x-usfm-pro" n="', '" /> '),
    r"\+rb": ('<milestone type="x-usfm-rb" n="', '" /> '),
    r"\+rt": ('<milestone type="x-usfm-rt" n="', '" /> '),
    r"\+ndx": ("", '<index index="Index" level1="{}" /> '),
    r"\+png": ("", '<index index="Geography" level1="{}" />'),
    r"\+w": ("", '<index index="Glossary" level1="{}" />'),
    r"\+wa": ("", '<index index="Aramaic" level1="{}" />'),
    r"\+wg": ("", '<index index="Greek" level1="{}" />'),
    r"\+wh": ("", '<index index="Hebrew" level1="{}" />'),
    # stray xt tags are handled here
    r"\xt": ("<reference>", "</reference>"),
    r"\+xt": ('<seg type="x-nested"><reference>', "</reference></seg>"),
    # This should be converted to an 'a' tag. More work needs
    # to be done before that can happen though.
    r"\jmp": ('<seg type="x-usfm-jmp">', "</seg>"),
    r"\+jmp": ('<seg type="x-usfm-jmp" subType="x-nested">', "</seg>"),
}

# special strongs feature tag...
STRONGSTAG = ("<w {}{}>", "</w>")

# footnote and cross reference tags
NOTETAGS = {
    r"\f": ('<note placement="foot">\ufdd2', "\ufdd3</note>"),
    r"\fe": ('<note placement="end">\ufdd2', "\ufdd3</note>"),
    r"\x": ('<note type="crossReference">', "</note>"),
    r"\ef": (
        '<note placement="foot" subType="x-extended">\ufdd2',
        "\ufdd3</note>",
    ),
    r"\ex": ('<note type="crossReference" subType="x-extended">', "</note>"),
}

# tags internal to footnotes and cross references
# * If any of these ever start with anything other than \f or \x *
# * then the NOTEFIXRE regex will need to be modified.           *
NOTETAGS2 = {
    r"\fm": ('<hi type="super">', "</hi>"),
    r"\fdc": ('<seg editions="dc">', "</seg>"),
    r"\fr": ('<reference type="annotateRef">', "</reference>"),
    r"\fk": ("<catchWord>", "</catchWord>"),
    r"\fq": ("<catchWord>", "</catchWord>"),
    r"\fqa": ('<rdg type="alternate">', "</rdg>"),
    # I think this should be label... but that doesn't validate.
    # r'\fl': ('<label>', '</label>'),
    r"\fl": ('<seg type="x-usfm-fl">', "</seg>"),
    r"\fv": ('<hi type="super">', "</hi>"),
    r"\ft": ("", ""),
    r"\xot": ('<seg editions="ot">', "</seg>"),
    r"\xnt": ('<seg editions="nt">', "</seg>"),
    r"\xdc": ('<seg editions="dc">', "</seg>"),
    r"\xk": ("<catchWord>", "</catchWord>"),
    r"\xq": ("<catchWord>", "</catchWord>"),
    # there is no mapping in the osis manual for the xo usfm tag
    r"\xo": (
        '<reference type="annotateRef" subType="x-origin">',
        "</reference>",
    ),
    r"\xop": ('<seg type="x-usfm-xop">', "</seg>"),
    r"\xta": ('<seg type="x-usfm-xta">', "</seg>"),
    r"\xt": ("<reference>", "</reference>"),
    # nested versions of internal footnote tags
    r"\+fm": ('<seg type="x-nested"><hi type="super">', "</hi></seg>"),
    r"\+fdc": ('<seg type="x-nested"><seg editions="dc">', "</seg></seg>"),
    r"\+fr": (
        '<seg type="x-nested"><reference type="annotateRef">',
        "</reference></seg>",
    ),
    r"\+fk": ('<seg type="x-nested"><catchWord>', "</catchWord></seg>"),
    r"\+fq": ('<seg type="x-nested"><catchWord>', "</catchWord></seg>"),
    r"\+fqa": ('<seg type="x-nested"><rdg type="alternate">', "</rdg></seg>"),
    r"\+fl": ('<seg type="x-nested"><seg type="x-usfm-fl">', "</seg></seg>"),
    r"\+fv": ('<seg type="x-nested"><hi type="super">', "</hi></seg>"),
    r"\+ft": ("", ""),
    r"\+xot": ('<seg type="x-nested"><seg editions="ot">', "</seg></seg>"),
    r"\+xnt": ('<seg type="x-nested"><seg editions="nt">', "</seg></seg>"),
    r"\+xdc": ('<seg type="x-nested"><seg editions="dc">', "</seg></seg>"),
    r"\+xk": ('<seg type="x-nested"><catchWord>', "</catchWord></seg>"),
    r"\+xq": ('<seg type="x-nested"><catchWord>', "</catchWord></seg>"),
    r"\+xo": (
        '<seg type="x-nested"><reference type="annotateRef" subType="x-origin">',
        "</reference></seg>",
    ),
    r"\+xop": ('<seg type="x-nested"><seg type="x-usfm-xop">', "</seg></seg>"),
    r"\+xta": ('<seg type="x-nested"><seg type="x-usfm-xta">', "</seg></seg>"),
    r"\+xt": ('<seg type="x-nested"><reference>', "</reference></seg>"),
}

# -------------------------------------------------------------------------- #

# defined attributes for tags
DEFINEDATTRIBUTES = {
    r"\w": ("lemma", "strong", "srcloc"),
    r"\+w": ("lemma", "strong", "srcloc"),
    r"\xt": ("link-ref"),
    r"\+xt": ("link-ref"),
    r"\fig": ("alt", "src", "size", "loc", "copy", "ref"),
    r"\jmp": ("link-href", "link-title", "link-name"),
    r"\+jmp": ("link-href", "link-title", "link-name"),
    r"\qt-s": ("id", "who"),
    r"\qt-e": ("id"),
    r"\periph": ("id"),
}

# defaultattributes for tags
# x-default will be used as the default for undefined default attributes
DEFAULTATTRIBUTES = {
    r"\w": "lemma",
    r"\+w": "lemma",
    r"\xt": "link-ref",
    r"\+xt": "link-ref",
}

# -------------------------------------------------------------------------- #
# REGULAR EXPRESSIONS

# create a function to squeeze all regular spaces, carriage returns,
# and newlines into a single space.
SQUEEZE = partial(re.sub, r"[ \t\n\r]+", " ", flags=re.U + re.M + re.DOTALL)

# matches special text and character styles
# Automatically build SPECIALTEXTRE regex string from SPECIALTEXT dict.
SPECIALTEXTRE_S = r"""
        # put special text tags into a named group called 'tag'
        (?P<tag>

            # tags always start with a backslash and may have a + symbol which
            # indicates that it's a nested character style.
            \\\+?

            # match the tags we want to match.
            (?:{})
        )

        # there is always at least one space separating the tag and the content
        \s+

        # put the tag content into a named group called 'osis'
        (?P<osis>.*?)

        # tag end marker
        (?P=tag)\*
    """.format(
    "|".join([_.replace("\\", "") for _ in SPECIALTEXT if not _.startswith(r"\+")])
)
SPECIALTEXTRE = re.compile(SPECIALTEXTRE_S, re.U + re.VERBOSE)
del SPECIALTEXTRE_S

# match z tags that have both a start and end marker
ZTAGS_S = r"""
        # put z tags that have a start and end marker into named group 'tag'
        (?P<tag>

            # tags always start with a backslash
            \\

            # match alphanumeric characters
            z(?:[A-Za-z0-9]+)
        )

        # there is always at least one space separating the tag and the content
        \s+

        # put the tag content into a named group called 'osis'
        (?P<osis>.*?)

        # tag end marker
        (?P=tag)\*
    """
ZTAGSRE = re.compile(ZTAGS_S, re.U + re.VERBOSE)
del ZTAGS_S

# match milestone z tags
ZTAGS2_S = r"""
    # put z tag content in a named group 'tag'
    (?P<tag>

        # tags start with a backslash
        \\

        # match alphanumeric characters and hyphen
        z(?:[A-Za-z0-9\-]+)

        # there may be a space
        \s*

        # there may be attributes before the end tag
        .*?

        # tag end marker
        \\\*
    )
"""
ZTAGS2RE = re.compile(ZTAGS2_S, re.U + re.VERBOSE)
del ZTAGS2_S

# matches special feature tags
# Automatically build SPECIALFEATURESRE regex string from FEATURETAGS dict.
SPECIALFEATURESRE_S = r"""
        # put the special features tags into a named group called 'tag'
        (?P<tag>

            # tags always start with a backslash and may have a + symbol which
            # indicates that it's a nested character style.
            \\\+?

            # this matches all of the known usfm special features except
            # for fig which is handled in a different manner.
            (?:{})
        )

        # there is always at least one space separating the tag and the content
        \s+

        # put the tag content into a named group called 'osis'
        (?P<osis>.*?)

        # tag end marker
        (?P=tag)\*
    """.format(
    "|".join([_.replace("\\", "") for _ in FEATURETAGS if not _.startswith(r"\+")])
)
SPECIALFEATURESRE = re.compile(SPECIALFEATURESRE_S, re.U + re.VERBOSE)
del SPECIALFEATURESRE_S

# regex used in footnote/crossref functions
# Automatically build NOTERE regex string from NOTETAGS dict.
NOTERE_S = r"""
        # put the footnote and cross reference markers into a named group
        # called 'tag'
        (?P<tag>

            # tags always start with a backslash
            \\

            # this matches the usfm footnote and cross reference markers.
            (?:{})
        )

        # there is always at least one space following the tag.
        \s+

        # footnote caller (currently ignored by this script)
        \S

        # there is always at least one space following the caller
        \s+

        # put the tag content into a named group called 'osis'
        (?P<osis>.*?)

        # footnote / cross reference end tag
        (?P=tag)\*
    """.format(
    "|".join([_.replace("\\", "") for _ in NOTETAGS if not _.startswith(r"\+")])
)
NOTERE = re.compile(NOTERE_S, re.U + re.VERBOSE)
del NOTERE_S
# ---
# Automatically build NOTEFIXRE regex string from NOTETAGS2 dict.
NOTEFIXRE_S = r"""
        (
            # tags always start with a backslash and may have a + symbol which
            # indicates that it's a nested character style.
            \\\+?

            # this matches all of the footnote/crossref specific usfm tags that
            # appear inside footnotes and cross references.
            (?:{})
        )

        # there is always at least one space following the tag.
        \s+

        # This matches the content of the tag
        (.*?)

        # This marks the end of the tag. It matches against either the
        # start of an additional tag or the end of the note.
        (?=\\\+?[fx]|</note)
    """.format(
    "|".join([_.replace("\\", "") for _ in NOTETAGS2 if not _.startswith(r"\+")])
)
NOTEFIXRE = re.compile(NOTEFIXRE_S, re.U + re.VERBOSE)
del NOTEFIXRE_S

# match \vp tags
VPRE = re.compile(
    r"""
        \\vp
        \s+
        (?P<num>\S+)
        \s*
        \\vp\*
        \s*
    """,
    re.U + re.VERBOSE,
)

# regex for matching against \ca or \va usfm tags.
CVARE = re.compile(
    r"""
        # put the tag we match into a named group called tag
        (?P<tag>

            # tags always start with a backslash
            \\

            # match against either ca or va
            (?:ca|va)
        )

        # there is always at least one space following the tag
        \s+

        # put the number into a named group called num
        (?P<num>\S+)

        # make sure the end tag matched the start tag...
        (?P=tag)\*

        # there may or may not be space following this tag.
        \s*
    """,
    re.U + re.VERBOSE,
)

# regex for finding usfm tags
USFMRE = re.compile(
    r"""
    # the first character of a usfm tag is always a backslash
    \\

    # a plus symbol marks the start of a nested character style.
    # this may or may not be present.
    \+?

    # tag names are ascii letters
    [A-Za-z]+

    # tags may or may not be numbered
    \d?

    # a word boundary to mark the end of our tags.
    \b

    # character style closing tags ends with an asterisk.
    \*?

""",
    re.U + re.VERBOSE,
)


ATTRIBRE = re.compile(r' +(\S+=[\'"])', re.U + re.DOTALL)


# -------------------------------------------------------------------------- #
# VARIABLES USED BY REFLOW ROUTINE

# set of paragraph style tags built MOSTLY from other lists above...
# this is used by reflow to reformat the input for processing
# * chapter paragraph tags are omitted because we handle them differently
PARFLOW = set(
    chain(
        IDTAGS.keys(),
        TITLETAGS.keys(),
        PARTAGS.keys(),
        [r"\tr", r"\pb", r"\periph", r"\b", r"\c", r"\cl", r"\cd"],
    )
)

# poetry/prose tags... used by reflow subroutine below.
# this is used by reflow to test if we have paragraph markup.
PARCHECK = {_ for _ in PARTAGS if _ not in (r"\iex", r"\ie", r"\qa")}

# title tags... used by reflow subroutine below.
# use TITLETAGS keys to eliminate unnecessary duplication
TITLEFLOW = set(TITLETAGS.keys())

# -------------------------------------------------------------------------- #
# VARIABLES USED BY POSTPROCESS ROUTINE

OSISITEM = set(
    chain({_[0] for _ in PARTAGS.items() if _[0].startswith("<item ")}, ["<item>"])
)
OSISL = set(chain({_[0] for _ in PARTAGS.items() if _[0].startswith("<l ")}, ["<l>"]))

# -------------------------------------------------------------------------- #

# xml 1.1 schema...
XMLSCHEMA = b"""
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
FeTrUPnMMRdyRThQkELTDGM=
"""

# osis 2.1.1 schema...
# compressed with bzip2 and base64 encoded.
SCHEMA = b"""
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
OFCQJyEEPw==
"""

# -------------------------------------------------------------------------- #

# logging.basicConfig(format="%(levelname)s: %(message)s")
logging.basicConfig(format="%(message)s")
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.WARNING)

# -------------------------------------------------------------------------- #


def convertcl(text: str) -> str:
    """
    CL tag format conversion.

    Convert cl tags that appear only before chapter one to
    the form that appears after each chapter marker.

    """
    lines = text.split("\n")

    # count number of cl tags in text
    clcount = len([_ for _ in lines if _.startswith(r"\cl ")])

    # test for presence of only 1 cl marker.
    if clcount == 1:
        chaplines = [_ for _ in range(len(lines)) if lines[_].startswith(r"\c ")]

        # get cl marker line if it precedes chapter 1 and add this after
        # each chapter marker in the book.
        if lines[chaplines[0] - 1].startswith(r"\cl "):
            clmarker = lines[chaplines[0] - 1]
            lines[chaplines[0] - 1] = ""
            for i in reversed(chaplines):
                cnumber = lines[i].split(" ")[1]
                lines.insert(i + 1, " ".join([clmarker, cnumber]))

    # return our lines with converted cl tags.
    return "\n".join(lines)


def reflow(flowtext: str) -> str:
    """
    Reflow text for Processing.

    Place all paragraph style tags on their own line.
    This makes it significantly easier to handle paragraph markup.

    """
    # ####################################################################### #
    # The titlepar function depends on how this routine was written in order  #
    # to function properly. Don't make changes here unless you know what      #
    # you're doing and understand the ramifications in relation to how the    #
    # titlepar function operates!                                             #
    # ####################################################################### #

    def manglecheck(text: str) -> bool:
        """Check to see if we have paragraph markup."""
        return any(
            re.search(r"\\{}\b".format(_.lstrip(r"\\")), text, re.U + re.M + re.DOTALL)
            for _ in PARCHECK
        )

    def endmark(text: str) -> str:
        """Mark end of cl, sp, and qa tags."""
        textlines = (
            f"{_}\ufdd4" if _[0:4] in {r"\cl ", r"\sp ", r"\qa "} else _
            for _ in text.split("\n")
        )
        return "\n".join([f"{_}\ufdd5" if _[0:4] == r"\cp " else _ for _ in textlines])

    def reflowpar(text: str) -> str:
        """Put (almost) all paragraph tags on separate lines."""
        for _ in PARFLOW:
            if _ in text:
                text = text.replace(f"{_} ", f"\n{_} ")
        return text

    def fixlines(text: str) -> str:
        """Fix various potential issues with lines of text."""
        return "\n".join(
            [
                (
                    _.replace("\\v ", "\n\v ")
                    if _.split(" ", maxsplit=1)[0]
                    in {
                        r"\is ",
                        r"\is1 ",
                        r"\is2 ",
                        r"\is3 ",
                        r"\is4 ",
                        r"\is5 ",
                        r"\ms ",
                        r"\ms1 ",
                        r"\ms2 ",
                        r"\ms3 ",
                        r"\ms4 ",
                        r"\ms5 ",
                        r"\s ",
                        r"\s1 ",
                        r"\s2 ",
                        r"\s3",
                        r"\s4 ",
                        r"\s5 ",
                        r"\th ",
                        r"\th1 ",
                        r"\th2 ",
                        r"\th3 ",
                        r"\th4 ",
                        r"\th5 ",
                        r"\th6 ",
                        r"\th7 ",
                        r"\th8 ",
                        r"\th9 ",
                        r"\tc ",
                        r"\tc1 ",
                        r"\tc2 ",
                        r"\tc3 ",
                        r"\tc4 ",
                        r"\tc5 ",
                        r"\tc6 ",
                        r"\tc7 ",
                        r"\tc8 ",
                        r"\tc9 ",
                    }
                    else _
                )
                for _ in text.split("\n")
            ]
        )

    # test for paragraph markup before mangling the text
    mangletext = manglecheck(flowtext)

    # remove leading and trailing whitespace, mark end of cl sp and qa tags.
    # prepare to process text with paragraph formatting
    # put (almost) all paragraph style tags on separate lines
    flowtext = reflowpar(SQUEEZE(endmark(flowtext.strip())))

    for _ in (
        # always add newline after \ie
        (r"\ie ", "\\ie\n"),
        # always put a space before \cp and \ca tags
        (r"\cp", r" \cp"),
        (r"\ca", r" \ca"),
    ):
        if _[0] in flowtext:
            flowtext = flowtext.replace(_[0], _[1])

    # fix various possible issues in text lines.
    flowtext = fixlines(flowtext)

    # process text without paragraph markup (may not work. needs testing.)
    if not mangletext:
        # force some things  onto newlines.
        flowtext = flowtext.replace("\\c ", "\n\\c ").replace("\\v ", "\n\\v ")

        # make sure all lines start with a usfm tag...
        lines = flowtext.split("\n")
        for _ in range(len(lines) - 1, 0, -1):
            if not lines[_].startswith("\\"):
                lines[_ - 1] = f"{lines[_ - 1]} {lines[1]}"
                lines.pop(_)
        flowtext = "\n".join(lines)

        # remove some newlines that we don't want...
        flowtext = (
            flowtext.replace("\n\\ca", " \\ca")
            .replace("\n\\cp", " \\cp")
            .replace("\n\\va", " \\va")
            .replace("\n\\vp", " \\vp")
        )

    # fix newline issue
    if "\ufdd4" in flowtext:
        flowtext = flowtext.replace("\ufdd4", "\n")

    # add custom end marker for cp tags for easier processing
    if "\ufdd5" in flowtext:
        flowtext = flowtext.replace("\ufdd5", r"\cp*")

    # done
    return flowtext


def getbookid(text: str) -> str | None:
    """Get book id from file text."""
    lines = [_ for _ in text.split("\n") if _.startswith("\\id ")]
    bookid = None if not lines else lines[0].split()[1].strip()
    return None if not bookid else BOOKNAMES.get(bookid, f"* {bookid}")


def getencoding(text: bytes) -> str | None:
    """Get encoding from file text."""
    lines = [_.decode("utf8") for _ in text.split(b"\n") if _.startswith(b"\\ide")]
    return "utf_8_sig" if not lines else lines[0].partition(" ")[2].lower().strip()


def markintroend(lines: list[str]) -> list[str]:
    """
    Mark end of introductions.

    Loop through lines of text and mark start and end of introductions
    to aid in adding div's to introduction sections.

    """
    newlines = []
    intro = False
    for i in enumerate(lines):
        tmp = i[1].partition(" ")
        if tmp[0][0:3] == r"\ie":
            intro = False
            newlines.append(i[1])
            newlines.append("\ufde1")
        elif tmp[0][:3] in {
            r"\ib",
            r"\il",
            r"\im",
            r"\io",
            r"\ip",
            r"\iq",
            r"\is",
            r"\ie",
        }:
            if not intro:
                newlines.append("\ufde0")
                intro = True
            newlines.append(i[1])
        elif intro:
            intro = False
            newlines.append(i[1])
            newlines.append("\ufde1")
        else:
            newlines.append(i[1])

    if intro:
        newlines.append("\ufde1")

    return newlines


def parseattributes(tag: str, tagtext: str) -> tuple[str, str, Any, bool]:
    """Separate attributes from text in usfm."""
    # split attributes from text
    text, _, attributestring = tagtext.partition("|")
    attribs: dict[str, str] = {}

    # extract attributes
    if "=" not in attributestring:
        attribs[DEFAULTATTRIBUTES.get(tag, "x-default")] = attributestring
    else:
        tmp = ATTRIBRE.sub("\ufde2\\1", attributestring)
        for _ in tmp.split("\ufde2"):
            attr = _.partition("=")
            attribs[attr[0]] = attr[2].strip('"')

    # attribute validity check
    isinvalid = (
        (
            len(
                [
                    _
                    for _ in attribs
                    if _ not in DEFINEDATTRIBUTES[tag] and not _.startswith("x-")
                ]
            )
            > 0
        )
        if tag in DEFINEDATTRIBUTES
        else len([_[:2] for _ in attribs if _.startswith("x-")]) > 0
    )

    return text, attributestring, attribs, isinvalid


# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #


def c2o_getdescription(text: str) -> tuple[str, str]:
    """Extract id, ide, and rem lines from text to use as osis description."""
    lines = text.split("\n")
    descriptionlines = [
        (_.partition(" "))
        for _ in lines
        if _.startswith(r"\id ") or _.startswith(r"\ide ") or _.startswith(r"\rem ")
    ]
    newtext = "\n".join(
        [_ for _ in lines if (_.partition(" ")) not in descriptionlines]
    )
    description = "\n".join(
        [
            f'<description type="usfm" subType="x-{_[0][1:].strip()}">{_[2].strip()}</description>'
            for _ in descriptionlines
        ]
    )
    return description, newtext


def c2o_preprocess(text: str) -> str:
    """Preprocess text."""
    # preprocessing...
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "%gt;")
        .replace("~", "\u00a0")
        .replace(r"//", '<lb type="x-optional" />')
        .replace(r"\pb ", '<milestone type="pb" />')
        .replace(r"\pb", '<milestone type="pb" />')
    )


def c2o_identification(text: str) -> str:
    """
    Process identification tags.

    sts, h, h1, h2, h3, toc1, toc2, toc3, restore, usfm.
    handling of id, ide, and rem are done elsewhere.

    """
    line = text.partition(" ")
    if line[0] in IDTAGS:
        text = (
            f"{IDTAGS[line[0]][1].format(line[2].strip())}\ufdd0"
            if IDTAGS[line[0]][0] == ""
            else f"{IDTAGS[line[0]][0]}{line[2].strip()}{IDTAGS[line[0]][1]}\ufdd0"
        )
    return text


def c2o_titlepar(blocktext: str, bookid: str) -> str:
    """Process title and paragraph tags."""
    # local copies of global variables.
    partags = PARTAGS
    othertags = OTHERTAGS
    celltags = CELLTAGS
    titletags = TITLETAGS

    def titles_and_sections(line: list[str]) -> str:
        """Process titles and sections."""
        # make sure titles don't end with a \b or an \ib tag
        line[2] = line[2].strip()
        if line[2].endswith(r"\b"):
            line[2] = line[2][:-2]
        elif line[2].endswith(r"\ib"):
            line[2] = line[2][:-3]

        # is there ever a reason for a \b tag to appear in a title?
        # if there is, I will have to add \b processing here.

        if line[0] == r"\periph":
            # handle usfm attributes if present
            osis, attributetext, attributes, isvalid = {
                True: parseattributes(r"periph", line[2]),
                False: (line[2], None, {}, True),
            }["|" in line[2]]
            del isvalid  # make pylint happy
            if attributetext is not None:
                attributetext = f"<!-- USFM Attributes - {attributetext} -->"
            starttag = titletags[line[0]][0]
            endtag = titletags[line[0]][1]

            # process id attribute
            if "id" in attributes:
                idattribute = f' n="{attributes["id"]}">'
                starttag = starttag.replace(">", idattribute)

            # finished processing periph now...
            text = "\ufdd0<!-- {} -->{}{}{}{}\ufdd0".format(
                line[0].replace("\\", ""),
                starttag,
                osis.strip(),
                endtag,
                attributetext,
            )
        else:
            text = "\ufdd0<!-- {} -->{}{}{}\ufdd0".format(
                line[0].replace("\\", ""),
                titletags[line[0]][0],
                line[2].strip(),
                titletags[line[0]][1],
            )
        return text

    def paragraphs(line: list[str]) -> str:
        """Process paragraph tags."""
        pstart, pend = partags[line[0]]
        btag = ""
        if pstart.startswith("<p"):
            pstart = f"{pstart}\ufdd0"
            pend = f"\ufdd0{pend}\ufdd0"

        text = f"{pstart}{line[2].strip()}"
        # handle b  and ib tags in paragraphs and poetry...
        if text.endswith("\\b") or text.endswith("\\ib"):
            text = text.rstrip("\\b").rstrip("\\ib")
            btag = "<!-- b -->"
        elif r"\b " in text or r"\ib" in text:
            text = text.replace("\\b ", "<!-- b -->").replace("\\ib ", "<!-- b -->")

        # finish paragraphs.
        return f"{text}{pend}{btag}\ufdd0"

    def tables(line: list[str]) -> str:
        """Process tables."""
        line[2] = (
            line[2]
            .strip()
            .rstrip("\\b")
            .strip()
            .replace(r"\th", "\n\\th")
            .replace(r"\tc", "\n\\tc")
        )
        cells = line[2].split("\n")
        for i in enumerate(cells):
            tmp = list(cells[i[0]].partition(" "))
            if tmp[0] in celltags:
                cells[i[0]] = (
                    f"{celltags[tmp[0]][0]}{tmp[2].strip()}{celltags[tmp[0]][1]}"
                )
        return f"<row>{''.join(cells)}</row>\ufdd0"

    def selah(text: str) -> str:
        """Handle selah."""
        selahfix = (
            _
            for _ in text.replace("<l", "\n<l").replace("</l>", "</l>\n").split("\n")
            if _ != ""
        )
        selahfix2 = (
            (
                _.replace("<selah>", '</l><l type="selah">')
                .replace("</selah>", "</l><l>")
                .replace("<l> </l>", "")
                .replace("<l>  </l>", "")
                if _.startswith(r"<l") and "<selah>" in _
                else _
            )
            for _ in selahfix
        )
        return " ".join(
            [
                (
                    _.replace("<selah>", '<lg><l type="selah">').replace(
                        "</selah>", "</l></lg>"
                    )
                    if "<selah>" in _ or "</selah>" in _
                    else _
                )
                for _ in selahfix2
            ]
        )

    # add periph tag to titletags if book being processed
    # is a  peripheral or private use book.
    if bookid in {
        "FRONT",
        "INTRODUCTION",
        "BACK",
        "X-OTHER",
        "XXA",
        "XXB",
        "XXC",
        "XXD",
        "XXE",
        "XXF",
        "XXG",
    }:
        titletags[r"\periph"] = ('<title type="main">', "</title>")

    # ################################################################### #
    # NOTE: I've not seen any kind of documentation to suggest that usage
    #       of the usfm \d tag outside of psalms is valid.
    #
    #       Additionally every other converter that I've looked at does not
    #       make a special exception for \d tags outside of psalms.
    #       Neither the deprecated perl script nor the currently preferred
    #       python script hosted by crosswire.org do this. Haiola does not
    #       do this. Bibledit does not do this.
    #
    #       Anyway, it takes 2 lines. It was trivial. So, against my better
    #       judgment I've provided an implementation of this change as was
    #       requested.
    #
    #       Uncomment the next 2 lines of code to enable handling of
    #       incorrect use of this tag.
    #
    # if bookid != "Ps":
    #     titletags[r'\d'] = ('<title canonical="true">', '</title>')
    # ################################################################### #

    blockline = list(blocktext.partition(" "))

    # process titles and sections
    if blockline[0] in titletags:
        blocktext = titles_and_sections(blockline)

    # process paragraphs
    elif blockline[0] in partags:
        blocktext = paragraphs(blockline)

    # process tables
    elif blockline[0] == r"\tr":
        blocktext = tables(blockline)

    # other title, paragraph, intro tags
    for _ in othertags.items():
        blocktext = blocktext.replace(_[0], _[1])

    # fix selah
    if "<selah>" in blocktext:
        blocktext = selah(blocktext)

    return blocktext


def c2o_fixgroupings(grouplines: list[str]) -> list[str]:
    """Fix linegroups in poetry, lists, etc."""

    def btags(lines: list[str]) -> list[str]:
        """Handle b tags."""
        for _ in enumerate(lines):
            if "<!-- b -->" in lines[_[0]]:
                lines[_[0]] = (
                    lines[_[0]].replace("<!-- b -->", '<lb type="x-p" />')
                    if lines[_[0]][:2] in {"<l", "<p"}
                    else lines[_[0]].replace("<!-- b -->", "")
                )
        return lines

    def lgtags(lines: list[str]) -> list[str]:
        """Handle lg tag groupings."""
        inlg = False
        for _ in enumerate(lines):
            if lines[_[0]].startswith("<l "):
                if not inlg:
                    lines[_[0]] = f"<lg>\ufdd0{lines[_[0]]}"
                    inlg = True
            elif inlg:
                lines[_[0] - 1] = f"{lines[_[0] - 1]}\ufdd0</lg>\ufdd0"
                inlg = False
        return lines

    def listtags(lines: list[str]) -> list[str]:
        """Handle list tag groupings."""
        inlist = False
        for _ in enumerate(lines):
            if lines[_[0]].startswith("<item "):
                if not inlist:
                    lines[_[0]] = f"<list>\ufdd0{lines[_[0]]}"
                    inlist = True
            elif inlist:
                lines[_[0] - 1] = f"{lines[_[0] - 1]}\ufdd0</list>\ufdd0"
                inlist = False
        return lines

    def tabletags(lines: list[str]) -> list[str]:
        """Handle table tag groupings."""
        intable = False
        for _ in enumerate(lines):
            if lines[_[0]].startswith("<row"):
                if not intable:
                    lines[_[0]] = f"\ufdd0<table>\ufdd0{lines[_[0]]}"
                    intable = True
            elif intable:
                lines[_[0] - 1] = f"{lines[_[0] - 1]}\ufdd0</table>\ufdd0"
                intable = False
        return lines

    def introductions(lines: list[str]) -> list[str]:
        """Encapsulate introductions in divs."""
        lines1 = (
            '<div type="introduction">\ufdd0' if _ == "\ufde0" else _ for _ in lines
        )
        lines2 = ("</div>\ufdd0" if _ == "\ufde1" else _ for _ in lines1)
        return [
            f'{_.replace("\ufde1", "")}</div>\ufdd0' if _.endswith("\ufde1") else _
            for _ in lines2
        ]

    # append a blank line. (needed in some cases)
    grouplines.append("")

    # add breaks before verse tags
    # Process b tags,
    # add missing lg tags, list tags, and table tags.
    # Encapsulate introductions inside div tags.
    # Return results.
    return introductions(
        tabletags(
            listtags(
                lgtags(btags([_.replace(r"\v ", "\ufdd0\\v ") for _ in grouplines]))
            )
        )
    )


def c2o_specialtext(text: str) -> str:
    """
    Process special text and character styles.

    add, add*, bk, bk*, dc, dc*, k, k*, lit, nd, nd*, ord, ord*, pn, pn*,
    qt, qt*, sig, sig*, sls, sls*, tl, tl*, wj, wj*

    em, em*, bd, bd*, it, it*, bdit, bdit*, no, no*, sc, sc*


    * lit tags are handled in the titlepar function

    """

    def simplerepl(match: re.Match[str]) -> str:
        """Simple regex replacement helper function."""
        tag = SPECIALTEXT[match.group("tag")]
        return f'{tag[0]}{match.group("osis")}{tag[1]}'

    text = SPECIALTEXTRE.sub(simplerepl, text, 0)
    # Make sure all nested tags are processed.
    # In order to avoid getting stuck here we abort
    # after a maximum of 5 attempts. (5 was chosen arbitrarily)
    nestcount = 0
    while "\\" in text:
        nestcount += 1
        text = SPECIALTEXTRE.sub(simplerepl, text, 0)
        if nestcount > 5:
            break

    return text


def c2o_noterefmarkers(text: str) -> str:
    """Process footnote and cross reference markers."""

    def notefix(notetext: str) -> str:
        """Additional footnote and cross reference tag processing."""

        def notefixsub(fnmatch: re.Match[str]) -> str:
            """Simple regex replacement helper function."""
            tag = list(NOTETAGS2[fnmatch.groups()[0]])
            attrtxt: str
            txt, _, attrtxt = (
                (fnmatch.groups()[1].partition("|"))
                if "<reference>" in tag
                else (fnmatch.groups()[1], "", "")
            )
            # try to convert usfm reference attributes to osisRef
            if "<reference" in tag:
                tmp = attrtxt.replace("link-href=", "")
                reftxt = ""
                if len(tmp) == 3:
                    # reference points to a book
                    reftxt = BOOKNAMES[tmp]
                elif " " in reftxt and "=" not in reftxt:
                    bk, chapverse = tmp.split(" ", maxsplit=1)
                    isonechap = BOOKNAMES[bk] in ONECHAP
                    if ":" not in chapverse and "-" not in reftxt and not isonechap:
                        # reference points to a chapter
                        reftxt = f"{BOOKNAMES[bk]}.{chapverse}"
                    elif "-" not in reftxt:
                        # reference points to a single verse
                        reftxt = (
                            f'{BOOKNAMES[bk]}.{chapverse.replace(":", ".")}'
                            if not isonechap
                            else f"{BOOKNAMES[bk]}.1.{chapverse}"
                        )
                    else:
                        # is a reference to a range of verses
                        cvsplit = chapverse.split(":", maxsplit=1)
                        if len(cvsplit) == 1:
                            chap1, chap2 = ("1", "1")
                            verse1, verse2 = cvsplit[0].split("-", maxsplit=1)
                        else:
                            chap1, chap2 = (cvsplit[0], cvsplit[0])
                            verse1, verse2 = cvsplit[1].split("-", maxsplit=1)
                            if ":" in verse2:
                                chap2, verse2 = verse2.split(":", maxsplit=1)
                        refstart = f"{BOOKNAMES[bk]}.{chap1}.{verse1}"
                        refend = f"{BOOKNAMES[bk]}.{chap2}.{verse2}"
                        reftxt = f"{refstart}-{refend}"
                if reftxt != "":
                    tag[0] = tag[0].replace(">", f' osisRef="{reftxt}">')
            if attrtxt != "":
                txt = f"<!-- USFM Attributes: {attrtxt} -->{txt}"
            return "".join([tag[0], txt, tag[1]])

        notetext = NOTEFIXRE.sub(notefixsub, notetext, 0)
        for _ in [
            r"\fm*",
            r"\fdc*",
            r"\fr*",
            r"\fk*",
            r"\fq*",
            r"\fqa*",
            r"\fl*",
            r"\fv*",
            r"\ft*",
            r"\xo*",
            r"\xk*",
            r"\xq*",
            r"\xt*",
            r"\xot*",
            r"\xnt*",
            r"\xdc*",
            r"\+fm*",
            r"\+fdc*",
            r"\+fr*",
            r"\+fk*",
            r"\+fq*",
            r"\+fqa*",
            r"\+fl*",
            r"\+fv*",
            r"\+ft*",
            r"\+xo*",
            r"\+xk*",
            r"\+xq*",
            r"\+xt*",
            r"\+xot*",
            r"\+xnt*",
            r"\+xdc*",
        ]:
            if _ in notetext:
                notetext = notetext.replace(_, "")
        return notetext

    def simplerepl(match: re.Match[str]) -> str:
        """Simple regex replacement helper function."""
        tag = NOTETAGS[match.group("tag")]
        notetext = match.group("osis").replace("\n", " ")
        if "<transChange" in notetext:
            notetext = notetext.replace(
                '<transChange type="added">',
                '<seg><transChange type="added">',
            ).replace("</transChange>", "</transChange></seg>")
        return f"{tag[0]}{notetext}{tag[1]}"

    text = notefix(NOTERE.sub(simplerepl, text, 0))

    # handle fp tags
    text = (
        text.replace("\ufdd2", "<p>")
        .replace("\ufdd3", "</p>")
        .replace(r"\fp ", r"</p><p>")
        if r"\fp " in text
        else text.replace("\ufdd2", "").replace("\ufdd3", "")
    )

    # return our processed text handling \cat if necessary
    return (
        text
        if r"\cat " not in text
        else text.replace(r"\cat ", r'<index index="category" level1="').replace(
            r"\cat*", r'" />'
        )
    )


def c2o_specialfeatures(specialtext: str) -> str:
    """Process special features."""

    def simplerepl(match: re.Match[str]) -> str:
        """Simple regex replacement helper function."""
        matchtag = match.group("tag")
        tag = FEATURETAGS[matchtag]
        rawosis = match.group("osis")

        osis, attributetext, attributes, isvalid = {
            True: parseattributes(matchtag, rawosis),
            False: (rawosis, None, {}, True),
        }["|" in rawosis]
        del isvalid  # make pylint happy
        osis2 = osis
        strong1 = ""
        strong2 = ""

        # handle w tag attributes
        tag2 = None
        if matchtag in {r"\w", r"\+w"}:
            if (
                "lemma" in attributes.keys()
                and "strong" not in attributes.keys()
                and "x-strong" not in attributes.keys()
            ):
                osis2 = attributes["lemma"]
            if "strong" in attributes.keys() or "x-strong" in attributes.keys():
                tag2 = STRONGSTAG
                tmp = (
                    " ".join(
                        [f"strong:{_.strip()}" for _ in attributes["strong"].split(",")]
                    )
                    if "strong" in attributes.keys()
                    else " ".join(
                        [
                            f"strong:{_.strip()}"
                            for _ in attributes["x-strong"].split(",")
                        ]
                    )
                )
                # add lemma to osis strongs markup
                if "lemma" in attributes.keys():
                    tmp = f"{tmp} lemma:{attributes['lemma']}"
                strong1 = f'lemma="{tmp}"'
                strong2 = ""
            if "x-morph" in attributes.keys():
                if tag2 is not None:
                    strong2 = f' morph="{attributes["x-morph"]}"'

        # TODO: improve processing of tag attributes

        if tag[0] == "" and tag2 is None:
            # limited filtering of index entry contents...
            if '<seg type="x-nested"><transChange type="added">' in osis2:
                osis2 = osis2.replace(
                    '<seg type="x-nested"><transChange type="added">', ""
                ).replace("</transChange></seg>", "")
            outtext = f"{osis}{tag[1].format(osis2)}"
        elif tag2 is not None:
            outtext2 = ""
            # preserve unprocessed x- attributes as comments
            for i in (
                _
                for _ in attributes.keys()
                if _.startswith("x-") and _ not in ["x-strong", "x-morph"]
            ):
                outtext2 = f"{outtext2}<!-- {i} - {attributes[i]} -->"
            # process strongs
            outtext = f"{tag2[0].format(strong1, strong2)}{osis}{outtext2}{tag2[1]}"
        else:
            outtext = f"{tag[0]}{osis}{tag[1]}"

        # problems can occur when strongs numbers are present. This avoids those problems.
        if attributetext is not None and matchtag not in [r"\w", r"\+w"]:
            outtext = f"{outtext}<!-- USFM Attributes: {attributetext} -->"

        return outtext

    def figtags(text: str) -> str:
        """Process fig tags."""
        text = text.replace(r"\fig ", "\n\\fig ").replace(r"\fig*", "\\fig*\n")
        tlines = text.split("\n")
        for i in enumerate(tlines):
            if tlines[i[0]].startswith(r"\fig "):
                # old style \fig handling
                # \fig DESC|FILE|SIZE|LOC|COPY|CAP|REF\fig*
                if len(tlines[i[0]][5:-5].split("|")) > 2:
                    fig = tlines[i[0]][5:-5].split("|")
                    figref = ""
                    fig[0] = {
                        False: f"<!-- fig DESC - {fig[0]} -->\n",
                        True: fig[0],
                    }[not fig[0]]
                    fig[1] = {
                        False: f' src="{fig[1]}"',
                        True: fig[1],
                    }[not fig[1]]
                    fig[2] = {
                        False: f' size="{fig[2]}"',
                        True: fig[2],
                    }[not fig[2]]
                    fig[3] = {
                        False: f"<!-- fig LOC - {fig[3]} -->\n",
                        True: fig[3],
                    }[not fig[3]]
                    fig[4] = {
                        False: f' rights="{fig[4]}"',
                        True: fig[4],
                    }[not fig[4]]
                    fig[5] = {
                        False: f"<caption>{fig[5]}</caption>\n",
                        True: fig[5],
                    }[not fig[5]]
                    # this is likely going to be very broken without
                    # further processing of the references.
                    if fig[6]:
                        figref = f'<reference type="annotateRef">{fig[6]}</reference>\n'
                        fig[6] = f' annotateRef="{fig[6]}"'

                # new style \fig handling
                else:
                    figattr = parseattributes(r"\fig", tlines[i[0]][5:-5])
                    fig = []
                    figparts = {
                        "alt": "<!-- fig ALT - {} -->\n",
                        "src": ' src="{}"',
                        "size": ' size="{}"',
                        "loc": "<!-- fig LOC - {} -->\n",
                        "copy": ' rights="{}"',
                    }
                    for _ in ["alt", "src", "size", "loc", "copy"]:
                        fig.append(
                            {
                                True: figparts[_].format(figattr[2][_]),
                                False: "",
                            }[_ in figattr[2]]
                        )
                        # caption absent in new style fig attributes
                        fig.append("")
                        # this is likely going to be very broken without
                        # further processing of the references.
                        if "ref" in figattr[2]:
                            figref = f'<reference type="annotateRef">{figattr[2]["ref"]}</reference>\n\n'
                            fig.append(f' annotateRef="{figattr[2]["ref"]}"')
                        else:
                            figref = ""
                            fig.append("")
                # build our osis figure tag
                tlines[i[0]] = "".join(
                    [
                        fig[0],
                        fig[3],
                        "<figure",
                        fig[1],
                        fig[2],
                        fig[4],
                        fig[6],
                        ">\n",
                        figref,
                        fig[5],
                        "</figure>",
                    ]
                )

        return "".join(tlines)

    def milestonequotes(text: str) -> str:
        """Handle usfm milestone quotations."""
        for _ in [
            r"\qt-",
            r"\qt1-",
            r"\qt2-",
            r"\qt3-",
            r"\qt4-",
            r"\qt5-",
        ]:
            if _ in text:
                text = text.replace(_, f"\n{_}")
        tlines = text.replace(r"\*", "\\*\n").split("\n")
        qlevel = ""
        for i in enumerate(tlines):
            # make sure we're processing milestone \qt tags
            if tlines[i[0]].endswith(r"\*"):
                for j in (
                    r"\qt-",
                    r"\qt1-",
                    r"\qt2-",
                    r"\qt3-",
                    r"\qt4-",
                    r"\qt5-",
                ):
                    if tlines[i[0]].startswith(j):
                        # replace with milestone osis tags
                        newline = ""
                        tlines[i[0]] = tlines[i[0]].strip().replace(r"\*", "")
                        tag, _, qttext = tlines[i[0]].partition(" ")
                        # milestone start tag
                        if tag.endswith(r"-s"):
                            (
                                _,
                                attributetext,
                                attributes,
                                isvalid,
                            ) = parseattributes(r"\qt-s", qttext)
                            del isvalid, attributetext  # make pylint happy
                            newline = r"<q"
                            newline = {
                                True: f'{newline} sID="{attributes["id"]}"',
                                False: newline,
                            }["id" in attributes]
                            newline = {
                                True: f'{newline} who="{attributes["who"]}"',
                                False: newline,
                            }["who" in attributes]
                            qlevel = {True: tag[3], False: "1"}[
                                tag[3] in {"2", "3", "4", "5"}
                            ]

                            newline = f'{newline} level="{qlevel}" />'
                        # milestone end tag
                        elif tag.endswith(r"-e"):
                            (
                                _,
                                attributetext,
                                attributes,
                                isvalid,
                            ) = parseattributes(r"\qt-e", qttext)
                            newline = r"<q"
                            newline = {
                                True: f'{qlevel} eID="{attributes["id"]}"',
                                False: newline,
                            }["id" in attributes]
                            qlevel = {True: tag[3], False: "1"}[
                                tag[3] in {"2", "3", "4", "5"}
                            ]

                            # I don't know if I need the level attribute
                            # on the milestone end tag. I put it here
                            # just to be sure though. I will remove it
                            # later if it doesn't belong here.
                            newline = f'{newline} level="{qlevel}" />'
                        # replace line with osis milestone tag
                        if newline != "":
                            tlines[i[0]] = newline
        # rejoin lines
        return "".join(tlines)

    specialtext = SPECIALFEATURESRE.sub(simplerepl, specialtext, 0)

    if r"\fig" in specialtext:
        specialtext = figtags(specialtext)

    # Process usfm milestone quotation tags... up to 5 levels.
    for _ in [r"\qt-", r"\qt1-", r"\qt2-", r"\qt3-", r"\qt4-", r"\qt5-"]:
        if _ in specialtext:
            specialtext = milestonequotes(specialtext)
            break

    return specialtext


def c2o_ztags(text: str) -> str:
    """Process z tags that have both a start and end marker."""

    def simplerepl(match: re.Match[str]) -> str:
        """Simple regex replacement helper function."""
        return "".join(
            [
                ' <seg type="x-usfm-z',
                match.group("tag"),
                ">",
                match.group("osis"),
                "</seg> ",
            ]
        )

    def simplerepl2(match: re.Match[str]) -> str:
        """Simple regex replacement helper for milestone z tags."""
        return "".join([" <!-- ", match.group("tag").replace("\\z", ""), "--> "])

    if r"\z" in text:
        text = ZTAGS2RE.sub(simplerepl2, ZTAGSRE.sub(simplerepl, text, 0), 0)
        if r"\z" in text:
            # milestone z tags… this may need more work…
            text = " ".join(
                [
                    (
                        ' <milestone type="x-usfm-z{_[2:]}" /> '
                        if _.startswith(r"\z")
                        else _
                    )
                    for _ in text.split(" ")
                ]
            )
    return text


def c2o_chapverse(lines: list[str], bookid: str) -> list[str]:
    """Process chapter and verse tags."""

    def verserange(text: str) -> list[str]:
        """Generate list for verse ranges."""
        low, high = text.split("-")
        # make sure Right-To-Left and Left-To-Right marks aren't included
        # in verse range numbers.
        low = low.replace("\u200e", "").replace("\u200f", "")
        high = high.replace("\u200e", "").replace("\u200f", "")
        try:
            retval = [str(_) for _ in range(int(low), int(high) + 1)]
        except ValueError:
            end1 = ""
            end2 = ""
            if low[-1] in {"a", "b", "A", "B"}:
                end1 = low[-1]
                low = "".join(low[:-1])
            if high[-1] in {"a", "b", "A", "B"}:
                end2 = high[-1]
                high = "".join(high[:-1])
            retval = [str(_) for _ in range(int(low), int(high) + 1)]
            if end1 != "":
                retval[0] = "!".join([retval[0], end1])
            if end2 != "":
                retval[-1] = "!".join([retval[-1], end2])
        return retval

    # prepare for chapter and verse processing
    lines = [_.strip() for _ in " ".join(lines).split("\ufdd0")]

    # chapter and verse numbers
    closerlist = [_ for _ in range(len(lines)) if lines[_].startswith(r"<closer")]
    for i in reversed(closerlist):
        lines[i - 1] = " ".join([lines[i - 1], lines[i]])
        del lines[i]

    chap = ""
    verse = ""
    caid = ""
    haschap = False
    hasverse = False
    cvlist = [
        _
        for _ in range(len(lines))
        if lines[_].startswith(r"\c ") or lines[_].startswith(r"\v ")
    ]
    for i in cvlist:
        tmp: str | list[str] = ""
        vnum = ""
        # ## chapter numbers
        if lines[i].startswith(r"\c "):
            haschap = True
            tmp = list(lines[i].split(" ", 2))
            if len(tmp) < 3:
                tmp.append("")
            # make sure Right-To-Left and Left-To-Right marks aren't included
            # in chapter number when creating osisID.
            cnum = tmp[1].replace("\u200e", "").replace("\u200f", "")

            # nb fix...
            if "<!--" in cnum and "nb -->" in tmp[2]:
                cnum = cnum.replace("<!--", "").strip()
                tmp[2] = f"<!-- {tmp[2]}"

            caid = ""

            # generate chapter number
            if chap == "":
                lines[i] = "<chapter {} {} {} />{}".format(
                    f'sID="{bookid}.{cnum}"',
                    f'osisID="{bookid}.{cnum}{caid}"',
                    f'n="{cnum}"',
                    tmp[2],
                )
                chap = cnum
            else:
                if hasverse:
                    lines[i] = "{}\n{}\n<chapter {} {} {} />{}".format(
                        f'<verse eID="{bookid}.{chap}.{verse}" />',
                        f'<chapter eID="{bookid}.{chap}" />',
                        f'sID="{bookid}.{cnum}"',
                        f'osisID="{bookid}.{cnum}{caid}"',
                        f'n="{cnum}"',
                        tmp[2],
                    )
                    hasverse = False
                else:
                    lines[i] = "{}\n<chapter {} {} {} />{}".format(
                        f'<chapter eID="{bookid}.{chap}" />',
                        f'sID="{bookid}.{cnum}"',
                        f'osisID="{bookid}.{cnum}{caid}"',
                        f'n="{cnum}"',
                        tmp[2],
                    )

                chap = cnum
                verse = ""

        # ## verse numbers
        # BUG?: \va tags won't be handled unless lines start with a \v tag
        elif lines[i].startswith(r"\v "):
            # test for books with only one chapter
            if bookid in ONECHAP and haschap is False:
                chap = "1"

            hasverse = True
            tmp = list(lines[i].split(" ", 2))
            if len(tmp) < 3:
                tmp.append("")
            # make sure Right-To-Left and Left-To-Right marks aren't included
            # in verse number when creating osisID.
            vnum = tmp[1].replace("\u200e", "").replace("\u200f", "")

            vaid = ""

            # handle verse ranges
            if "-" in vnum:
                try:
                    vlist = verserange(vnum)
                    for j in enumerate(vlist):
                        vlist[j[0]] = f"{bookid}.{chap}.{vlist[j[0]]}"
                    osisid = f'osisID="{" ".join(vlist)}{vaid}"'
                except TypeError:
                    vnum = vnum.strip("-")
                    osisid = f'osisID="{bookid}.{chap}.{vnum}{vaid}"'
            else:
                osisid = f'osisID="{bookid}.{chap}.{vnum}{vaid}"'

            # generate verse tag
            if verse == "":
                # handle single chapter books without chapter marker
                if chap == "1" and haschap is False:
                    chapmark = "<chapter {} {} {} />\n".format(
                        f'sID="{bookid}.1"',
                        f'osisID="{bookid}.1{caid}"',
                        'n="1"',
                    )
                    haschap = True
                else:
                    chapmark = ""

                lines[i] = "{}<verse {} {} {} />{}".format(
                    chapmark,
                    f'sID="{bookid}.{chap}.{vnum}"',
                    osisid,
                    f'n="{vnum}"',
                    tmp[2],
                )
                verse = vnum
                hasverse = True
            else:
                lines[i] = "<verse {} />\n<verse {} {} {} />{}".format(
                    f'eID="{bookid}.{chap}.{verse}"',
                    f'sID="{bookid}.{chap}.{vnum}"',
                    osisid,
                    f'n="{vnum}"',
                    tmp[2],
                )
                verse = vnum
                hasverse = True

        elif lines[i].startswith(r"<closer"):
            lines[i] = f'<verse eID="{bookid}.{chap}.{verse}" />\n{tmp[2]}'
            verse = vnum
            hasverse = False

    if hasverse:
        lines.append(f'<verse eID="{bookid}.{chap}.{verse}" />')
    if haschap:
        lines.append(f'<chapter eID="{bookid}.{chap}" />')

    return lines


def c2o_processwj2(lines: list[str]) -> list[str]:
    """
    Alternate processing of wj tags.

    This attempts to insert q start and end tags in appropriate locations
    in order to avoid crossing container boundaries.

    """
    # get tags where lines need to be broken for processing
    wjtags = {
        (_[1][0].strip(), _[1][1].strip())
        for _ in (list(TITLETAGS.items()) + list(PARTAGS.items()))
        if _[1][0] != "" and _[1][1] != ""
    }

    # split words of jesus from the rest of the text.
    lines = (
        "\ufdd1".join(lines)
        .replace("\\wj ", "\n\\wj ")
        .replace("\\wj*", "\\wj*\n ")
        .split("\n")
    )

    # process words of Jesus.
    for i in enumerate(lines):
        if lines[i[0]].startswith(r"\wj "):
            for _ in wjtags:
                lines[i[0]] = lines[i[0]].replace(
                    _[0], f'{_[0]}<q who="Jesus" marker="">'
                )
                lines[i[0]] = lines[i[0]].replace(_[1], f"</q>{_[1]}")
    lines = [
        _.replace(r"\wj ", '<q who="Jesus" marker="">').replace(r"\wj*", "</q>")
        for _ in lines
    ]

    # rejoin lines, then resplit and return processed lines...
    return "".join(lines).split("\ufdd1")


###########################################################################################


def post_sidebar(lines: list[str]) -> list[str]:
    """Fix sidebar."""
    return (
        lines
        if not [_ for _ in lines if "SIDEBAR" in _]
        else [
            _.replace("<SIDEBAR>", '<div type="x-sidebar">').replace(
                "</SIDEBAR>", "</div>"
            )
            for _ in lines
            if _ != ""
        ]
    )


def post_vp(lines: list[str]) -> list[str]:
    """Handle vp tags that were missed."""
    for _ in enumerate(lines):
        while r"\vp " in lines[_[0]]:
            tmp = VPRE.search(lines[_[0]])
            if tmp is not None:
                vpnum = tmp.group("num")
                lines[_[0]] = VPRE.sub(
                    f'<milestone type="x-usfm-vp" n="{vpnum}" />',
                    lines[_[0]],
                    1,
                )
    return [_ for _ in lines if _ != ""]


def post_tagadjust(lines: list[str]) -> list[str]:
    """Adjust tags for postprocessing purposes."""
    # remove empty l tags
    lines = [_ for _ in lines if _ != '<l level="1"> </l>']
    # move lb and lg to their own lines
    for i in range(len(lines) - 1, 0, -1):
        if lines[i].endswith('<lb type="x-p" />'):
            lines.insert(i + 1, '<lb type="x-p" />')
            lines[i] = lines[i].rpartition('<lb type="x-p" />')[0].strip()
        if lines[i].endswith("<lg>"):
            lines.insert(i + 1, "<lg>")
            lines[i] = lines[i].rpartition("<lg>")[0].strip()
    return [_ for _ in lines if _ != ""]


def post_swap_lblg(lines: list[str]) -> list[str]:
    """Swap lb and lg tags when lg end tag follows lb."""
    for i in range(len(lines) - 1, 0, -1):
        try:
            if lines[i] == '<lb type="x-p" />' and lines[i + 1] == "</lg>":
                lines[i], lines[i + 1] = (lines[i + 1], lines[i])
        except IndexError:
            pass
    return [_ for _ in lines if _ != ""]


def post_verseend(lines: list[str]) -> list[str]:
    """Adjust placement of verse end tags."""
    for i in (_ for _ in range(len(lines)) if lines[_].startswith("<verse eID")):
        if lines[i - 1].strip() in OSISL or lines[i - 1].strip() in OSISITEM:
            lines.insert(i - 1, lines.pop(i))
        elif lines[i - 1] == "<row><cell>" and lines[i - 2] == "<table>":
            lines.insert(i - 2, lines.pop(i))

    for i, j in (
        (x, y)
        for x in (
            "<p",
            "<lb ",
            "</p>",
            "<lg",
            "<lb ",
            "</lg>",
            "<item",
            "</item",
            "<list",
            "<lb",
            "</list>",
            "<title",
            "<title",
            "<title",
            "<title",
            "<title",
            "<div",
            "</div>",
            "<lb ",
            "</p>",
            "</l",
            "</lg>",
            "<lb",
            "</list>",
            "<lb",
            "</p>",
            "</div>",
        )
        for y in (_ for _ in range(len(lines)) if lines[_].startswith("<verse eID"))
    ):
        if lines[j - 1].startswith(i):
            lines.insert(j - 1, lines.pop(j))
        elif i == "<title":
            if lines[j - 1].startswith("<!-- ") and i in lines[j - 1]:
                lines.insert(j - 1, lines.pop(j))

    for i, j in (
        (x, y)
        for x in ("</l>", "</item>")
        for y in (_ for _ in range(len(lines)) if lines[_].startswith("<verse eID"))
    ):
        if lines[j - 1].endswith(i):
            tmp = lines[j - 1].rpartition("<")
            lines[j - 1], lines[j] = (f"{tmp[0]}{lines[j]}{tmp[1]}{tmp[2]}", "")

    for i in (_ for _ in range(len(lines)) if lines[_].startswith("<verse eID")):
        try:
            if (
                lines[i + 1].startswith("<verse sID")
                and lines[i - 1].startswith("<l ")
                and lines[i - 2].endswith("</l>")
            ):
                tmp = lines[i - 2].rpartition("<")
                lines[i - 2], lines[i] = (f"{tmp[0]}{lines[i]}<{tmp[2]}", "")
            if (
                lines[i + 1].startswith("<verse sID")
                and lines[i - 1].startswith("<l ")
                and lines[i - 2].startswith("<lg")
                and lines[i - 3].startswith("</lg")
                and lines[i - 4].endswith("</l>")
            ):
                tmp = lines[i - 4].rpartition("<")
                lines[i - 4], lines[i] = (f"{tmp[0]}{lines[i]}<{tmp[2]}", "")
            if (
                lines[i + 1].startswith("<verse sID")
                and lines[i - 1].startswith("<l ")
                and lines[i - 2].startswith("<lg")
                and lines[i - 3] == "</p>"
            ):
                lines.insert(i - 3, lines.pop(i))
        except IndexError:
            pass
    return [_ for _ in lines if _ != ""]


def post_versestart(lines: list[str]) -> list[str]:
    """Adjust placement of some verse start tags...
    This is only to make sure they are properly nested inside paragraph markers!"""
    for i in (_ for _ in range(len(lines)) if lines[_].startswith("<verse sID")):
        try:
            if lines[i + 1].startswith("</p") and lines[i + 2].startswith("<p"):
                lines.insert(i + 2, lines.pop(i))
        except IndexError:
            pass
    return [_ for _ in lines if _ != ""]


def post_selahlgl(lines: list[str]) -> list[str]:
    """Fix problems with selah and l or lg tags."""
    for i in (_ for _ in range(len(lines)) if lines[_].startswith("<chapter sID")):
        if (
            lines[i].endswith("</l>")
            and lines[i + 1] == "</lg>"
            and lines[i - 1].startswith("<chapter eID")
            and lines[i - 2].startswith("<verse eID")
            and lines[i - 3].endswith("</l><l>")
        ):
            lines[i - 3], lines[i - 2], lines[i], lines[i + 1] = (
                lines[i - 3][:-3],
                f"{lines[i - 2]}</lg>",
                lines[i][:-4],
                "",
            )
    return [_ for _ in lines if _ != ""]


def post_lgl(lines: list[str]) -> list[str]:
    """Fix additional things with lg and l tags."""
    for i in (_ for _ in range(len(lines)) if lines[_].startswith("<chapter sID")):
        if (
            lines[i].endswith("</l>")
            and lines[i - 1].startswith("<chapter eID")
            and lines[i + 1] == "</lg>"
        ):
            lines[i - 2], lines[i], lines[i + 1] = (
                f"{lines[i - 2]}</l></lg>",
                lines[i][:-4],
                "",
            )
    return [_ for _ in lines if _ != ""]


def post_dverse(lines: list[str]) -> list[str]:
    """Fix placement of verse tags in relation to d titles with verses."""
    for i in (_ for _ in range(len(lines)) if lines[_].startswith("<!-- d -->")):
        if (
            lines[i + 1].startswith("<verse sID")
            and lines[i + 1].endswith("</title>")
            and lines[i + 2].startswith("<verse eID")
        ):
            tmp1 = lines[i + 1].rpartition("<")
            lines[i], lines[i + 1], lines[i + 2] = (
                f"{lines[i]}{tmp1[0]}{lines[i+2]}</title>",
                "",
                "",
            )
    return [_ for _ in lines if _ != ""]


def post_acrostic(lines: list[str]) -> list[str]:
    """Fix verse end markers following "acrostic" Titles."""
    # This exists because I can't figure out why my other fixes aren't working.
    for i, j in (
        (x, y)
        for x in ('<title type="acrostic"', "</lg", "</l>", "<!- ", "</p>")
        for y in (_ for _ in range(len(lines)) if lines[_].startswith("<verse eID"))
    ):
        if lines[j - 1].startswith(i) and i != "</l>":
            lines.insert(j - 1, lines.pop(j))
        elif lines[j - 1].endswith(i) and i == "</l>":
            lines[j - 1], lines[j] = (
                f'{lines[j - 1].rpartition("<")[0]}{lines[j]}</l>',
                "",
            )
    return [_ for _ in lines if _ != ""]


def convert_to_osis(text: str, bookid: str = "TEST") -> str:
    """Convert usfm file to osis."""
    # ---------------------------------------------------------------------- #

    # preprocess, split text, mark introduction endings... then process
    # identification, character styles, special features, footnotes and cross references,
    # ztags, paragraph style formatting
    # words of Jesus
    # fix groupings for poetry, lists, tables
    # process chapter/verse markers
    lines = c2o_chapverse(
        c2o_fixgroupings(
            c2o_processwj2(
                [
                    c2o_titlepar(
                        c2o_ztags(
                            c2o_noterefmarkers(
                                c2o_specialfeatures(
                                    c2o_specialtext(c2o_identification(_))
                                )
                            )
                        ),
                        bookid,
                    )
                    for _ in markintroend(c2o_preprocess(text).split("\n"))
                ]
            )
        ),
        bookid,
    )

    # postprocessing to fix some issues that may be present
    linespost = post_acrostic(
        post_dverse(
            post_lgl(
                post_selahlgl(
                    post_versestart(
                        post_verseend(
                            post_swap_lblg(
                                post_tagadjust(
                                    post_vp(
                                        post_sidebar(
                                            [
                                                _.strip()
                                                for _ in "\n".join(lines).split("\n")
                                                if _.strip() != ""
                                                and _.strip() != "<!-- b -->"
                                            ]
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            )
        )
    )

    # rejoin lines after processing
    return "\n".join([_ for _ in linespost if _ != ""])


# -------------------------------------------------------------------------- #


def doconvert(text: str) -> tuple[str, ...]:
    """Convert our text and return our results."""
    # convert cl lines to form that follows each chapter marker instead of
    # form that precedes first chapter.
    if r"\cl " in text:
        text = convertcl(text)

    # get book id. use TEST if none present.
    bookid = getbookid(text)
    if bookid is not None:
        if bookid.startswith("* "):
            LOG.error("Book id naming issue - %s", bookid.replace("* ", ""))
    else:
        bookid = "TEST"

    # get id, ide, and rem statements to use for descriptiontext
    descriptiontext, newtext = c2o_getdescription(text)

    # decode and reflow our text
    newtext = reflow(newtext)

    # convert file to osis
    LOG.info("... Processing %s ...", bookid)
    newtext = convert_to_osis(newtext, bookid)
    return bookid, descriptiontext, newtext


def proc_readfiles(fnames: list[str], fencoding: str) -> str:
    """Read files and return concatenated file contents."""
    files = []
    for fname in fnames:
        # read our text files
        with open(fname, "rb") as ifile:
            text = ifile.read()

        # strip whitespace from beginning and end of file
        text = text.strip()

        # get encoding. Abort processing if we don't know the encoding.
        # default to utf_8_sig encoding if no encoding is specified.
        bookencoding = "utf_8_sig"
        try:
            bookencoding = (
                lookup(fencoding).name if fencoding is not None else getencoding(text)
            )
            if "utf-8" in bookencoding:
                bookencoding = "utf_8_sig"

            # use utf_8_sig in place of utf_8 encoding to eliminate errors that
            # may occur if a Byte Order Mark is present in the input file.
            if bookencoding == "utf_8":
                bookencoding = "utf_8_sig"
        except LookupError:
            LOG.error("ERROR: Unknown encoding... aborting conversion.")
            LOG.error(r"    \ide line for %s says --> %s", fname, bookencoding)
            sysexit()

        # convert file to unicode and add contents to list for processing...
        files.append(text.decode(bookencoding))
    return "\ufddf".join(files)


def proc_xmlvalidate(osisdoc2: bytes) -> bytes:
    """Validate and reformat osis and return results."""
    # a test string allows output to still be generated
    # even when when validation fails.
    testosis = SQUEEZE(osisdoc2.decode("utf_8"))

    LOG.info("Validating osis xml...")
    osisschema = decode(decode(decode(SCHEMA, "base64"), "bz2"), "utf_8")
    xmlschema = decode(
        decode(decode(XMLSCHEMA, "base64"), "bz2"),
        "utf_8",
    )
    with NamedTemporaryFile(suffix=".xsd") as xmlxsd:
        osisschema = osisschema.replace(
            "http://www.w3.org/2001/03/xml.xsd",
            f"file://{xmlxsd.name}",
        )
        xmlxsd.write(xmlschema.encode("utf_8"))

        try:
            vparser = et.XMLParser(
                schema=et.XMLSchema(et.XML(osisschema)),
                remove_blank_text=True,
            )
            _ = et.fromstring(testosis.encode("utf_8"), vparser)  # nosec
            LOG.warning("Validation passed!")
            osisdoc2 = et.tostring(
                _,
                pretty_print=True,
                xml_declaration=True,
                encoding="utf_8",
            )
        except et.XMLSyntaxError as err:
            LOG.error("Validation failed: %s", str(err))
    return osisdoc2


def processfiles(
    fnames: list[str],
    fencoding: str,
    dodebug: bool,
    sortorder: str,
    langcode: str,
    nonormalize: bool,
    workid: str,
    outputfile: str,
) -> None:
    """Process usfm files specified on command line."""
    books: dict[str, str] = {}
    descriptions: dict[str, str] = {}
    booklist: list[str] = []

    # get username from operating system
    username = {True: getenv("LOGNAME"), False: getenv("USERNAME")}[
        getenv("USERNAME") is None
    ]

    # read all files
    LOG.info("Reading files... ")

    # process file contents
    filelist = proc_readfiles(fnames, fencoding).split("\ufddf")
    results: list[tuple[str, ...]]
    LOG.info("Processing files...")
    with concurrent.futures.ProcessPoolExecutor() as executor:
        results = (
            list(executor.map(doconvert, filelist))
            if not dodebug
            else [doconvert(_) for _ in filelist]
        )

    # store results
    for bookid, descriptiontext, newtext in results:
        # store our converted text for output
        if bookid != "TEST":
            books[bookid] = (
                (f'<div type="{NONCANONICAL[bookid]}">\n{newtext}\n</div>\n\n')
                if bookid in NONCANONICAL
                else (
                    f'<div type="book" osisID="{bookid}" canonical="true">\n{newtext}\n</div>\n\n'
                )
            )
            descriptions[bookid] = descriptiontext
            booklist.append(bookid)
        else:
            books[bookid], descriptions[bookid] = (
                (f"{books[bookid]}\n{newtext}", f"{books[bookid]}\n{descriptiontext}")
                if bookid in books
                else (newtext, descriptiontext)
            )
            if "TEST" not in booklist:
                booklist.append("TEST")

    # ## Get order for books...
    if sortorder == "none":
        tmp = "\n".join([books[_] for _ in booklist])
        tmp2 = [descriptions[_] for _ in booklist]
    elif sortorder == "canonical":
        tmp = "\n".join([books[_] for _ in CANONICALORDER if _ in books])
        tmp2 = [descriptions[_] for _ in CANONICALORDER if _ in books]
    else:
        with open(f"order-{sortorder}.txt", "r", encoding="utf_8") as order:
            bookorderstr = order.read()
            bookorder = [
                _ for _ in bookorderstr.split("\n") if _ != "" and not _.startswith("#")
            ]
        tmp = "\n".join([books[_] for _ in bookorder if _ in books])
        tmp2 = [descriptions[_] for _ in bookorder if _ in books]

    # check for strongs presence in osis
    strongsheader = STRONGSWORK if "<w " in tmp else ""

    # assemble osis doc in desired order
    osisdoc = "{}{}{}\n".format(
        OSISHEADER.format(
            workid,
            langcode,
            username,
            datetime.now().strftime("%Y.%m.%dT%H.%M.%S"),
            workid,
            workid,
            "\n".join(tmp2),
            langcode,
            workid,
            strongsheader,
        ),
        tmp,
        OSISFOOTER,
    )

    # Print note about references not being processed.
    LOG.warning("NOTE: References have not been processed.")

    # apply NFC normalization to text unless explicitly disabled.
    osisdoc2 = (
        encode(osisdoc, "utf_8")
        if nonormalize
        else encode(normalize("NFC", osisdoc), "utf_8")
    )

    # validate and "pretty print" our osis doc if requested.
    if HAVELXML:
        osisdoc2 = proc_xmlvalidate(osisdoc2)
    else:
        LOG.error("LXML needs to be installed for validation.")

    # debug output... don't use formatted xml...
    if dodebug:
        osisdoc2 = osisdoc.encode("utf_8")

    # find unhandled usfm tags that are leftover after processing
    usfmtagset: set[str] = set()
    usfmtagset.update(USFMRE.findall(osisdoc2.decode("utf_8")))
    if usfmtagset:
        LOG.warning("Unhandled USFM Tags: %s", ", ".join(sorted(usfmtagset)))

    # simple whitespace cleanups before writing to file...
    osisdoc2 = (
        osisdoc2.decode("utf_8")
        .replace(" <note", "<note")
        .replace(" </p>", "</p>")
        .replace(" </item>", "</item>")
        .replace(" </l>", "</l>")
        .replace("</w><w", "</w> <w")
        .replace(" </w>", "</w>")
        .replace("</w><transChange", "</w> <transChange")
        .replace("</transChange><w", "</transChange> <w")
        .encode("utf_8")
    )

    # write doc to file
    outfile = f"{workid}.osis" if outputfile is None else outputfile
    with open(outfile, "wb") as ofile:
        ofile.write(osisdoc2)

    if "TEST" in books:
        print(books["TEST"])


# -------------------------------------------------------------------------- #


if __name__ == "__main__":
    PARSER = ArgumentParser(
        formatter_class=ArgumentDefaultsHelpFormatter,
        description="""
            convert USFM bibles to OSIS.
        """,
        epilog=f"""
            * Version: {META["VERSION"]} * {META["DATE"]} * This script is public domain. *
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
    PARSER.add_argument("-o", help="specify output file", metavar="output_file")
    PARSER.add_argument(
        "-l", help="specify langauge code", metavar="LANG", default="und"
    )
    PARSER.add_argument(
        "-s", help="sort order", choices=BOOKORDERS, default="canonical"
    )
    PARSER.add_argument("-v", help="verbose output", action="store_true")
    PARSER.add_argument(
        "-x",
        help="",
        action="store_true",
    )
    PARSER.add_argument(
        "-n", help="disable unicode NFC normalization", action="store_true"
    )
    PARSER.add_argument(
        "file",
        help="file or files to process (wildcards allowed)",
        nargs="+",
        metavar="filename",
    )
    ARGS = PARSER.parse_args()

    if not HAVELXML:
        LOG.warning("Note:  lxml is not installed. Skipping OSIS validation.")

    ARGS.file = [_ for __ in ARGS.file for _ in chain(glob(__)) if os.path.isfile(_)]

    if ARGS.v:
        LOG.setLevel(logging.INFO)
    if ARGS.d:
        LOG.setLevel(logging.DEBUG)
    processfiles(
        ARGS.file,
        ARGS.e,
        ARGS.d,
        ARGS.s,
        ARGS.l,
        ARGS.n,
        ARGS.workid,
        ARGS.o,
    )
