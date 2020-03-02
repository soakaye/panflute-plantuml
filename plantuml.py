#!/usr/bin/env python

"""
Pandoc panflute filter to process code blocks with class "plantuml" into
'plantuml-images' images.
"""

import codecs
import hashlib
import os
import pathlib
import re
import sys
from subprocess import call

from panflute import CodeBlock, Header, Image, Para, Str, toJSONFilter

# default encode
DEFAULT_CODE = 'utf-8'

MAX_IDENT_RENAME_NUM = 10

# output image directory
IMAGEDIR = "plantuml-images"

# newpage diagram name format
SPLIT_DIAGRAM_NAME_FORMAT = "{}{}"

# identites
identities = set()

# set stdin/stdout encoding: utf-8
if (sys.version_info.major == 3) and (sys.version_info.minor < 7):  # for <=python3.6
    sys.stdin = codecs.getreader(DEFAULT_CODE)(sys.stdin.buffer)
    sys.stdout = codecs.getwriter(DEFAULT_CODE)(sys.stdout.buffer)
else:
    sys.stdin.reconfigure(encoding=DEFAULT_CODE)
    sys.stdout.reconfigure(encoding=DEFAULT_CODE)


def sha1(x):
    return hashlib.sha1(x.encode()).hexdigest()


def make_new_ident(ident):
    if ident in identities:
        for id in range(1, MAX_IDENT_RENAME_NUM+1):
            new_ident = '{}-{}'.format(ident, id)
            if new_ident in identities:
                continue
            else:
                ident = new_ident
                break

    return ident


def get_header(attrib, suffix):
    if not suffix:
        header_attribute = 'header'
    else:
        header_attribute = SPLIT_DIAGRAM_NAME_FORMAT.format('header', suffix)

    if header_attribute in attrib:
        header_str = attrib[header_attribute]
        if header_str:
            msgs = header_str.split(',', 1)
            if len(msgs) != 2:
                level = 1
                title_str = msgs[0]
            else:
                try:
                    level = int(msgs[0].strip())
                    title_str = msgs[1]
                except:
                    level = 1
                    title_str = msgs[1]
            
            ident = make_new_ident(re.sub('[ \t\n]', '-', title_str))
            identities.add(ident)

            title = [Str(title_str)]
            header = Header(*title, level=level, identifier=ident)
            return header

    return None


def get_caption_attribute(attrib, suffix):
    if not suffix:
        caption_attribute = 'caption'
    else:
        caption_attribute = SPLIT_DIAGRAM_NAME_FORMAT.format('caption', suffix)

    if caption_attribute in attrib:
        caption_str = attrib[caption_attribute]
        if caption_str:
            return ([Str(caption_str)], 'fig:')

    return ([], '')


def get_plantuml_jar():
    plantuml_jar = os.getenv(
        'PLANTUML_JAR', 'plantuml.jar').strip('"').strip("'")

    return plantuml_jar


def plantuml(elem, doc):
    if type(elem) == CodeBlock and 'plantuml' in elem.classes:
        filename = sha1(elem.text)
        filetype = {'html': 'svg', 'latex': 'eps'}.get(doc.format, 'png')
        src = os.path.join(IMAGEDIR, filename + '.uml')
        dest = os.path.join(IMAGEDIR, filename + '.' + filetype)
        dest_dir = pathlib.Path(IMAGEDIR)

        if not os.path.isfile(dest):
            try:
                os.mkdir(IMAGEDIR)
                sys.stderr.write('Created directory ' + IMAGEDIR + '\n')
            except OSError:
                pass

            txt = elem.text
            if not txt.startswith("@start"):
                txt = "@startuml\n" + txt + "\n@enduml\n"
            with open(src, "w", encoding=DEFAULT_CODE, errors='ignore') as f:
                f.write(txt)

            args = ["java", "-jar", get_plantuml_jar(),
                    "-Dfile.encoding=UTF-8",
                    "-charset", "UTF-8",
                    "-t"+filetype,
                    src]
            call(args)

            #sys.stderr.write('Created image ' + dest + '\n')

        dest_files = sorted(dest_dir.glob(filename + '*.' + filetype))

        parts = []
        for i, image in enumerate(dest_files):
            rel = image.relative_to(dest_dir)
            sys.stderr.write('Created image {} - {}\n'.format(i+1,
                                                              os.path.join(dest_dir.name, rel)))
            dest_image = str(image)
            basename = image.with_suffix('').name
            suffix = basename[len(filename):]

            head = get_header(elem.attributes, suffix)
            if head:
                parts.append(head)

            caption, typef = get_caption_attribute(elem.attributes, suffix)

            if i == 0:
                im = Image(*caption, identifier=elem.identifier,
                           attributes=elem.attributes, url=dest_image, title=typef)
                identities.add(elem.identifier)
            else:
                ident = SPLIT_DIAGRAM_NAME_FORMAT.format(
                    elem.identifier, suffix)
                new_ident = make_new_ident(ident)
                identities.add(new_ident)

                im = Image(*caption, identifier=new_ident,
                           attributes=elem.attributes, url=dest_image, title=typef)

            parts.append(Para(im))

        return parts

    elif hasattr(elem, "identifier"):
        if elem.identifier:
            identities.add(elem.identifier)



if __name__ == "__main__":
    toJSONFilter(plantuml)
