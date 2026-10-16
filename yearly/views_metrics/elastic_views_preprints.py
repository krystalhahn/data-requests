"""
given a time range, build a CSV of monthly view counts for all preprints
"""

import argparse
import collections.abc as _abc
import csv
import dataclasses
import itertools
import os

import requests


_OSF_TOKEN = os.environ["OSF_TOKEN"]
# _SEARCH_URL = 'https://api.staging.osf.io/_/metrics/raw-osfmetrics_es8/*itemusagereport*/_search'
_SEARCH_URL = "https://api.osf.io/_/metrics/raw-osfmetrics_es8/*itemusagereport*/_search"
_SORT = ('item_iri', 'cycle_coverage')
_CHUNK_SIZE = 1000
_PAGE_SIZE = _CHUNK_SIZE


@dataclasses.dataclass
class _UsageRow:
    osfid: str
    osfprovider: str
    yearmonth: str
    view_count: int
    cumulative_view_count: int


def _get_argparser():
    _argparser = argparse.ArgumentParser()
    _argparser.add_argument("--out-csv", "-o", required=True)
    _argparser.add_argument("--from-cycle", required=True)
    _argparser.add_argument("--thru-cycle", required=True)
    _argparser.add_argument("--after-osfid")
    _argparser.add_argument("--after-cycle")
    return _argparser


def _do_search(json_body: dict):
    # print(json_body)
    
    _resp = requests.post(
        _SEARCH_URL,
        headers={
            "Authorization": f"Bearer {_OSF_TOKEN}",
            "Accept": "application/json",
        },
        json=json_body,
    )
    if not _resp.ok:
        breakpoint()
    _resp.raise_for_status()
    return _resp.json()


def _each_osfid_batch(osfid_csv_reader, osfid_column: str):
    for _row_batch in itertools.batched(osfid_csv_reader, _CHUNK_SIZE):
        _osfid_batch = [_row[osfid_column] for _row in _row_batch]
        _remainder_fields = {
            _row[osfid_column]: {
                _k: _v for _k, _v in _row.items() if _k != osfid_column
            }
            for _row in _row_batch
        }
        yield _osfid_batch, _remainder_fields


def _field_values(out_row: _UsageRow) -> dict:
    return dataclasses.asdict(out_row)


def _each_doc(base_query: dict, search_after):
    _search_body = {
        'query': base_query,
        'size': _PAGE_SIZE,
        'sort': _SORT,
    }
    if search_after:
        _search_body['search_after'] = search_after

    _total = 0

    while True:
        _resp = _do_search(_search_body)
        _hits = _resp['hits']['hits']

        if _hits:
            for _hit in _hits:
                yield _hit['_source']
                _total += 1

                if _total % 100000 == 0:
                    print(f'Processed {_total} documents...')

            _search_after = _hits[-1]['sort']
            _search_body['search_after'] = _search_after
        else:
            print(f'Finished. Total documents: {_total}')
            return


def _each_usage_row(
    from_cycle: str,
    thru_cycle: str,
    after_osfid: str | None,
    after_cycle: str | None,
) -> _abc.Iterator[_UsageRow]:
    _query = {
        'bool': {
            'filter': [
                {'term': {'item_types': 'Preprint'}},
                {'range': {'cycle_coverage': {
                    'gte': from_cycle,
                    'lte': thru_cycle,
                }}},
            ],
        },
    }
    _search_after = None
    if after_osfid or after_cycle:
        assert after_osfid and after_cycle
        _search_after = [f'https://osf.io/{after_osfid}', after_cycle]
    for _doc in _each_doc(_query, _search_after):
        yield _UsageRow(
            osfid=_doc["item_osfids"][0],
            osfprovider=";".join(_doc["provider_ids"]),
            yearmonth=_yearmonth_from_cycle_coverage(_doc["cycle_coverage"]),
            view_count=_doc["view_count"],
            cumulative_view_count=_doc["cumulative_view_count"],
        )


def _out_fieldnames() -> list[str]:
    return [_field.name for _field in dataclasses.fields(_UsageRow)]


def _yearmonth_from_cycle_coverage(cycle_coverage: str):
    """convert from "YYYY.M" to "YYYY-MM" format"""
    (_year, _month) = map(int, cycle_coverage.split("."))
    return f"{_year}-{_month:0>2}"


def _main(out_csv: str, from_cycle: str, thru_cycle: str, after_osfid: str | None = None, after_cycle: str | None = None):
    _out_mode = 'x'
    if after_osfid or after_cycle:
        assert after_osfid and after_cycle
        _out_mode = 'a'
    with open(out_csv, _out_mode) as _out_file:
        _writer = csv.DictWriter(
            _out_file, _out_fieldnames()
        )
        if _out_mode != 'a':
            _writer.writeheader()
        for _row in _each_usage_row(from_cycle, thru_cycle, after_osfid, after_cycle):
            _writer.writerow(_field_values(_row))


if __name__ == "__main__":
    _kwargs = vars(_get_argparser().parse_args())
    _main(**_kwargs)
