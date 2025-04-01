# What is u2o?

u2o is a fast python conversion program that is used to convert [usfm](http://paratext.org/about/usfm) formatted bibles to [osis xml](http://bibletechnologies.net/). Currently it targets [version 3.0 of the usfm specification](http://ubsicap.github.io/usfm/) that bible translators use when translating scripture into different languages.

# Why did I write it?

[The SWORD Project](http://www.crosswire.org/) had a script called usfm2osis.py that they used for converting usfm formatted bibles to osis xml for use with their software. Since I'm familiar with python, I decided to test it out to see how well it worked. It was the result of that testing that prompted me to write this alternative.

* The usfm2osis.py converter mentioned above ran way too slow on my older computer. (It took more than 2 minutes to process the World English Bible). I thought I could make one that ran faster.

* The usfm2osis.py source is difficult for me to read, so I'm unable to work on improving it. I think my difficulty is with the huge amount of complicated regular expressions that it uses... about 200! Which reminds me of a Jamie Zawinski quote.... *“Some people, when confronted with a problem, think ‘I know, I'll use regular expressions.’ Now they have two problems.”* (Sometimes they make sense, though. The script I wrote uses some.)

* I wanted a converter that worked with python3.

* I wanted a converter that would be easy to update when changes are made to the USFM standard.

* I thought it would be a fun project. (it was!)

# The Result

u2o is quite fast. For example, it only takes about 10 seconds to process the World English Bible on my old computer. *That's about a 90% reduction in processing time compared with usfm2osis.py in my testing.*

The output validates against the OSIS 2.1.1 schema. No markup errors are reported by osis2mod when generating modules for any of the bibles that I have access to at this time.

Should work fine for any version of CPython that is currently supported by the python developers. (as of april 2025 this would be python 3.9+)

# The Alternatives

There are of course other programs that convert usfm to osis. Here are the ones I am familiar with:

* [usfm2osis.py](https://github.com/chrislit/usfm2osis) - The version by it's original developer. (no longer maintained)

* [usfm2osis.py](https://github.com/refdoc/Module-tools) - The version that was used by The SWORD Project prior to them switching over to my converter. (Seems to require Python2.)

* [haiola](http://haiola.org/) - Very nice. Converts to many different formats, not just osis.

# cu2o

This is a simple wrapper for u2o.py that will allow processing of usfm files that are concatenated into a single file. Consider it experimental. Note that it *requires* u2o in order to work.
