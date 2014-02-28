"""
Pelican BibTeX
==============

A Pelican plugin that populates the context with a list of formatted
citations, loaded from a BibTeX file at a configurable path.

The use case for now is to generate a ``Publications'' page for academic
websites.
"""
# Author: Vlad Niculae <vlad@vene.ro>
# Unlicense (see UNLICENSE for details)

import os

import logging
logger = logging.getLogger(__name__)

from pelican import signals

__version__ = '0.2'


def add_publications(generator):
    """
    Populates context with a list of BibTeX publications.

    Configuration
    -------------
    generator.settings['PUBLICATIONS_SRC']:
        local path to the BibTeX file to read.

    Output
    ------
    generator.context['publications']:
        List of tuples (key, year, text, bibtex, pdf, slides, poster).
        See Readme.md for more details.

    """
    # check if settings are provided via pelicanconf.py
    settings_present = False
    for s in ['PUBLICATIONS_SRC','PRESENTATIONS_SRC', 'POSTERS_SRC']:
        if s in generator.settings:
            settings_present = True
    if not settings_present:
        return

    try:
        from StringIO import StringIO
    except ImportError:
        from io import StringIO
    try:
        from pybtex.database.input.bibtex import Parser
        from pybtex.database.output.bibtex import Writer
        from pybtex.database import BibliographyData, PybtexError
        from pybtex.backends import html
        from pybtex.style.formatting import plain
    except ImportError:
        logger.warn('`pelican_bibtex` failed to load dependency `pybtex`')
        return

    for s, c in zip(['PUBLICATIONS_SRC','PRESENTATIONS_SRC', 'POSTERS_SRC'], 
                    ['publications','presentations', 'posters']):
        if s not in generator.settings:
            continue
        refs_file = generator.settings[s]
        try:
            bibdata_all = Parser().parse_file(refs_file)
        except PybtexError as e:
            logger.warn('`pelican_bibtex` failed to parse file %s: %s' % (
                refs_file,
                str(e)))
            continue

        publications = []

        # format entries
        plain_style = plain.Style()
        html_backend = html.Backend()
        formatted_entries = plain_style.format_entries(bibdata_all.entries.values())

        for formatted_entry in formatted_entries:
            key = formatted_entry.key
            entry = bibdata_all.entries[key]
            year = entry.fields.get('year')
            slides = entry.fields.pop('slides', None)
            poster = entry.fields.pop('poster', None)
            
            # add PDF link is file is present
            # Zotero exports a 'file' field, which contains the 'Zotero' and
            # 'Filesystem' filenames, seperated by ':'
            filename = entry.fields['file'].split(':')[0]
            if os.access(os.path.join('content', 'download', filename), os.R_OK):
                pdf = os.path.join('download', filename)
            else:
                pdf = None

            #render the bibtex string for the entry
            bib_buf = StringIO()
            bibdata_this = BibliographyData(entries={key: entry})
            Writer().write_stream(bibdata_this, bib_buf)
            text = formatted_entry.text.render(html_backend)
            doi = entry.fields.get('doi') if 'doi' in entry.fields.keys() else ""
            url = entry.fields.get('url') if 'url' in entry.fields.keys() else ""

            # prettify entries
            # remove BibTeX's {}
            text = text.replace("\{", "")
            text = text.replace("{", "")
            text = text.replace("\}", "")
            text = text.replace("}", "")
            # subscript 2 in NO2, CO2, SO2
            text = text.replace("NO2", "NO<sub>2</sub>")
            text = text.replace("CO2", "CO<sub>2</sub>")
            text = text.replace("CO2", "CO<sub>2</sub>")
            # for posters and presentations, make for nicer printing
            text = text.replace("In <em>", "Presented at <em>")

            publications.append((key,
                                 year,
                                 text,
                                 bib_buf.getvalue(),
                                 doi,
                                 url,
                                 pdf,
                                 slides,
                                 poster))

            # store the list of artifacts in the generator context
            generator.context[c] = publications


def register():
    signals.generator_init.connect(add_publications)
