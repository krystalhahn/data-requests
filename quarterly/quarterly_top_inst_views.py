def view_count_payload(guid, start, end):
    return {
        "query": {
            "bool" : {
                "must" : [
                    {"term" : { "item_public" : "true"}},
                    {"term" : { "item_guid": guid}},
                    {"range" : { "timestamp": {"gte": f"{start.year}-{start.month:02}-01", "lt": f"{end.year}-{end.month:02}-01"}}},
                    {"term" : {"action_labels": "view"}}
                ]
            }
        },
        "size": 0
    }

def get_quarterly_top_views():
    from osf.metrics import CountedAuthUsage
    import csv
    import io
    import pytz
    filename = '/tmp/top_inst_views.csv'
    COL_HEADERS = ['institution', 'title', 'guid', 'views']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()
    jul = timezone.datetime(2024,7,1,tzinfo=pytz.utc)
    oct = timezone.datetime(2024,10,1,tzinfo=pytz.utc)
    targets = Institution.objects.all()
    for i in targets:
        target_nodes = i.nodes.filter(is_public=True, created__gte=jul, created__lt=oct)
        output_dict = {}  # {guid : {COL_HEADERS:vals}}
        top_counts = [] # [(guid,count),...]
        for node in target_nodes:
            guid = node._id
            q = view_count_payload(guid, jul, oct)
            count = CountedAuthUsage.search().update_from_dict(q).execute().to_dict()['hits']['total']
            if count:
                if len(top_counts) < 5 or count > min(top_counts, key=lambda x: x[1])[1]:
                    top_counts.append((guid,count))
                    output_dict[guid] = {
                        'institution': i.name,
                        'title': node.title,
                        'guid': guid,
                        'views': count
                    }
                while len(top_counts) > 5:
                    _min_item = min(top_counts, key=lambda x: x[1])
                    output_dict.pop(_min_item[0])
                    top_counts.pop(top_counts.index(_min_item))
        for row in output_dict.values():
            writer.writerow(row)
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())