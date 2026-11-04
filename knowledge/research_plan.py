"""Prepare bounded domestic/global dog-video discovery batches; no external calls."""
import argparse
import hashlib
import json
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlencode

from pydantic import Field, field_validator
from knowledge.models import Config, StrictModel


class Source(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    language: Literal['ko', 'en']
    queries: list[Annotated[str, Field(min_length=1, max_length=150)]] = Field(min_length=1, max_length=2)
    verification: Literal['search_target_not_verified']

    @field_validator('name', 'queries')
    @classmethod
    def meaningful(cls, value):
        values = value if isinstance(value, list) else [value]
        if any(not text.strip() or text != text.strip() for text in values):
            raise ValueError('Nonempty trimmed research text required')
        return value


class Catalog(StrictModel):
    schema_version: Literal[1]
    sources: list[Source] = Field(min_length=1, max_length=20)


def prepare(document):
    catalog = Catalog.model_validate(document)
    names = [row.name.casefold() for row in catalog.sources]
    if len(set(names)) != len(names):raise ValueError('Duplicate research source')
    searches = []; configs = []
    for language in ('ko', 'en'):
        queries = []
        for source in catalog.sources:
            if source.language != language:continue
            for query in source.queries:
                if query in queries:raise ValueError('Duplicate discovery query')
                queries.append(query)
                searches.append({'source_name': source.name, 'language': language, 'query': query,
                    'search_url': 'https://www.youtube.com/results?' + urlencode({'search_query': query}),
                    'verification': source.verification, 'video_found': False, 'training_ready': False})
        for offset in range(0, len(queries), 4):
            # Discovery configuration never grants channel permissions or enables paid analysis.
            config = Config.model_validate({'queries': queries[offset:offset+4], 'policies': {},
                'daily_requests': 20, 'max_videos': 5, 'notebook': None})
            configs.append((f'knowledge-{language}-{offset//4+1}.json', config.model_dump()))
    return configs, {'status': 'search_plan_only', 'external_calls': 0,
        'sources': len(catalog.sources), 'searches': searches,
        'notice': 'Names are search targets, not verified official channels or analyzed videos.'}


def select_batch(db, config, document):
    """Rotate queries while preserving explicit operator permissions and budgets."""
    configs, _ = prepare(document)
    key = 'research-next:' + hashlib.sha256(json.dumps(document, sort_keys=True).encode()).hexdigest()
    row = db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
    index = int(row['value']) % len(configs) if row else 0
    name, batch = configs[index]
    merged = config.model_dump();merged['queries'] = batch['queries']
    selected = Config.model_validate(merged)
    return selected, {'name': name, 'index': index, 'next': (index+1) % len(configs), 'key': key}


def advance_batch(db, batch, charged_requests):
    if charged_requests <= 0:return  # Exhausted quota must not skip unsearched batches.
    with db:
        db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (batch['key'], str(batch['next'])))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, default=Path('config/dog-video-sources.json'))
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.catalog.stat().st_size > 64000:raise ValueError('Catalog too large')
        configs, report = prepare(json.loads(args.catalog.read_text()))
        args.output_dir.mkdir(parents=True, exist_ok=False)
        for name, config in configs:
            (args.output_dir/name).write_text(json.dumps(config, ensure_ascii=False, indent=2)+'\n')
        (args.output_dir/'search-plan.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    except (OSError, ValueError):
        parser.exit(2, 'Research plan blocked: check catalog and a fresh output directory.\n')
    print(f'Prepared {report["sources"]} search targets, {len(report["searches"])} queries and {len(configs)} configurations. No videos fetched or models trained.')


if __name__ == '__main__':main()
