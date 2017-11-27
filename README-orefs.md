# About the orefs.py script

## What Is This Thing?

This is an _**experimental**_ script that I wrote in an attempt to parse cross references and add the needed osisRef attribute to the reference tags in osis files. It is intended to eventually be integrated into u2o, but it needs a LOT more testing before that happens.

## Why Did I Attempt This

A while back, I added the ability to add the osisRef attribute to references by using the SWORD Lib if the python bindings were available. At the time, they were packaged for the linux distribution that I use. As time went on and I upgraded my system, I discovered that those python bindings were no longer being made available in the provided packages. How disappointing.

I could have resolved this problem in several ways.

1. I could ask for the SWORD libs to be included in the packages. (Not likely to happen.)
2. I could try to compile the SWORD lib and it's dependents myself. (Not likely to be successful.)
3. I could implement my own cross reference parsing.

I chose 3. It gave me something to do when I had nothing else more pressing that demanded my attention. It allowed me to potentially eliminate a dependency in the process.

# orefs config files

## Notes on usage

I added the ability to specify an external config file for the orefs utility. It has 2 sections. The first section is for specifying alternatives to the default delimiters used for cross reference parsing. The second section is for manually specifying the book names and abbreviations used for parsing cross references instead of having it done automatically.

## Example config file

The following is an example config file I used when I was testing this script. NOTE: All parts of the config file are required.

---

```markdown
[DEFAULT]
#
# WARNING! Make sure that all of these default values are different. If any of
# them are duplicated, it will cause problems for the reference parsing.
#
#
# SEPM specifies the character which separates multiple references
# SEPC specifies the character which separates chapters from verses
# SEPP specifies the character which separates multiple parts of a reference.
#      That is, multiple verses or verse ranges.
# SEPR specifies the character which separates the first part of a verse
#      range from the 2nd part of a verse range
# SEPRNORM is a list of characters that will be converted to SEPR during
#          processing of verse ranges to make things easier.
#

SEPM = ;
SEPC = :
SEPP = ,
SEPR = -
SEPRNORM = –—

[ABBR]
#
# This section contains comma separated book names and abbreviations used for
# processing cross references.
#
Gen = Genesis, Gen
Exod = Exodus, Exo
Lev = Leviticus, Lev
Num = Numbers, Num
Deut = Deuteronomy, Deu
Josh = Joshua, Jos
Judg = Judges, Jdg
Ruth = Ruth, Rut
1Sam = 1 Samuel, 1Sa
2Sam = 2 Samuel, 2Sa
1Kgs = 1 Kings, 1Ki
2Kgs = 2 Kings, 2Ki
1Chr = 1 Chronicles, 1Ch
2Chr = 2 Chronicles, 2Ch
PrMan = Prayer of Manasses, Man
Jub =
1En =
Ezra = Ezra, Ezr
Neh = Nehemiah, Neh
Tob = Tobit, Tob
Jdt = Judith, Jdt
Esth = Esther, Est
EsthGr = Esther Greek, ESG
1Meq =
2Meq =
3Meq =
Job = Job, Job
Ps = Psalms, Psalm
AddPs = Psalm 151, Ps151
5ApocSyrPss =
Odes =
Prov = Proverbs, Pro
Reproof =
Eccl = Ecclesiastes, Ecc
Song = Song of Solomon, Sng
Wis = Wisdom of Solomon, Wisdom, Wis
Sir = Sirach, Sir
PssSol =
Isa = Isaiah, Isa
Jer = Jeremiah, Jer
Lam = Lamentations, Lam
Bar = Baruch, Bar
EpJer =
2Bar =
EpBar =
4Bar =
Ezek = Ezekiel, Ezk
Dan = Daniel, Dan
DanGr = Daniel (Greek), DanielG
PrAzar =
Sus =
Bel =
Hos = Hosea, Hos
Joel = Joel, Jol
Amos = Amos, Amo
Obad = Obadiah, Oba
Jonah = Jonah, Jon
Mic = Micah, Mic
Nah = Nahum, Nam
Hab = Habakkuk, Hab
Zeph = Zephaniah, Zep
Hag = Haggai, Hag
Zech = Zechariah, Zec
Mal = Malachi, Mal
1Esd = 1 Esdras, 1Es
2Esd = 2 Esdras, 2Es
4Ezra =
5Ezra =
6Ezra =
1Macc = 1 Maccabees, 1Ma
2Macc = 2 Maccabees, 2Ma
3Macc = 3 Maccabees, 3Ma
4Macc = 4 Maccabees, 4Ma
Matt = Matthew, Mat
Mark = Mark, Mrk
Luke = Luke, Luk
John = John, Jhn
Acts = Acts, Act
Rom = Romans, Rom
1Cor = 1 Corinthians, 1Co
2Cor = 2 Corinthians, 2Co
Gal = Galatians, Gal
Eph = Ephesians, Eph
Phil = Philippians, Php
Col = Colossians, Col
1Thess = 1 Thessalonians, 1Th
2Thess = 2 Thessalonians, 2Th
1Tim = 1 Timothy, 1Ti
2Tim = 2 Timothy, 2Ti
Titus = Titus, Tit
Phlm = Philemon, Phm
Heb = Hebrews, Heb
Jas = James, Jas
1Pet = 1 Peter, 1Pe
2Pet = 2 Peter, 2Pe
1John = 1 John, 1Jn
2John = 2 John, 2Jn
3John = 3 John, 3Jn
Jude = Jude, Jud
Rev = Revelation, Rev
EpLao =

```
