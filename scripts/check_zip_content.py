import requests
import zipfile
import io

def check_zip(year):
    url = f"https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}FD.zip"
    print(f"Checking {url}...")
    r = requests.get(url)
    print(f"Size: {len(r.content)} bytes")
    try:
        z = zipfile.ZipFile(io.BytesIO(r.content))
        names = z.namelist()
        print(f"Files: {names}")
        
        if f'{year}FD.txt' in names:
            with z.open(f'{year}FD.txt') as f:
                lines = f.readlines()
                print(f"Index entries: {len(lines)}")
                for line in lines[:5]:
                    print(line.decode('utf-8').strip())
    except Exception as e:
        print(f"Error: {e}")

check_zip(2025)
