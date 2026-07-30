def get_weekly_nodes_deleted(backup_cutoff, source):
    import io
    import csv
    from tqdm import tqdm
    import datetime
    import pytz
    from django.utils import timezone
    import time

    filename = f'/tmp/weekly_nodes_deleted_{source}.csv'
    fieldnames = ['node_id', 'abstractnode_type', 'date_deleted', 'has_node_removed_log', 'date_node_removed_log', 'has_project_deleted_log', 'date_project_deleted_log']
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()

    end_y, end_m, end_d = map(int, backup_cutoff.split("-"))
    end = timezone.datetime(end_y, end_m, end_d, tzinfo=pytz.utc)
    start = end - datetime.timedelta(days=7)

    if source == "from_field":
        nodes = Node.objects.filter(deleted__gte=start, deleted__lt=end)

        for n in tqdm(nodes, total=nodes.count()):
            node_removed_log = n.logs.filter(action="node_removed").order_by('created').first()
            project_deleted_log = n.logs.filter(action="project_deleted").order_by('created').first()

            writer.writerow({
                'node_id': n._id,
                'abstractnode_type': AbstractNode.objects.get(guids___id=n._id).type,
                'date_deleted': n.deleted,
                'has_node_removed_log': node_removed_log is not None,
                'date_node_removed_log': node_removed_log.created if node_removed_log else None,
                'has_project_deleted_log': project_deleted_log is not None,
                'date_project_deleted_log': project_deleted_log.created if project_deleted_log else None
            })
    elif source == "from_logs":
        deleted_actions = ["node_removed", "project_deleted"]

        logs = NodeLog.objects.filter(
            action__in=deleted_actions, created__gte=start, created__lt=end
        ).select_related('node').order_by('node_id', 'created')

        seen_nodes = set()
        for log in tqdm(logs, total=logs.count()):
            if log.node_id in seen_nodes:
                continue
            seen_nodes.add(log.node_id)

            writer.writerow({
                'node_id': log.node._id if log.node else None,
                'abstractnode_type': AbstractNode.objects.get(guids___id=log.node._id).type if log.node else None,
                'date_deleted': log.node.deleted,
                'has_node_removed_log': log.action == "node_removed",
                'date_node_removed_log': log.created if log.action == "node_removed" else None,
                'has_project_deleted_log': log.action == "project_deleted",
                'date_project_deleted_log': log.created if log.action == "project_deleted" else None
            })

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")