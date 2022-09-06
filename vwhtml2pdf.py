import os
import re
import json
import base64
from urllib.parse import unquote
from collections import OrderedDict

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import JavascriptException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.utils import ChromeType


def setup_driver(path, chrome_binary=None, window_size="1920,1080"):
    driver_options = Options()
    driver_options.add_argument('--headless')
    driver_options.add_argument('--disable-gpu')
    # driver_options.add_argument(f'--window-size={window_size}')   # FIXME
    # Make given chrome_binary visible to webdriver-manager
    if chrome_binary is not None:
        chrome_binary_path = os.path.dirname(chrome_binary)
        os.environ['PATH'] = ':'.join((chrome_binary_path, os.environ['PATH']))
        driver_options.binary_location = chrome_binary
    driver_manager = ChromeDriverManager(chrome_type=ChromeType.CHROMIUM,
                                         version="101.0.4951.41")
    driver_service = Service(driver_manager.install())
    driver = webdriver.Chrome(service=driver_service, options=driver_options)
    # Set script timeout to 1 minute
    driver.set_script_timeout(60)
    # Establish browser context
    driver.get(path)
    return driver

def js(driver, script, errors, execute_async=False, args=[]):
    try:
        if execute_async:
            if script.endswith(';'):
                script = script[:-1]
            script = f'var sel_cb = arguments[0]; sel_cb({script});'
            # print(f'[+] Executing async script: {script}')
            return driver.execute_async_script(script, *args)
        else:
            # print(f'[+] Executing script: {script}')
            return driver.execute_script(script, *args)
    except JavascriptException as jse:
        print(f'[!] Error while executing script: {jse}')
        errors.append((script, jse.__repr__()))

def set_attribute(driver, el, name, val, errors):
    script = 'arguments[0].setAttribute(arguments[1], arguments[2]);'
    js(driver, script, errors, args=[el, name, val])

def get_text_content(driver, el, errors):
    script = 'return arguments[0].textContent;'
    text = js(driver, script, errors, args=[el])
    if text is not None:
        text = text.strip()
    return text

# https://stackoverflow.com/a/65360714
def txt2filename(txt, chr_set='extended'):
    """Converts txt to a valid filename.

    Args:
        txt: The str to convert.
        chr_set:
            'printable':    Any printable character except those disallowed on Windows/*nix.
            'extended':     'printable' + extended ASCII character codes 128-255
            'universal':    For almost *any* file system. '-.0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    """

    FILLER = '-'
    # Maximum length of filename is 255 bytes in Windows and some *nix flavors.
    MAX_LEN = 255

    # Step 1: Remove excluded characters.
    # 127 is unprintable, the rest are illegal in Windows.
    BLACK_LIST = set(chr(127) + r'<>:"/\|?*')
    white_lists = {
        'universal': {'-.0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'},
        # 0-32, 127 are unprintable
        'printable': {chr(x) for x in range(32, 127)} - BLACK_LIST,
        'extended' : {chr(x) for x in range(32, 256)} - BLACK_LIST,
    }
    white_list = white_lists[chr_set]
    result = ''.join(x
                     if x in white_list else FILLER
                     for x in txt)

    # Step 2: Device names, '.', and '..' are invalid filenames in Windows.
    DEVICE_NAMES = 'CON,PRN,AUX,NUL,COM1,COM2,COM3,COM4,' \
                   'COM5,COM6,COM7,COM8,COM9,LPT1,LPT2,' \
                   'LPT3,LPT4,LPT5,LPT6,LPT7,LPT8,LPT9,' \
                   'CONIN$,CONOUT$,..,.'.split()
    if result in DEVICE_NAMES:
        result = f'-{result}-'

    # Step 3: Truncate long files while preserving the file extension.
    if len(result) > MAX_LEN:
        if '.' in txt:
            result, _, ext = result.rpartition('.')
            ext = '.' + ext
        else:
            ext = ''
        result = result[:MAX_LEN - len(ext)] + ext

    # Step 4: Windows does not allow filenames to end with '.' or ' '
    # or begin with ' '.
    result = re.sub(r'^[. ]', FILLER, result)
    result = re.sub(r' $', FILLER, result)

    return result

def waitforpage(driver, selector, timeout=15):
    WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
    )

def prepare_page(driver, errors, waitforselector='#tabs_sidebar', delay=2):
    # Wait for content to load
    waitforpage(driver, waitforselector)

    # Inject javascript functions
    # print('[|] Injecting javascript functions')
    with open('./jshacks.js') as jshacks:
        js(driver, jshacks.read(), errors)

    # Wait some time
    js(driver, f'hack_delay("{delay*1000}");', errors, execute_async=True)

    # Setup page layout
    cssrules = [
        '@page { size: B5; orphans:4; widows:2; }',
        'h2 { page-break-after : avoid }',
        'table { page-break-inside : avoid }',
        'div.segment { page-break-inside : avoid }',    # FIXME
        'div.subsegment { page-break-inside : avoid }', # FIXME
        'p { page-break-inside : avoid }',
        'li { page-break-inside : avoid }',
        # '@media print { @page { size: B5 portrait; margin: 0; } }', # FIXME
    ]
    for css in cssrules:
        js(driver, f'hack_injectcss("{css}");', errors)

def print_to_pdf(driver, print_options={}):
    # https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-printToPDF
    inch_factor = 25.4
    calculated_print_options = {
        'landscape': False,
        'displayHeaderFooter': False,
        'printBackground': True,
        # 'scale': 1.2,
        'paperWidth': 176 / inch_factor,
        'paperHeight': 250 / inch_factor,
        'marginTop': 1 / inch_factor,
        'marginBottom': 1 / inch_factor,
        'marginLeft': 1 / inch_factor,
        'marginRight': 1 / inch_factor,
	    'preferCSSPageSize': False,
    }
    calculated_print_options.update(print_options)
    res = driver.execute_cdp_cmd('Page.printToPDF', calculated_print_options)
    return base64.b64decode(res['data'])


def vin_login(driver, url, vin):
    # Navigate to destination
    driver.get(url)
    # Wait for content to load
    waitforpage(driver, '#vinInputFieldContainer')
    # Enter VIN
    selector = '#vinSplitInput > input.vinSplitInputPart'
    for elem in driver.find_elements(By.CSS_SELECTOR, selector):
        size = int(elem.get_attribute('size'))
        elem.send_keys(vin[:size])
        vin = vin[size:]
    # Submit
    elem = driver.find_element(By.CSS_SELECTOR, '#vinGoButton')
    elem.click()


def fetch_titlepage(driver):
    errors = []

    # Preprocessing
    prepare_page(driver, errors, waitforselector='div.welcome-vinmode-topics-col')
    # Remove disclaimer
    sel = '[ng-controller="disclaimerCtrl"]'
    js(driver, f'hack_hide_elems(\'{sel}\');', errors)
    sel = 'body > div.modal-backdrop.in'
    js(driver, f'hack_hide_elems(\'{sel}\');', errors)
    # Remove all but the latest manual version
    sel = 'div.welcome-vinmode-topics-col > [ng-controller="TopicCtrl"]'
    js(driver, f'hack_hide_elems_keep_first(\'{sel}\');', errors)
    # js(driver, f'window.hack_hide_older_versions();', errors)

    # Fetch toc button
    sel_tocbutton = 'a.topicLinkWrapper'
    el_tocbutton = driver.find_element(By.CSS_SELECTOR, sel_tocbutton)
    # Fetch version of the manual, i.e. car model
    sel_div = 'div.col-xs-8.title.complete'
    el_div = el_tocbutton.find_element(By.CSS_SELECTOR, sel_div)
    el_model = el_div.find_element(By.CSS_SELECTOR, sel_div + '> h3.modell-bez')
    el_title = el_div.find_element(By.CSS_SELECTOR, sel_div + '> h4.doc-title')
    el_version = el_div.find_element(By.CSS_SELECTOR, sel_div + '> div.modell-var')
    title = f'{el_title.text} - {el_model.text} - {el_version.text}'

    # Print to PDF
    pdf = print_to_pdf(driver)
    # Return all collected data
    return pdf, title, el_tocbutton, errors


def fetch_toc(driver, el_tocbutton):
    chapters = OrderedDict()
    errors = []

    # Navigate to destination
    el_tocbutton.click()

    # Wait for content to load
    js(driver, f'hack_delay("{6000}");', errors, execute_async=True)
    # waitforpage(driver, '#contentTable')
    # js(driver, f'hack_delay("{4000}");', errors, execute_async=True)

    # Setup page layout
    # js(driver, 'hack_injectcss("@page { margin: 5mm; }");', errors)   # FIXME

    def scroll_into_view(el):
        script = 'arguments[0].scrollIntoView(false);'
        js(driver, script, errors, args=[el])

    # Remove sidebar stickiness
    el_sb = driver.find_element(By.CSS_SELECTOR, 'div#sideBar')
    class_sb = el_sb.get_attribute('class')
    class_sb = class_sb.replace('cssSticky ', '')
    set_attribute(driver, el_sb, 'class', class_sb, errors)
    # Resize content table
    el_ts = driver.find_element(By.CSS_SELECTOR, 'div#tabs_sidebar')
    style_ts = el_ts.get_attribute('style')
    style_ts = re.sub(r'max-height: [0-9]+px', 'max-height: -1px', style_ts)
    set_attribute(driver, el_ts, 'style', style_ts, errors)
    el_toc = driver.find_element(By.CSS_SELECTOR, 'div#contentTable')
    style_toc = el_toc.get_attribute('style')
    style_toc = style_toc.replace('overflow-y: scroll', 'overflow-y: visible')
    style_toc = re.sub(r'max-height: [0-9]+px', 'max-height: -1px', style_toc)
    set_attribute(driver, el_toc, 'style', style_toc, errors)
    # Expand all sections
    print('[|] Expanding sections')
    els_plus = driver.find_elements(By.CSS_SELECTOR, 'span.mdi-plus')
    for el in els_plus:
        scroll_into_view(el)
        js(driver, 'hack_click(arguments[0]);', errors, args=[el])
        # Give the animation some time
        js(driver, f'hack_delay("{200}");', errors, execute_async=True)

    # Collect all toc links
    els_a = driver.find_elements(By.CSS_SELECTOR, 'a.vw-toc')
    for el_a in els_a:
        text = get_text_content(driver, el_a, errors)
        title = txt2filename(text)
        # print(f'[|] text "{text}" --> title "{title}"')
        url = el_a.get_attribute('href')
        if url not in chapters:
            chapters[url] = title
    print(f'[|] Found {len(els_a)} links ({len(chapters)} unique)')

    # Make sidebar invisible for printing
    el_sb = driver.find_element(By.CSS_SELECTOR, 'div#sideBar')
    set_attribute(driver, el_sb, 'style', 'display:none;', errors)
    # Print to PDF
    pdf = print_to_pdf(driver)
    # Return all collected data
    return pdf, chapters, errors

def fix_url(url, relative=True):
    if relative:
        url = url[24:]
    safechars = [
        '%26',  # &
        '%2c',  # ,
        '%2f',  # /
        '%c2',  # Â
        '%a0',  # '	 '
    ]
    # "Escape" our safechars
    for sc in safechars:
        url = url.replace(sc.upper(), sc.upper().replace('%', 'SAFECHAR'))
        url = url.replace(sc.lower(), sc.lower().replace('%', 'SAFECHAR'))
    # Unquote
    url = unquote(url)
    # "Unescape" our safechars
    url = url.replace('SAFECHAR', '%')

    return url

def fetch_chapter(driver, chapurl):
    errors = []

    # Load and prepare page
    driver.get(chapurl)
    try:
        prepare_page(driver, errors, waitforselector='h4.doc-title', delay=4)
    except TimeoutException as te:
        # Retry on above level
        return None, None, [te]

    # Remove disclaimer
    sel = '[ng-controller="disclaimerCtrl"]'
    js(driver, f'hack_hide_elems(\'{sel}\');', errors)
    sel = 'body > div.modal-backdrop.in'
    js(driver, f'hack_hide_elems(\'{sel}\');', errors)

    # Setup page layout
    # js(driver, 'hack_injectcss("@page { margin: 15mm; }");', errors)  # FIXME

    # Get breadcrumbs
    el_bcs = driver.find_elements(By.CSS_SELECTOR, 'ul.breadcrumb > li')
    breadcrumbs = []
    for el_bc in el_bcs:
        bc = get_text_content(driver, el_bc, errors)
        if bc != 'Umschlag':
            breadcrumbs.append(bc)
    el_title = driver.find_element(By.CSS_SELECTOR, 'h4.doc-title')
    doc_title = get_text_content(driver, el_title, errors)
    if len(breadcrumbs) > 0 and doc_title != breadcrumbs[-1]:
        breadcrumbs.append(doc_title)

    # Make sidebar invisible for printing
    el_sb = driver.find_element(By.CSS_SELECTOR, 'div#sideBar')
    set_attribute(driver, el_sb, 'style', 'display:none;', errors)
    # Print to PDF
    pdf = print_to_pdf(driver)

    # Return all collected data
    return pdf, breadcrumbs, errors

def fetch_manual(vin, vinurl, workdir, chrome_binary=None):
    print(f'[+] --- HTML2PDF ---')
    error_dict = {}
    files, filemap, topics = [], {}, {}
    titlepdfname = 'title.pdf'
    tocpdfname, tocjsonname = 'toc.pdf', 'toc.json'
    topicsjsonname = 'topics.json'
    filesjsonname, filemapjsonname = 'files.json', 'filemap.json'
    vinjsonname = 'vin.json'

    # Setup driver
    driver = setup_driver(vinurl, chrome_binary=chrome_binary)

    # Enter VIN
    vin_login(driver, vinurl, vin)
    fvjson = os.path.join(workdir, vinjsonname)
    with open(fvjson, 'w') as fp:
        json.dump(vin, fp)

    # Get titlepage
    fp = os.path.join(workdir, titlepdfname)
    print(f'[+] Fetching {driver.current_url} --> "{fp}"')
    titlepage, root_title, el_tocbutton, errors = fetch_titlepage(driver)
    with open(fp, 'wb') as file:
        file.write(titlepage)
    if len(errors) > 0:
        error_dict[driver.current_url] = errors
    files.append(titlepdfname)
    topics[titlepdfname] = [root_title]

    # Get toc
    tocurl = el_tocbutton.get_attribute('href')
    fp = os.path.join(workdir, tocpdfname)
    print(f'[+] Fetching {tocurl} --> "{fp}"')
    result, chapters, errors = fetch_toc(driver, el_tocbutton)
    with open(fp, 'wb') as file:
        file.write(result)
    if len(errors) > 0:
        error_dict[tocurl] = errors
    # add to files, chapters and filemap
    files.append(tocpdfname)
    topics[tocpdfname] = ['TOC']
    chapters[tocurl] = root_title
    filemap[tocurl] = tocpdfname
    fpjson = os.path.join(workdir, tocjsonname)
    print(f'[+] Storing link map --> "{fpjson}"')
    with open(fpjson, 'w') as fp:
        json.dump(chapters, fp)

    # Get additional pages
    fetch_amount = len(chapters) - 1
    for i, chapter_url in enumerate(chapters.keys()):
        if chapter_url == tocurl:
            continue
        num = i + 1
        fn = txt2filename(f'{num} - {chapters[chapter_url]}.pdf')
        fp = os.path.join(workdir, fn)
        filemap[chapter_url] = fn
        print(f'[{num}/{fetch_amount}] Fetching {chapter_url} --> "{fp}"')
        result, breadcrumbs, errors = fetch_chapter(driver, chapter_url)
        retry_counter = 0
        while len(errors) > 0 and retry_counter < 2:
            retry_counter += 1
            print(f'[{num}/{fetch_amount}] Retry: {chapter_url} --> "{fp}"')
            result, breadcrumbs, errors = fetch_chapter(driver, chapter_url)
        with open(fp, 'wb') as file:
            file.write(result)
        files.append(fn)
        topics[fn] = breadcrumbs
        if len(errors) > 0:
            error_dict[chapter_url] = errors

    # Store files list
    fjson = os.path.join(workdir, filesjsonname)
    print(f'[+] Storing files list --> "{fjson}"')
    with open(fjson, 'w') as f:
        json.dump(files, f)
    # Store topics
    ftjson = os.path.join(workdir, topicsjsonname)
    print(f'[+] Storing topic hierarchy --> "{ftjson}"')
    with open(ftjson, 'w') as ft:
        json.dump(topics, ft)
    # Store file map
    fmjson = os.path.join(workdir, filemapjsonname)
    print(f'[+] Storing file map --> "{fmjson}"')
    with open(fmjson, 'w') as fp:
        json.dump(filemap, fp)

    # Shutdown driver
    driver.quit()

    # Error handling
    if len(error_dict) > 0:
        print()
        print(f'[!] There have been error(s) on {len(error_dict)} page(s):')
        for k, v in error_dict.items():
            print(f'[+] {k}')
            for e in v:
                print(f'[|] {e}')
        errjson = os.path.join(workdir, 'errors.json')
        print(f'[+] Storing error map --> "{errjson}"')
        with open(errjson, 'w') as fp:
            json.dump(error_dict, fp)
