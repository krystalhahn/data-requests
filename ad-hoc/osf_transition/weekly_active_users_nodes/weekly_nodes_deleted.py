def get_weekly_nodes_deleted(backup_cutoff, source):
    import io
    import csv
    from tqdm import tqdm
    import datetime
    import pytz
    from django.utils import timezone
    import time

    filename = f'/tmp/weekly_nodes_deleted_{source}.csv'
    fieldnames = ['node_id', 'abstractnode_type', 'date_deleted', 
                  'has_node_removed_log', 'date_node_removed_log', 
                  'has_project_deleted_log', 'date_project_deleted_log',
                  'has_confirm_spam_log', 'date_confirm_spam_log']
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
            confirm_spam_log = n.logs.filter(action="confirm_spam").order_by('created').first()

            writer.writerow({
                'node_id': n._id,
                'abstractnode_type': AbstractNode.objects.get(guids___id=n._id).type,
                'date_deleted': n.deleted,
                'has_node_removed_log': node_removed_log is not None,
                'date_node_removed_log': node_removed_log.created if node_removed_log else None,
                'has_project_deleted_log': project_deleted_log is not None,
                'date_project_deleted_log': project_deleted_log.created if project_deleted_log else None,
                'has_confirm_spam_log': confirm_spam_log is not None,
                'date_confirm_spam_log': confirm_spam_log.created if confirm_spam_log else None
            })
    elif source == "from_logs":
        actions = [
            "node_removed",
            "project_deleted",
            "confirm_spam",
            "confirm_ham",
        ]

        logs = (
            NodeLog.objects.filter(
                action__in=actions,
                created__gte=start,
                created__lt=end,
            )
            .select_related("node")
            .order_by("node_id", "created")
        )

        node_data = {}

        for log in tqdm(logs, total=logs.count()):
            if log.node is None:
                continue

            data = node_data.setdefault(log.node_id, {
                "node": log.node,
                "has_node_removed_log": False,
                "date_node_removed_log": None,
                "has_project_deleted_log": False,
                "date_project_deleted_log": None,
                "has_confirm_spam_log": False,
                "date_confirm_spam_log": None,
            })

            if log.action == "node_removed":
                data["has_node_removed_log"] = True
                if data["date_node_removed_log"] is None:
                    data["date_node_removed_log"] = log.created

            elif log.action == "project_deleted":
                data["has_project_deleted_log"] = True
                if data["date_project_deleted_log"] is None:
                    data["date_project_deleted_log"] = log.created

            elif log.action == "confirm_spam":
                # latest state is spam
                data["has_confirm_spam_log"] = True
                data["date_confirm_spam_log"] = log.created

            elif log.action == "confirm_ham":
                # latest state is ham, so clear spam state
                data["has_confirm_spam_log"] = False
                data["date_confirm_spam_log"] = None

        for data in node_data.values():
            node = data["node"]

            # only write nodes that actually had a relevant log
            # or ended the week in a confirmed spam state
            if not (
                data["has_node_removed_log"]
                or data["has_project_deleted_log"]
                or data["has_confirm_spam_log"]
            ):
                continue

            writer.writerow({
                "node_id": node._id,
                "abstractnode_type": AbstractNode.objects.get(guids___id=node._id).type,
                "date_deleted": node.deleted,
                "has_node_removed_log": data["has_node_removed_log"],
                "date_node_removed_log": data["date_node_removed_log"],
                "has_project_deleted_log": data["has_project_deleted_log"],
                "date_project_deleted_log": data["date_project_deleted_log"],
                "has_confirm_spam_log": data["has_confirm_spam_log"],
                "date_confirm_spam_log": data["date_confirm_spam_log"],
            })

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")