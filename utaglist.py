#!/usr/bin/env python3

"""
List ufm tags.

A simple script to generate a list of usfm tags that were used in one
or more utf8 encoded usfm files. Requires python3.

This script is public domain.

"""

import argparse
import re
import collections
import glob
from typing import Counter, List

# -------------------------------------------------------------------------- #

VERSION = "1.1.2"

# -------------------------------------------------------------------------- #

# set of known usfm tags in version 3.0 of usfm specification
# I think I have all the tags here.
KNOWNTAGS = {
    # identification
    r"\id",
    r"\ide",
    r"\sts",
    r"\rem",
    r"\h",
    r"\h1",
    r"\h2",
    r"\h3",
    r"\toc1",
    r"\toc2",
    r"\toc3",
    # introductions
    r"\imt",
    r"\imt1",
    r"\imt2",
    r"\imt3",
    r"\imt4",
    r"\is",
    r"\is1",
    r"\is2",
    r"\ip",
    r"\ipi",
    r"\im",
    r"\imi",
    r"\ipq",
    r"\imq",
    r"\ipr",
    r"\iq",
    r"\iq1",
    r"\iq2",
    r"\iq3",
    r"\ib",
    r"\ili",
    r"\ili1",
    r"\ili2",
    r"\iot",
    r"\io",
    r"\io1",
    r"\io2",
    r"\io3",
    r"\io4",
    r"\ior",
    r"\ior*",
    r"\iex",
    r"\iqt",
    r"\iqt*",
    r"\imte",
    r"\imte1",
    r"\imte2",
    r"\ie",
    # titles, headings, labels
    r"\mt",
    r"\mt1",
    r"\mt2",
    r"\mt3",
    r"\mt4",
    r"\mte",
    r"\mte1",
    r"\mte2",
    r"\ms",
    r"\ms1",
    r"\ms2",
    r"\ms3",
    r"\mr",
    r"\s",
    r"\s1",
    r"\s2",
    r"\s3",
    r"\s4",
    r"\sr",
    r"\r",
    r"\rq",
    r"\rq*",
    r"\d",
    r"\sp",
    # chapters and verses
    r"\c",
    r"\ca",
    r"\ca*",
    r"\cl",
    r"\cp",
    r"\cd",
    r"\v",
    r"\va",
    r"\va*",
    r"\vp",
    r"\vp*",
    # paragraphs/poetry
    r"\p",
    r"\po",
    r"\m",
    r"\pmo",
    r"\pm",
    r"\pmc",
    r"\pmr",
    r"\pi",
    r"\pi1",
    r"\pi2",
    r"\pi3",
    r"\mi",
    r"\nb",
    r"\cls",
    r"\lh",
    r"\lf",
    r"\li",
    r"\li1",
    r"\li2",
    r"\li3",
    r"\li4",
    r"\lim",
    r"\lim1",
    r"\lim2",
    r"\lim3",
    r"\lim4",
    r"\lim5",
    r"\pc",
    r"\pr",
    r"\ph",
    r"\ph1",
    r"\ph2",
    r"\ph3",
    r"\q",
    r"\q1",
    r"\q2",
    r"\q3",
    r"\q4",
    r"\qr",
    r"\qc",
    r"\qs",
    r"\qs*",
    r"\qa",
    r"\qac",
    r"\qac*",
    r"\qm",
    r"\qm1",
    r"\qm2",
    r"\qm3",
    r"\qd",
    r"\lik",
    r"\lik*",
    r"\litl",
    r"\litl*",
    r"\ts",
    r"\sd",
    r"\sd1",
    r"\sd2",
    r"\sd3",
    r"\sd4",
    r"\sd5",
    r"\b",
    # tables
    r"\tr",
    r"\th",
    r"\th1",
    r"\th2",
    r"\th3",
    r"\th4",
    r"\th5",
    r"\thr",
    r"\thr1",
    r"\thr2",
    r"\thr3",
    r"\thr4",
    r"\thr5",
    r"\tc",
    r"\tc1",
    r"\tc2",
    r"\tc3",
    r"\tc4",
    r"\tc5",
    r"\tcr",
    r"\tcr1",
    r"\tcr2",
    r"\tcr3",
    r"\tcr4",
    r"\tcr5",
    # footnotes
    r"\f",
    r"\f*",
    r"\fe",
    r"\fe*",
    r"\fr",
    r"\fk",
    r"\fq",
    r"\fqa",
    r"\fl",
    r"\fp",
    r"\fv",
    r"\fv*",
    r"\ft",
    r"\fdc",
    r"\fdc*",
    r"\fm",
    r"\fm*",
    # cross references
    r"\x",
    r"\x*",
    r"\xo",
    r"\xk",
    r"\xq",
    r"\xt",
    r"\xot",
    r"\xot*",
    r"\xnt",
    r"\xnt*",
    r"\xdc",
    r"\xdc*",
    r"\xta",
    r"\xta*",
    r"\xop",
    r"\xop*",
    # special text
    r"\add",
    r"\add*",
    r"\bk",
    r"\bk*",
    r"\dc",
    r"\dc*",
    r"\k",
    r"\k*",
    r"\lit",
    r"\nd",
    r"\nd*",
    r"\ord",
    r"\ord*",
    r"\pn",
    r"\pn*",
    r"\qt",
    r"\qt*",
    r"\sig",
    r"\sig*",
    r"\sls",
    r"\sls*",
    r"\tl",
    r"\tl*",
    r"\wj",
    r"\wj*",
    r"\addpn",
    r"\addpn*",
    r"\+add",
    r"\+add*",
    r"\+bk",
    r"\+bk*",
    r"\+dc",
    r"\+dc*",
    r"\+k",
    r"\+k*",
    r"\+nd",
    r"\+nd*",
    r"\+ord",
    r"\+ord*",
    r"\+pn",
    r"\+pn*",
    r"\+qt",
    r"\+qt*",
    r"\+sig",
    r"\+sig*",
    r"\+sls",
    r"\+sls*",
    r"\+tl",
    r"\+tl*",
    r"\+wj",
    r"\+wj*",
    r"\+addpn",
    r"\+addpn*",
    # character styles
    r"\em",
    r"\em*",
    r"\bd",
    r"\bd*",
    r"\it",
    r"\it*",
    r"\bdit",
    r"\bdit*",
    r"\no",
    r"\no*",
    r"\sc",
    r"\sc*",
    r"\+em",
    r"\+em*",
    r"\+bd",
    r"\+bd*",
    r"\+it",
    r"\+it*",
    r"\+bdit",
    r"\+bdit*",
    r"\+no",
    r"\+no*",
    r"\+sc",
    r"\+sc*",
    # spacing
    r"\pb",
    # special features
    r"\fig",
    r"\fig*",
    r"\ndx",
    r"\ndx*",
    r"\pro",
    r"\pro*",
    r"\w",
    r"\w*",
    r"\wg",
    r"\wg*",
    r"\wh",
    r"\wh*",
    r"\wa",
    r"\wa*",
    r"\png",
    r"\png*",
    r"\jmp",
    r"\jmp*",
    r"\rb",
    r"\rb*",
    r"\rt",
    r"\rt*",
    # peripherals
    r"\periph",
    # study bible content
    r"\ef",
    r"\ef*",
    r"\ex",
    r"\ex*",
    r"\esb",
    r"\esbe",
    r"\cat",
    r"\cat*",
    # milestone quotations
    r"\qt-s",
    r"\qt1-s",
    r"\qt2-s",
    r"\qt3-s",
    r"\qt4-s",
    r"\qt5-s",
    r"\qt-e",
    r"\qt1-e",
    r"\qt2-e",
    r"\qt3-e",
    r"\qt4-e",
    r"\qt5-e",
    r"\*",
}

# regex for finding usfm tags
USFMRE = re.compile(
    r"""
    # handle usfm tags other than special spacing...
    (?:
        # the first character of a usfm tag is always a backslash
        \\

        # a plus symbol marks the start of a nested character style.
        # this may or may not be present.
        \+?

        # tag names are ascii letters
        [A-Za-z]+

        # tags may or may not be numbered
        [0-9]?

        # a word boundary to mark the end of our tags.
        \b

        # character style closing tags end with an asterisk.
        \*?
    )

    # OR...
    |

    # one of the two special spacing tags.
    (?:
        (?:~|//)
    )
""",
    re.U + re.VERBOSE,
)

# -------------------------------------------------------------------------- #


def processtags(fnames: List[str], tcounts: bool) -> None:
    """Process usfm tags in all files."""
    count = 0
    counttags: Counter[str] = collections.Counter()
    knownset = set()

    filenames = []
    for _ in fnames:
        if "*" in _:
            filenames.extend(glob.glob(_))
        else:
            filenames.append(_)

    for fname in filenames:
        with open(fname, "rb") as infile:
            intext = infile.read()

            # build tag set
            knownset.update(USFMRE.findall(intext.decode("utf8")))

            # build usage counts
            for i in USFMRE.findall(intext.decode("utf8")):
                count += 1
                counttags[i] += 1

    # split tags into known and unknown sets
    unknownset = knownset.difference(KNOWNTAGS)
    knownset = knownset.intersection(KNOWNTAGS)

    # output results.
    print()
    if knownset:
        print(f"Known USFM Tags: {', '.join(sorted(knownset))}\n")
    if unknownset:
        print(f"Unknown USFM Tags: {', '.join(sorted(unknownset))}\n")

    # print tag usage counts
    if tcounts:
        print("\nTag usage count:\n")
        for i in sorted(counttags):
            print(f"{counttags[i]: 8} - {i}")
        print(f"\nTotal number of usfm tags found:   {count}\n")


# -------------------------------------------------------------------------- #


if __name__ == "__main__":
    PARSER = argparse.ArgumentParser(
        description="""
            A simple script to generate a list of usfm tags that were used in
           one or more utf8 encoded usfm files.
        """,
        epilog=f"""
            * Version: {VERSION} * This script is public domain *
        """,
    )
    PARSER.add_argument(
        "-c", help="include usage counts for tags", action="store_true"
    )
    PARSER.add_argument(
        "file", help="name of file to process (wildcards allowed)", nargs="+"
    )
    ARGS = PARSER.parse_args()

    processtags(ARGS.file, ARGS.c)
