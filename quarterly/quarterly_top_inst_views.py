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


# def get_quarterly_top_views():
#     from osf.metrics import CountedAuthUsage
#     import csv
#     import io
#     import pytz
#     filename = '/tmp/top_inst_views.csv'
#     COL_HEADERS = ['institution', 'title', 'guid', 'views']
#     output = io.StringIO()
#     writer = csv.DictWriter(output, COL_HEADERS)
#     writer.writeheader()
#     jul = timezone.datetime(2024,7,1,tzinfo=pytz.utc)
#     oct = timezone.datetime(2024,10,1,tzinfo=pytz.utc)
#     targets = Institution.objects.all()
#     for i in targets:
#         target_nodes = i.nodes.filter(is_public=True, created__gte=jul, created__lt=oct)
#         output_dict = {}  # {guid : {COL_HEADERS:vals}}
#         top_counts = [] # [(guid,count),...]
#         for node in target_nodes:
#             guid = node._id
#             q = view_count_payload(guid, jul, oct)
#             count = CountedAuthUsage.search().update_from_dict(q).execute().to_dict()['hits']['total']
#             if count:
#                 if len(top_counts) < 5 or count > min(top_counts, key=lambda x: x[1])[1]:
#                     top_counts.append((guid,count))
#                     output_dict[guid] = {
#                         'institution': i.name,
#                         'title': node.title,
#                         'guid': guid,
#                         'views': count
#                     }
#                 while len(top_counts) > 5:
#                     _min_item = min(top_counts, key=lambda x: x[1])
#                     output_dict.pop(_min_item[0])
#                     top_counts.pop(top_counts.index(_min_item))
#         for row in output_dict.values():
#             writer.writerow(row)
#     with open(filename, 'w') as writeFile:
#         writeFile.write(output.getvalue())


# parameterized version
def get_quarterly_top_views(year, quarter):
    """
    Generate a report of the top 5 most viewed public nodes affiliated with each institution for a given quarter.

    Example usage:
    -----------------
    get_quarterly_top_views(2025, 3)  # Q3 of 2025

    1. year: The year for which the report is to be generated (e.g., 2025).
    2. quarter: The quarter of the year (1 to 4) for which the report is to be generated.
    """

    import csv
    import io
    import pytz

    from django.utils import timezone
    from osf.metrics import CountedAuthUsage, Institution

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
