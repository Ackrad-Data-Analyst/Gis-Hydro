from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

KML = '''<?xml version="1.0"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document><Folder><Placemark><name>Synthetic boundary</name><Polygon><outerBoundaryIs><LinearRing><coordinates>-112,33,0 -111,33,0 -111,34,0 -112,33,0</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark></Folder></Document></kml>'''

def make_kmz(path: Path) -> Path:
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("doc.kml", KML)
    return path
