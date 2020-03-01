#!/usr/bin/env python
 
"""
Pandoc panflute filter to process code blocks with class "plantuml" into
plant-generated images.
"""

import codecs
import hashlib
import os
import pathlib
import sys
from panflute import toJSONFilter, Str, Para, Image, CodeBlock
from subprocess import call
 

DEFAULT_CODE = 'utf-8'

if (sys.version_info.major == 3) and (sys.version_info.minor < 7):  # for <=python3.6
    # for stdin
    sys.stdin = codecs.getreader(DEFAULT_CODE)(sys.stdin.buffer)
    # for stdout
    sys.stdout = codecs.getwriter(DEFAULT_CODE)(sys.stdout.buffer)
else:
    sys.stdin.reconfigure(encoding=DEFAULT_CODE)
    sys.stdout.reconfigure(encoding=DEFAULT_CODE)



imagedir = "plantuml-images"

GENERATE_IMAGE_FORMAT = "{}_{:03d}"

def sha1(x):
    return hashlib.sha1(x.encode()).hexdigest()
 
 
def filter_keyvalues(kv):
  res = []
  caption = []
  for k,v in kv:
    if k == "caption":
      caption = [ Str(v) ]
    else:
      res.append( [k,v] )
 
  return caption, "fig:" if caption else "", res
 
def filter_keyvalue_header(kv, index):
    res = []
    header = []


def get_plantuml_path():
    plantuml_path = os.getenv('PLANTUML_JAR', 'plantuml.jar')
    plantuml_path = plantuml_path.strip('"')

    return plantuml_path


def plantuml(elem, doc):
    identities = set()
    
    if hasattr(elem, "identifier"):
        if elem.identifier:
            identities.add(elem.identifier)

    if type(elem) == CodeBlock and 'plantuml' in elem.classes:
        if 'caption' in elem.attributes:
            caption = [Str(elem.attributes['caption'])]
            typef = 'fig:'
        else:
            caption = []
            typef = ''
 
        filename = sha1(elem.text)
        filetype = {'html': 'svg', 'latex': 'eps'}.get(doc.format, 'png')
        src = os.path.join(imagedir, filename + '.uml')
        dest = os.path.join(imagedir, filename + '.' + filetype)
        dest_dir = pathlib.Path(imagedir)

        if not os.path.isfile(dest):
            try:
                os.mkdir(imagedir)
                sys.stderr.write('Created directory ' + imagedir + '\n')
            except OSError:
                pass
 
            txt =  elem.text
            if not txt.startswith("@start"):
                txt = "@startuml\n" + txt + "\n@enduml\n"
            with open(src, "w", encoding=DEFAULT_CODE, errors='ignore') as f:
                f.write(txt)
 
            args = ["java",
                  "-jar", get_plantuml_path(),
                  '-Dfile.encoding="UTF-8"',
                  "-t"+filetype,
                  src]
            #sys.stderr.write('args = {}\n'.format(args))      
            call(args)
 
            sys.stderr.write('Created image ' + dest + '\n')
 
        return Para(Image(*caption, identifier=elem.identifier,
            attributes=elem.attributes, url=dest, title=typef))
 
if __name__ == "__main__":
    toJSONFilter(plantuml)
