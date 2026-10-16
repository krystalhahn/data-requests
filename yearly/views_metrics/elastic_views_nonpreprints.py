"""
given a CSV file containing osfids and a time range, build a CSV of monthly view counts
"""

import argparse
import collections.abc as _abc
import csv
import dataclasses
import itertools

import requests


_OSF_COOKIE = "..."  # add your cookie
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
    _argparser.add_argument("--osfid-csv", "-i", required=True)
    _argparser.add_argument("--osfid-column", "-c", default="guid")
    _argparser.add_argument("--out-csv", "-o", required=True)
    _argparser.add_argument("--from-cycle", required=True)
    _argparser.add_argument("--thru-cycle", required=True)
    return _argparser


def _do_search(json_body: dict):
    _resp = requests.post(
        _SEARCH_URL,
        headers={
            "Cookie": _OSF_COOKIE,
            'Accept': "application/json",
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


def _field_values(out_row: _UsageRow, remainder_fields) -> dict:
    return {
        **remainder_fields.get(out_row.osfid, {}),
        **dataclasses.asdict(out_row),
    }


def _each_doc(base_query: dict):
    _search_body = {
        'query': base_query,
        'size': _PAGE_SIZE,
        'sort': _SORT,
    }
    while ...:
        _resp = _do_search(_search_body)
        _hits = _resp['hits']['hits']
        if _hits:
            for _hit in _hits:
                yield _hit['_source']
            _search_body['search_after'] = _hits[-1]['sort']
        else:
            return


def _each_usage_row(
    osfid_batch: _abc.Iterable[str],
    from_cycle: str,
    thru_cycle: str,
) -> _abc.Iterator[_UsageRow]:
    _query = {
        'bool': {
            'filter': [
                {'terms': {'item_osfids': osfid_batch}},
                {'range': {'cycle_coverage': {
                    'gte': from_cycle,
                    'lte': thru_cycle,
                }}},
            ],
        },
    }
    for _doc in _each_doc(_query):
        yield _UsageRow(
            osfid=_doc["item_osfids"][0],
            osfprovider=";".join(_doc["provider_ids"]),
            yearmonth=_yearmonth_from_cycle_coverage(_doc["cycle_coverage"]),
            view_count=_doc["view_count"],
            cumulative_view_count=_doc["cumulative_view_count"],
        )


def _out_fieldnames(in_fieldnames, osfid_column) -> list[str]:
    _field_names = [_name for _name in in_fieldnames if _name != osfid_column]
    _field_names.extend(_field.name for _field in dataclasses.fields(_UsageRow))
    return _field_names


def _yearmonth_from_cycle_coverage(cycle_coverage: str):
    """convert from "YYYY.M" to "YYYY-MM" format"""
    (_year, _month) = map(int, cycle_coverage.split("."))
    return f"{_year}-{_month:0>2}"


def _main(osfid_csv: str, osfid_column: str, out_csv: str, from_cycle: str, thru_cycle: str):
    with open(osfid_csv) as _in_file:
        _reader = csv.DictReader(_in_file)
        with open(out_csv, "x") as _out_file:
            _writer = csv.DictWriter(
                _out_file, _out_fieldnames(_reader.fieldnames, osfid_column)
            )
            _writer.writeheader()
            for _osfid_batch, _remainder_fields in _each_osfid_batch(
                _reader, osfid_column
            ):
                for _row in _each_usage_row(_osfid_batch, from_cycle, thru_cycle):
                    _writer.writerow(_field_values(_row, _remainder_fields))


if __name__ == "__main__":
    _kwargs = vars(_get_argparser().parse_args())
    _main(**_kwargs)
