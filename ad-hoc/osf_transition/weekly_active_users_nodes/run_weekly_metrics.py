import csv
from functools import wraps
import sys
import time

from django.db.models import OuterRef, Q, Subquery, F, Func, Max, Value
import io
from tqdm import tqdm
import datetime
import pytz
from django.utils import timezone


def timeit(func):
    """Decorator to measure the execution time of a function (in minutes)."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        elapsed = end - start
        print(f"Function '{func.__name__}' executed in {elapsed / 60:.2f} mins")
        return result

    return wrapper


@timeit
def get_weekly_active_users(backup_cutoff):

    filename = f'/tmp/weekly_active_users.csv'
    fieldnames = ['login_count', 'action_count_from_user', 'action_count_from_log']
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()

    end_y, end_m, end_d = map(int, backup_cutoff.split("-"))
    end = timezone.datetime(end_y, end_m, end_d, tzinfo=pytz.utc)
    start = end - datetime.timedelta(days=7)

    print("Counting logins...")
    t0 = time.time()
    login_count = OSFUser.objects.filter(date_last_login__gte=start, date_last_login__lt=end).count()
    print(f"Login count: {login_count} (took {time.time() - t0:.2f}s)")

    print("Counting users with actions from NodeLog...")
    t0 = time.time()
    # don't count when there is no user (system)
    action_count_from_log = NodeLog.objects.filter(created__gte=start, created__lt=end, user__isnull=False).values('user').distinct().count()
    print(f"Action count from NodeLog: {action_count_from_log} (took {time.time() - t0:.2f}s)")

    print("Counting users with actions from OSFUser...")
    t0 = time.time()
    action_count_from_user = OSFUser.objects.filter(logs__created__gte=start, logs__created__lt=end).distinct().count()
    print(f"Action count from OSFUser: {action_count_from_user} (took {time.time() - t0:.2f}s)")

    writer.writerow({
        'login_count': login_count,
        'action_count_from_user': action_count_from_user,
        'action_count_from_log': action_count_from_log
    })

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")


@timeit
def get_weekly_nodes_created(backup_cutoff, source):

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

@timeit
def get_weekly_nodes_deleted(backup_cutoff, source):

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

@timeit
def get_weekly_nodes_made_public(backup_cutoff, exclude_later_made_private):

    filename = f'/tmp/weekly_nodes_made_public_from_logs.csv'
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


@timeit
def main(backup_cutoff):
    print("Starting weekly data extraction...\n")

    print("Count active users...")
    get_weekly_active_users(backup_cutoff)

    print("\nExtract nodes created from field...")
    get_weekly_nodes_created(backup_cutoff, source="from_field")
    
    print("\nExtract nodes created from logs...")
    get_weekly_nodes_created(backup_cutoff, source="from_logs")

    print("\nExtract nodes deleted from field...")
    get_weekly_nodes_deleted(backup_cutoff, source="from_field")

    print("\nExtract nodes deleted from logs...")
    get_weekly_nodes_deleted(backup_cutoff, source="from_logs")

    print("\nExtract all nodes made public...")
    get_weekly_nodes_made_public(backup_cutoff, exclude_later_made_private=False)

    print("\nExtract nodes made public that were not made private later...")
    get_weekly_nodes_made_public(backup_cutoff, exclude_later_made_private=True)

    print("\nWeekly data extraction completed.")


if __name__ == "__main__":
    try:
        main(backup_cutoff)
    except KeyboardInterrupt:
        print("Interrupted!")
