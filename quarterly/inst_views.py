import csv
from datetime import date

from django.utils import timezone
import io
import pytz


# Payload Helpers --------------------------------------------------------------
def view_count_monthly_payload(guid, before=None, after=None):
    """
    Helper function to generate the Elasticsearch query payload for counting monthly views of a given item.
    """
    if not (before and after):
        raise Exception("Must specify range")
    return {
        "query": {
            "bool": {
                "must": [
                    {"term": {"item_public": "true"}},
                    {"term": {"item_guid": guid}},
                    {
                        "range": {
                            "timestamp": {"gte": f"{after}-01", "lt": f"{before}-01"}
                        }
                    },
                    {"term": {"action_labels": "view"}},
                ]
            }
        },
        "size": 0,
    }


def view_count_payload(guid, start, end):
    """
    Generate Elasticsearch query payload to count views for a specific item (identified by GUID) within a specified date range.
    """
    return {
        "query": {
            "bool": {
                "must": [
                    {"term": {"item_public": "true"}},
                    {"term": {"item_guid": guid}},
                    {
                        "range": {
                            "timestamp": {
                                "gte": f"{start.year}-{start.month:02}-01",
                                "lt": f"{end.year}-{end.month:02}-01",
                            }
                        }
                    },
                    {"term": {"action_labels": "view"}},
                ]
            }
        },
        "size": 0,
    }


# View Functions --------------------------------------------------------------
def get_quarterly_top_views(year, quarter):
    """
    Generate a report of the top 5 most viewed public nodes affiliated with each institution for a given quarter.

    Example usage:
    -----------------
    get_quarterly_top_views(2025, 3)  # Q3 of 2025

    1. year: The year for which the report is to be generated (e.g., 2025).
    2. quarter: The quarter of the year (1 to 4) for which the report is to be generated.
    """

    from osf.metrics import CountedAuthUsage
    from osf.models import Institution

    filename = "/tmp/top_inst_views.csv"
    COL_HEADERS = ["institution", "title", "guid", "views"]
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    # compute start and end months of the specified quarter
    start_month = (quarter - 1) * 3 + 1
    end_month = start_month + 3

    start = timezone.datetime(year, start_month, 1, tzinfo=pytz.utc)

    if end_month > 12:
        end = timezone.datetime(year + 1, end_month - 12, 1, tzinfo=pytz.utc)
    else:
        end = timezone.datetime(year, end_month, 1, tzinfo=pytz.utc)

    targets = Institution.objects.all()

    for i in targets:
        target_nodes = i.nodes.filter(
            is_public=True, created__gte=start, created__lt=end
        )
        output_dict = {}  # {guid : {COL_HEADERS:vals}}
        top_counts = []  # [(guid, count), ...]

        for node in target_nodes:
            guid = node._id
            q = view_count_payload(guid, start, end)
            count = (
                CountedAuthUsage.search()
                .update_from_dict(q)
                .execute()
                .to_dict()["hits"]["total"]
            )

            if count:
                if (
                    len(top_counts) < 5
                    or count > min(top_counts, key=lambda x: x[1])[1]
                ):
                    top_counts.append((guid, count))
                    output_dict[guid] = {
                        "institution": i.name,
                        "title": node.title,
                        "guid": guid,
                        "views": count,
                    }

                while len(top_counts) > 5:
                    min_item = min(top_counts, key=lambda x: x[1])
                    top_counts.remove(min_item)
                    output_dict.pop(min_item[0], None)

        for row in output_dict.values():
            writer.writerow(row)

    with open(filename, "w") as writeFile:
        writeFile.write(output.getvalue())


def get_monthly_total_views(year, start_month, end_month):
    """
    Get monthly total views for all institutions between start_month and end_month (inclusive of start_month, exclusive of end_month)

    Example usage:
    -----------------
    get_monthly_total_views(2025, 7, 10)  # Q3 of 2025

    1. year: The year for which the report is to be generated (e.g., 2025).
    2. start_month: The starting month (1-12) for the report (e.g., 7 for July).
    3. end_month: The ending month (1-12) for the report (e.g., 10 for October, exclusive).
    """
    from osf.metrics import CountedAuthUsage
    from osf.models import Institution

    filename = "/tmp/monthly_inst_views.csv"
    COL_HEADERS = ["institution", "month", "affiliated_views"]
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    targets = Institution.objects.all()

    for i in targets:
        target_nodes = i.nodes.filter(is_public=True, deleted__isnull=True)

        # generate YYYY-MM strings from start_month up to end_month
        current = date(year, start_month, 1)
        end = date(year, end_month, 1)

        while current < end:
            if current.month == 12:
                next_month = date(current.year + 1, 1, 1)
            else:
                next_month = date(current.year, current.month + 1, 1)

            start = current.strftime("%Y-%m")
            end = next_month.strftime("%Y-%m")

            affl_count = 0

            for node in target_nodes:
                guid = node._id
                q = view_count_monthly_payload(guid, after=start, before=end)
                affl_count += (
                    CountedAuthUsage.search()
                    .update_from_dict(q)
                    .execute()
                    .to_dict()["hits"]["total"]
                )

            writer.writerow(
                {"institution": i.name, "month": start, "affiliated_views": affl_count}
            )

            current = next_month

    with open(filename, "w") as writeFile:
        writeFile.write(output.getvalue())


# Wrapper function
def run_quarterly_views(year, quarter):
    print("Generating quarterly top views report...")
    get_quarterly_top_views(year, quarter)

    print("Generating monthly total views report...")
    start_month = (quarter - 1) * 3 + 1
    end_month = start_month + 3
    get_monthly_total_views(year, start_month, end_month)

    print("Quarterly views reports generation completed.")


if __name__ == "__main__":
    run_quarterly_views(2025, 4)
