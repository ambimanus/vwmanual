# vwmanual

Convert the online Volkswagen car manual into a PDF.

Needs a recent stable version of the **chromium** browser (not chrome).

```
usage: main.py [-h] --chromium-binary CHROMIUM_BINARY [--vin VIN] [--vin-login VIN_LOGIN] [--keep-tmp-files] [--output OUTPUT]

optional arguments:
  -h, --help            show this help message and exit
  --chromium-binary CHROMIUM_BINARY
                        Path to chromium binary 982481 (101.0.4951.0)
  --vin VIN             Vehicle Identification Number (VIN) [default: WVWZZZE1ZNP000000 (which is ID.3 MY22)]
  --vin-login VIN_LOGIN
                        VIN login page [default: https://userguide.volkswagen.de/public/vin/login/de_DE]
  --keep-tmp-files      Don't delete temporary files
  --output OUTPUT       Output filename [default: './Betriebsanleitung - <car model> - Ausgabe <month>.<year>.pdf']
```

## Step by step instructions

Using bash on Ubuntu. Don't do this as `root`, otherwise chromium won't start later on. Instead, create a normal user and use `sudo` in step 5.

1. Get the code, i.e. clone the repository into a local folder:

   ```
   $ git clone https://github.com/ambimanus/vwmanual.git
   ```

2. Create a virtual environment:

   ```
   $ cd vwmanual
   $ mkdir .venv && python3 -m venv .venv
   ```

3. Activate the virtual environment and install dependencies:

   ```
   $ source .venv/bin/activate
   (.venv) $ pip install -r requirements.txt
   ```

4. Make sure that a recent stable version of chromium 101.0.4951.0 is
   available. In my setup, I fetched a standalone version like this:

   ```
   (.venv) $ curl -o 982481-chrome-linux.zip https://www.googleapis.com/download/storage/v1/b/chromium-browser-snapshots/o/Linux_x64%2F982481%2Fchrome-linux.zip?alt=media
   (.venv) $ unzip 982481-chrome-linux.zip -d 982481/
   ```

5. If you are running a fresh LXC container, you'll most likely need to install some chromium dependencies:

   ```
   (.venv) $ sudo apt install libasound2 libatk-bridge2.0-0 libatk1.0-0 libatspi2.0-0 libcairo2 libcups2 libdbus-1-3 libdrm2 libexpat1 libgbm1 libgcc1 libgdk-pixbuf2.0-0 libglib2.0-0 libgtk-3-0 libnspr4 libnss3 libpango-1.0-0 libpangocairo-1.0-0
   ```

6. Run the script while pointing to the chromium binary:

   ```
   (.venv) $ python main.py --chromium-binary 982481/chrome-linux/chrome
   ```
