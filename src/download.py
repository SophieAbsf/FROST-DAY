import requests
from pathlib import Path

BASE_URL = "https://object.files.data.gouv.fr/meteofrance/data/synchro_ftp/BASE/QUOT/"


def download_file(filename, save_dir="data/raw"):
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    url = BASE_URL + filename
    filepath = save_dir / filename

    response = requests.get(url, stream=True)
    response.raise_for_status()

    with open(filepath, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    return filepath