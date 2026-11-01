"""Reproducible public CC-BY source acquisition; never grants training approval.

Only dog WAV members are extracted. Unknown identities remain unknown; filenames
are recording identifiers, not individual dogs. No archive extractall/pickle/code.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import struct
import tarfile
import urllib.request
import math
import zipfile
import xml.etree.ElementTree as ET

SOURCES = {
    'barkmeow': ('3563990', 'barkmeow_v0.2.tar.gz', 31661044,
                'd47826703a65cb5a2e11f55f1097202641e0d00bd337003168f3e2ce433b8ee4'),
    'dog-pain': ('15304081', 'Dog pain database_V2.xlsx', 251320,
                 '9a72e1532f5c8b0c8200f75135a11bcae9bb60cf7f25e1565483f0136329e82a'),
}


def audio_info(b):
    if len(b) < 44 or b[:4] != b'RIFF' or b[8:12] != b'WAVE' or struct.unpack_from('<I', b, 4)[0]+8 != len(b):
        raise ValueError('Invalid WAV container')
    offset = 12; fmt = None; raw = None
    while offset+8 <= len(b):
        tag, size = struct.unpack_from('<4sI', b, offset)
        chunk = b[offset+8:offset+8+size]
        if len(chunk) != size: raise ValueError('Truncated WAV chunk')
        if tag == b'fmt ':
            if fmt is not None or size < 16: raise ValueError('Invalid format chunk')
            fmt = struct.unpack_from('<HHIIHH', chunk)
        if tag == b'data':
            if raw is not None: raise ValueError('Duplicate data chunk')
            raw = chunk
        offset += 8+size+(size%2)
    if fmt is None or raw is None: raise ValueError('Missing audio chunks')
    encoding, channels, rate, byte_rate, align, bits = fmt
    if (encoding, bits) not in ((1, 16), (3, 32)) or channels not in (1, 2) or not 8000 <= rate <= 192000:
        raise ValueError('Unsupported audio format')
    if align != channels*bits//8 or byte_rate != rate*align or len(raw)%align:
        raise ValueError('Invalid audio alignment')
    frames = len(raw)//align
    if not .1 <= frames/rate <= 600: raise ValueError('Audio duration exceeded')
    if encoding == 3 and any(not math.isfinite(x[0]) for x in struct.iter_unpack('<f', raw)):
        raise ValueError('Nonfinite audio')
    return channels, rate, frames, 'float32' if encoding == 3 else 'pcm16'


def extract_dogs(archive, output):
    output = Path(output)
    if Path(archive).stat().st_size > 40_000_000:
        raise ValueError('Archive size exceeded')
    rows = []; payloads = []
    with tarfile.open(archive, 'r:gz') as stream:
        members = []
        total = 0
        for member in stream:
            total += member.size
            if len(members) >= 500 or total > 150_000_000:
                raise ValueError('Archive expanded size exceeded')
            path = PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts or '\\' in member.name or not (member.isfile() or member.isdir()):
                raise ValueError('Unsafe archive member')
            members.append(member)
        selected = [m for m in members if re.fullmatch(r'barkmeow/dog/dog_[0-9]+\.wav', m.name)]
        if not selected or len({m.name for m in selected}) != len(selected):
            raise ValueError('Missing or duplicate dog recordings')
        for member in sorted(selected, key=lambda m: m.name):
            if not member.isfile() or not 44 <= member.size <= 20_000_000:
                raise ValueError('Invalid audio member')
            b = stream.extractfile(member).read(member.size+1)
            if len(b) != member.size: raise ValueError('Truncated archive audio')
            channels, rate, frames, encoding = audio_info(b)
            name = PurePosixPath(member.name).name
            payloads.append((name, b))
            rows.append({'path': name, 'archive_member': member.name, 'sha256': hashlib.sha256(b).hexdigest(),
                         'bytes': len(b), 'duration_seconds': frames/rate, 'sample_rate': rate, 'channels': channels, 'encoding': encoding,
                         'source_label': 'dog', 'label_provenance': 'publisher directory; not independently reviewed',
                         'animal_id': None, 'household_id': None, 'device_id': None,
                         'source_recording_id': 'zenodo:3563990:'+name, 'training_approved': False})
    output.mkdir(parents=True, exist_ok=False)
    for name, b in payloads: (output/name).write_bytes(b)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--cached', help='Existing originals to verify instead of downloading')
    args = parser.parse_args(); root = Path(args.output); root.mkdir(parents=True, exist_ok=False)
    acquired = []
    for key, (record, filename, size, digest) in SOURCES.items():
        url = 'https://zenodo.org/records/'+record+'/files/'+urllib.parse.quote(filename)
        if args.cached:
            path = Path(args.cached)/filename
            if path.stat().st_size != size: raise ValueError('Source size mismatch')
            b = path.read_bytes()
        else:
            with urllib.request.urlopen(url, timeout=45) as response: b = response.read(size+1)
        if len(b) != size or hashlib.sha256(b).hexdigest() != digest: raise ValueError('Pinned source mismatch')
        (root/filename).write_bytes(b)
        acquired.append({'source': key, 'record': record, 'url': url, 'path': filename, 'bytes': size,
                         'sha256': digest, 'license': 'CC BY 4.0', 'training_approved': False})
    rows = extract_dogs(root/SOURCES['barkmeow'][1], root/'dog-audio')
    # Read only aggregate table structure; never publish clinical free text.
    ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(root/SOURCES['dog-pain'][1]) as z:
        if sum(x.file_size for x in z.infolist()) > 20_000_000: raise ValueError('Workbook too large')
        strings = [''.join(e.itertext()) for e in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', ns)]
        sheet_rows = ET.fromstring(z.read('xl/worksheets/sheet1.xml')).findall('m:sheetData/m:row', ns)
        ids = set(); observations = 0
        for row in sheet_rows[1:]:
            cells = {}
            for cell in row.findall('m:c', ns):
                column = ''.join(filter(str.isalpha, cell.attrib['r']))
                if column not in ('A', 'B'): continue
                value = cell.find('m:v', ns)
                if value is not None: cells[column] = strings[int(value.text)] if cell.get('t') == 's' else value.text
            if cells.get('A'): ids.add(cells['A'])
            if cells.get('B'): observations += 1
    clinical = {'worksheet_rows_including_header': len(sheet_rows), 'unique_nonempty_dog_ids': len(ids),
                'rows_with_observation_number': observations, 'raw_video_files_acquired': 0,
                'label_scope': 'clinical observations and questionnaires; not general emotion ground truth'}
    queue = [{'recording': r['source_recording_id'], 'sha256': r['sha256'], 'animal_id': None,
              'household_id': None, 'speaker_verified': False, 'events': [], 'reviewer': None,
              'training_approved': False} for r in rows]
    (root/'review-queue.json').write_text(json.dumps(queue, indent=2))
    report = {'sources': acquired, 'dog_recordings': rows, 'count': len(rows),
              'clinical_table_audit': clinical,
              'unique_content': len({r['sha256'] for r in rows}),
              'seconds': sum(r['duration_seconds'] for r in rows),
              'animal_disjoint_verified': False, 'training_performed': False,
              'limitations': ['Dog Pain file is a table, not the referenced videos',
                              'Archive is mixed species; only dog audio extracted',
                              'No emotion, speaker identity or onset/offset ground truth inferred',
                              'Raw content hashes do not rule out resampled or edited cross-dataset duplicates']}
    (root/'inventory.json').write_text(json.dumps(report, indent=2))
    (root/'ATTRIBUTION.txt').write_text('BarkMeowDB v0.2 — Dan Suh (Navercorp), DOI 10.5281/zenodo.3563990, CC BY 4.0.\n'
        'Dog Pain Database v2 — Annika Bremhorst, DOI 10.5281/zenodo.15304081, CC BY 4.0.\n'
        'Original files unchanged; dog WAV subset extracted. No diagnosis or training approval.\n')
    print(json.dumps({'dog_recordings': report['count'], 'unique_content': report['unique_content'],
                      'seconds': report['seconds'], 'training_performed': False}))


if __name__ == '__main__': main()
