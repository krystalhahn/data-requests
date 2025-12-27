# must be run on production server, not included in Postgres data dumps
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

def get_project_views(project_id):
    from osf.metrics import CountedAuthUsage
    import csv
    import io
    import datetime
    filename = '/tmp/project_views.csv'
    COL_HEADERS = ['project_name', 'component_name', 'component_guid', 'component_type', 'component_created', 'component_views']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    start = "2022-02"
    end = datetime.datetime.today().strftime('%Y-%m')
 
    project = Node.objects.get(guids___id=project_id)

    for descendant in project.descendants.all():
        
        view_count = 0
        q = view_count_payload(descendant._id, start=start, end=end)
        view_count = CountedAuthUsage.search().update_from_dict(q).execute().to_dict()['hits']['total']

        writer.writerow({
            'project_name': project.title,
            'component_name': descendant.title,
            'component_guid': descendant._id,
            'component_type': descendant.type,
            'component_created': descendant.created,
            'component_views': view_count
        })

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())