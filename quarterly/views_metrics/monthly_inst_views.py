def view_count_monthly_payload(guid, before=None, after=None):
    if not (before and after):
        raise Exception('Must specify range')
    return {
        "query": {
            "bool" : {
                "must" : [
                    {"term" : { "item_public" : "true"}},
                    {"term" : { "item_guid": guid}},
                    {"range" : { "timestamp": {"gte": f'{after}-01', "lt": f'{before}-01'}}},
                    {"term" : {"action_labels": "view"}}
                ]
            }
        },
        "size": 0
    }

def get_monthly_total_views():
    from osf.metrics import CountedAuthUsage
    import csv
    import io
    filename = '/tmp/monthly_inst_views.csv'
    COL_HEADERS = ['institution', 'month', 'affiliated_views']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()
    jul = "2024-07"
    aug = "2024-08"
    sep = "2024-09"
    oct = "2024-10"
    targets = Institution.objects.all()
    for i in targets:
        target_nodes = i.nodes.filter(is_public=True, deleted__isnull=True)
        dates = [jul, aug, sep, oct]
        while len(dates) > 1:
            start = dates.pop(0)
            end = dates[0]
            output_dict = {}  # {guid : {COL_HEADERS:vals}}
            affl_count = 0
            for node in target_nodes:
                guid = node._id
                q = view_count_monthly_payload(guid, after=start, before=end)
                affl_count += CountedAuthUsage.search().update_from_dict(q).execute().to_dict()['hits']['total']
            writer.writerow({
                'institution': i.name,
                'month': start,
                'affiliated_views': affl_count
            })
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

# parameterized version
def get_monthly_total_views(year, start_month, end_month):
    from osf.metrics import CountedAuthUsage
    from datetime import date
    import csv
    import io

    filename = f'/tmp/monthly_inst_views.csv'
    COL_HEADERS = ['institution', 'month', 'affiliated_views']
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

            start = current.strftime('%Y-%m')
            before = next_month.strftime('%Y-%m')
            
            affl_count = 0

            for node in target_nodes:
                guid = node._id
                q = view_count_monthly_payload(guid, after=start, before=end)
                affl_count += CountedAuthUsage.search().update_from_dict(q).execute().to_dict()['hits']['total']
            
            writer.writerow({
                'institution': i.name,
                'month': start,
                'affiliated_views': affl_count
            })

            current = next_month

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

# example usage
get_monthly_total_views(2025, 7, 10)    # Q3 of 2025