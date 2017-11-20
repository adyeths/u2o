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