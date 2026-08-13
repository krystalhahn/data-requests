def get_weekly_nodes_made_public(backup_cutoff, exclude_later_made_private):
    import io
    import csv
    from tqdm import tqdm
    import datetime
    import pytz
    from django.utils import timezone

    fieldnames = [
        'node_id',
        'abstractnode_type',
        'date_made_public_log',
        'has_made_public_log'
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()

    end_y, end_m, end_d = map(int, backup_cutoff.split("-"))
    end = timezone.datetime(end_y, end_m, end_d, tzinfo=pytz.utc)
    start = end - datetime.timedelta(days=7)

    # specifically  "made_public" log is not followed by a "made_private" log
    if exclude_later_made_private:
        filename = f'/tmp/weekly_nodes_made_public_from_logs.csv'

        actions = ["made_public", "made_private"]

        logs = (
            NodeLog.objects.filter(action__in=actions, created__gte=start, created__lt=end)
            .select_related("node")
            .order_by("node_id", "created")
        )

        node_data = {}

        for log in tqdm(logs, total=logs.count()):
            if log.node is None:
                continue

            data = node_data.setdefault(log.node_id, {
                "node": log.node,
                "has_made_public_log": False,
                "date_made_public_log": None,
            })

            if log.action == "made_public":
                # latest state becomes public
                data["has_made_public_log"] = True
                data["date_made_public_log"] = log.created

            elif log.action == "made_private":
                # latest state becomes private
                data["has_made_public_log"] = False
                data["date_made_public_log"] = None

        for data in node_data.values():
            if not data["has_made_public_log"]:
                continue

            node = data["node"]

            writer.writerow({
                "node_id": node._id,
                "abstractnode_type": AbstractNode.objects.get(
                    guids___id=node._id
                ).type,
                "date_made_public_log": data["date_made_public_log"],
                "has_made_public_log": True,
            })

    # regardless of whether there was a "made_private" log afterwards
    else:
        filename = f'/tmp/weekly_nodes_made_public_all.csv'

        logs = (
        NodeLog.objects.filter(action="made_public", created__gte=start, created__lt=end)
        .select_related("node")
        .order_by("node_id", "created")
        )

        seen_nodes = set()

        for log in tqdm(logs, total=logs.count()):
            if log.node is None or log.node_id in seen_nodes:
                continue

            seen_nodes.add(log.node_id)

            writer.writerow({
                "node_id": log.node._id,
                "abstractnode_type": AbstractNode.objects.get(
                    guids___id=log.node._id
                ).type,
                "date_made_public_log": log.created,
                "has_made_public_log": True
            })


        with open(filename, "w") as writeFile:
            writeFile.write(output.getvalue())

        print(f"Output written to {filename}")
