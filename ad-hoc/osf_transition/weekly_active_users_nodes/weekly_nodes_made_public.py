def get_weekly_nodes_made_public(backup_cutoff):
    import io
    import csv
    from tqdm import tqdm
    import datetime
    import pytz
    from django.utils import timezone

    filename = '/tmp/weekly_nodes_made_public.csv'

    fieldnames = [
        'node_id',
        'abstractnode_type',
        'date_made_public_log'
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()

    end_y, end_m, end_d = map(int, backup_cutoff.split("-"))
    end = timezone.datetime(end_y, end_m, end_d, tzinfo=pytz.utc)
    start = end - datetime.timedelta(days=7)

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
        })

    with open(filename, "w") as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")