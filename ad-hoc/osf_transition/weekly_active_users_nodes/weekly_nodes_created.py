def get_weekly_nodes_created(backup_cutoff, source):
    import io
    import csv
    from tqdm import tqdm
    import datetime
    import pytz
    from django.utils import timezone
    import time

    filename = f'/tmp/weekly_nodes_created_{source}.csv'
    fieldnames = ['node_id', 'abstractnode_type', 'date_created', 
                  'has_node_created_log', 'date_node_created_log', 
                  'has_project_created_log', 'date_project_created_log',
                  'has_project_created_from_draft_reg_log', 'date_project_created_from_draft_reg_log',
                  'has_created_from_log', 'date_created_from_log']
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()

    end_y, end_m, end_d = map(int, backup_cutoff.split("-"))
    end = timezone.datetime(end_y, end_m, end_d, tzinfo=pytz.utc)
    start = end - datetime.timedelta(days=7)

    if source == "from_field":
        nodes = Node.objects.filter(created__gte=start, created__lt=end)

        for n in tqdm(nodes, total=nodes.count()):
            node_created_log = n.logs.filter(action="node_created").order_by('created').first()
            project_created_log = n.logs.filter(action="project_created").order_by('created').first()
            project_created_from_draft_reg_log = n.logs.filter(action="project_created_from_draft_reg").order_by('created').first()
            created_from_log = n.logs.filter(action="created_from").order_by('created').first()

            writer.writerow({
                'node_id': n._id,
                'abstractnode_type': AbstractNode.objects.get(guids___id=n._id).type,
                'date_created': n.created,
                'has_node_created_log': node_created_log is not None,
                'date_node_created_log': node_created_log.created if node_created_log else None,
                'has_project_created_log': project_created_log is not None,
                'date_project_created_log': project_created_log.created if project_created_log else None,
                'has_project_created_from_draft_reg_log': project_created_from_draft_reg_log is not None,
                'date_project_created_from_draft_reg_log': project_created_from_draft_reg_log.created if project_created_from_draft_reg_log else None,
                'has_created_from_log': created_from_log is not None,
                'date_created_from_log': created_from_log.created if created_from_log else None
            })
    elif source == "from_logs":
        created_actions = ["node_created", "project_created", "project_created_from_draft_reg", "created_from"]

        logs = NodeLog.objects.filter(
            action__in=created_actions, created__gte=start, created__lt=end
        ).select_related('node').order_by('node_id', 'created')

        seen_nodes = set()
        for log in tqdm(logs, total=logs.count()):
            if log.node_id in seen_nodes:
                continue
            seen_nodes.add(log.node_id)

            writer.writerow({
                'node_id': log.node._id if log.node else None,
                'abstractnode_type': AbstractNode.objects.get(guids___id=log.node._id).type if log.node else None,
                'date_created': log.node.created if log.node else None,
                'has_node_created_log': log.action == "node_created", 
                'date_node_created_log': log.created if log.action == "node_created" else None,
                'has_project_created_log': log.action == "project_created",
                'date_project_created_log': log.created if log.action == "project_created" else None,
                'has_project_created_from_draft_reg_log': log.action == "project_created_from_draft_reg",
                'date_project_created_from_draft_reg_log': log.created if log.action == "project_created_from_draft_reg" else None,
                'has_created_from_log': log.action == "created_from",
                'date_created_from_log': log.created if log.action == "created_from" else None
            })

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")