import sys
import os
import json
import argparse

import PyPDF2


def build_manual(workdir, outdir, outf):
    print(f'[+] --- PDFLINKER ---')
    with open(os.path.join(workdir, 'files.json')) as ff:
        # sorted list of filenames, primary key
        files = json.load(ff)
    with open(os.path.join(workdir, 'filemap.json')) as ffm:
        # dict: URL --> filename
        filemap = json.load(ffm)
    with open(os.path.join(workdir, 'toc.json')) as ftj:
        # dict: URL --> title
        chaptermap = json.load(ftj)
    with open(os.path.join(workdir, 'topics.json')) as ftsj:
        # dict: filename --> [optional: bm_section, optional: bm_subsection, title]
        topics = json.load(ftsj)
    with open(os.path.join(workdir, 'vin.json')) as fvj:
        # VIN
        vin = json.load(fvj)

    # Build output document
    writer = PyPDF2.PdfFileWriter()
    chapter_indexes = {}

    titlef = files[0]
    print(f'[+] Adding titlepage: "{titlef}"')
    titlereader = PyPDF2.PdfFileReader(os.path.join(workdir, titlef))
    chapter_indexes[titlef] = len(writer.pages) + 1
    for page in titlereader.pages:
        # Add current page to output
        # print(f'[|] WRITING PAGE {len(writer.pages) + 1}')
        writer.addPage(page)

    tocf = files[1]
    print(f'[+] Adding toc file: "{tocf}"')
    tocreader = PyPDF2.PdfFileReader(os.path.join(workdir, tocf))
    chapter_indexes[tocf] = len(writer.pages) + 1
    for page in tocreader.pages:
        # Add current page to output
        # print(f'[|] WRITING PAGE {len(writer.pages) + 1}')
        writer.addPage(page)

    print('[+] Adding chapters')
    # Build chapter pages map
    current_index = len(writer.pages) + 1
    for chfname in files[2:]:
        # print(f'[|] Adding chapter: "{chfname}"')
        chreader = PyPDF2.PdfFileReader(os.path.join(workdir, chfname))
        chapter_indexes[chfname] = current_index
        current_index += len(chreader.pages)
        for page in chreader.pages:
            # print(f'[|] WRITING PAGE {len(writer.pages) + 1}')
            writer.addPage(page)

    # Add bookmarks
    print('[+] Adding bookmarks')
    bookmarks = {}
    for f in files:
        tree = topics[f]
        section = None
        subsection = None
        title = tree[-1]
        dstpg = chapter_indexes[f] - 1  # TODO I don't know why we have to substract 1 here
        if len(tree) == 3:
            section = tree[-3]
            if section not in bookmarks:
                # print(f'[|] Bookmark: section "{section}" --> page {dstpg}')
                bookmarks[section] = writer.addBookmark(section, dstpg)
        if len(tree) >= 2:
            subsection = tree[-2]
            if subsection not in bookmarks:
                # print(f'[|] Bookmark: subsection "{subsection}" --> page {dstpg}')
                bookmarks[subsection] = writer.addBookmark(subsection, dstpg,
                        parent=bookmarks.get(section, None))
        # print(f'[|] Bookmark: topic "{title}" --> page {dstpg}')
        writer.addBookmark(title, dstpg, parent=bookmarks.get(subsection, None))
    # Activate bookmark panel on startup
    writer.setPageMode('/UseOutlines')

    # Add metadata
    root_url = list(filemap.keys())[list(filemap.values()).index(tocf)]
    root_title = chaptermap[root_url]
    git_url = 'https://github.com/ambimanus/vwmanual'
    writer.addMetadata(
        {
            '/Title': root_title,
            '/Author': git_url,
            '/Subject': vin
        }
    )

    # Write output file
    sys.setrecursionlimit(10000) # FIXME
    if outf is None:
        outf = '.'.join((chaptermap[root_url], 'pdf'))
    outfile = os.path.join(outdir, outf)
    print(f'[+] Writing output file: "{outfile}"')
    os.makedirs(outdir, exist_ok=True)
    with open(outfile, 'wb') as f:
        writer.write(f)


def make_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument('--workdir', required=True)
    parser.add_argument('--output', help="Output filename [default: './Betriebsanleitung - <car model> - Ausgabe <month>.<year>.pdf']")

    return parser


if __name__ == '__main__':
    parser = make_parser()
    args = parser.parse_args()

    # Set output filename
    if args.output is not None:
        outdir, outfilename = os.path.split(args.output)
    else:
        outdir, outfilename = '.', None

    build_manual(args.workdir, outdir, outfilename)