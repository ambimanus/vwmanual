import os
import argparse
import tempfile

import vwhtml2pdf
import pdflinker

def make_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument('--chromium-binary', required=True, help="Path to chromium binary 982481 (101.0.4951.0)")
    parser.add_argument('--vin', default='WVWZZZE1ZNP000000', help="Vehicle Identification Number (VIN) [default: %(default)s (which is ID.3 MY22)]")
    parser.add_argument('--vin-login', default='https://userguide.volkswagen.de/public/vin/login/de_DE', help="VIN login page [default: %(default)s]")
    parser.add_argument('--keep-tmp-files', help='Don\'t delete temporary files', action='store_true')
    parser.add_argument('--output', help="Output filename [default: './Betriebsanleitung - <car model> - Ausgabe <month>.<year>.pdf']")

    return parser

if __name__ == '__main__':
    parser = make_parser()
    args = parser.parse_args()
    # print(f"Reporting command line arguments: {args}")

    # Create temporary workdir
    if args.keep_tmp_files:
        workdir = tempfile.mkdtemp()
    else:
        tdirobj = tempfile.TemporaryDirectory()
        workdir = tdirobj.name
    # print(f'[+] Storing temporary files in "{workdir}"')

    # Set output filename
    if args.output is not None:
        outdir, outfilename = os.path.split(args.output)
    else:
        outdir, outfilename = '.', None

    vwhtml2pdf.fetch_manual(args.vin, args.vin_login, workdir,
                            args.chromium_binary)
    pdflinker.build_manual(workdir, outdir, outfilename)