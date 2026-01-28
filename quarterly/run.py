import csv
from functools import wraps
import logging
import time

from django.utils import timezone
import io
import pytz
from tqdm import tqdm


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
def get_domain_metrics(ds=None):
    from osf.models import OSFUser, Email, Node, Registration, Preprint

    filename = "/tmp/all_domain_metrics.csv"
    COL_HEADERS = [
        "domain",
        "total_users",
        "orcid_total",
        "annual_login",
        "annual_actions",
        "total_nodes",
        "public_nodes",
        "total_regs",
        "public_regs",
        "total_preprints",
        "published_preprints",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    if not ds:
        # unames = OSFUser.objects.filter(is_active=True).exclude(spam_status=2).values_list('username', flat=True)
        unames = (
            Email.objects.filter(user__is_active=True)
            .exclude(user__spam_status=2)
            .values_list("address", flat=True)
        )
        ds = set([u.split("@")[1] for u in unames if "@" in u])

    target_date = timezone.now() - timezone.timedelta(days=365)

    pbar = tqdm(total=len(ds))

    for d in ds:
        users = OSFUser.objects.filter(
            is_active=True,
            id__in=Email.objects.filter(address__endswith=f"@{d}")
            .values_list("user_id", flat=True)
            .distinct(),
        ).exclude(spam_status=2)

        ns = (
            Node.objects.filter(
                _contributors__in=users, deleted__isnull=True, is_deleted=False
            )
            .exclude(spam_status__in=[1, 2])
            .distinct()
        )
        rs = (
            Registration.objects.filter(
                _contributors__in=users, deleted__isnull=True, is_deleted=False
            )
            .exclude(spam_status__in=[1, 2])
            .distinct()
        )
        ps = (
            Preprint.objects.filter(_contributors__in=users, deleted__isnull=True)
            .exclude(machine_state="initial")
            .exclude(spam_status__in=[1, 2])
            .distinct()
        )

        domain_metrics = {
            "domain": d,
            "total_users": users.count(),
            "orcid_total": 0,
            "annual_login": users.filter(date_last_login__gte=target_date).count(),
            "annual_actions": 0,
            "total_nodes": ns.count(),
            "public_nodes": ns.filter(is_public=True).count(),
            "total_regs": rs.count(),
            "public_regs": rs.filter(is_public=True)
            .exclude(moderation_state="withdrawn")
            .count(),
            "total_preprints": ps.count(),
            "published_preprints": ps.filter(is_public=True, is_published=True)
            .exclude(machine_state="withdrawn")
            .count(),
        }

        for u in users:
            if "VERIFIED" in list(u.external_identity.get("ORCID", {}).values()):
                domain_metrics["orcid_total"] += 1
            if (
                u.logs.filter(created__gte=target_date).exists()
                or u.preprint_logs.filter(created__gte=target_date).exists()
            ):
                domain_metrics["annual_actions"] += 1

        writer.writerow(domain_metrics)
        pbar.update()

    pbar.close()

    with open(filename, "w") as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")


@timeit
def get_quarterly_active_users(year, quarter):
    """
    Generate a report of active users affiliated with institutions for a given quarter.

    Exanmple usage:
    -----------------
    get_quarterly_active_users(2023, 2)
    -----------------------------------
    1. year: The year for which the report is to be generated (e.g., 2023).
    2. quarter: The quarter of the year (1 to 4) for which the report is to be generated.
    """

    from osf.models import Institution, OSFUser

    filename = "/tmp/inst_active_users.csv"
    COL_HEADERS = [
        "institution",
        "user",
        "guid",
        "email",
        "public_projects",
        "public_registrations",
        "quarterly_actions",
        "date_last_log",
        "department",
        "created",
        "date_last_login",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    # compute start and end datetimes of the specified quarter
    quarter_months = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}
    start_month, end_month = quarter_months[quarter]
    start_dt = timezone.datetime(year, start_month, 1, tzinfo=pytz.utc)
    if end_month == 12:
        end_dt = timezone.datetime(year + 1, 1, 1, tzinfo=pytz.utc)
    else:
        end_dt = timezone.datetime(year, end_month + 1, 1, tzinfo=pytz.utc)

    targets = Institution.objects.all()

    pbar = tqdm(total=targets.count())

    for i in targets:
        users = (
            OSFUser.objects.filter(
                institutionaffiliation__institution__id=i.id, is_active=True
            )
            .exclude(spam_status=2)
            .distinct()
        )

        for u in users:
            last_log = getattr(u.logs.order_by("-created").first(), "created", None)
            if last_log:
                last_log = str(last_log.date())
            inst_metrics = {
                "institution": i.name,
                "user": u.fullname,
                "guid": u._id,
                "email": u.username,
                "public_projects": u.nodes.filter(
                    type="osf.node",
                    is_public=True,
                    deleted__isnull=True,
                    affiliated_institutions__id=i.id,
                    created__gte=start_dt,
                    created__lt=end_dt,
                )
                .exclude(spam_status=2)
                .count(),
                "public_registrations": u.nodes.filter(
                    type="osf.registration",
                    is_public=True,
                    deleted__isnull=True,
                    affiliated_institutions__id=i.id,
                    created__gte=start_dt,
                    created__lt=end_dt,
                )
                .exclude(spam_status=2)
                .count(),
                "quarterly_actions": 0,
                "date_last_log": last_log,
                "department": i.institutionaffiliation_set.filter(user=u)
                .first()
                .sso_department,
                "created": u.created,
                "date_last_login": u.date_last_login,
            }
            if (
                u.logs.filter(created__gte=start_dt, created__lt=end_dt).exists()
                or u.preprint_logs.filter(
                    created__gte=start_dt, created__lt=end_dt
                ).exists()
            ):
                inst_metrics["quarterly_actions"] += 1
            writer.writerow(inst_metrics)

        pbar.update()

    pbar.close()

    with open(filename, "w") as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")


@timeit
def get_quarterly_inst_metrics(year, quarter):
    """
    Generate a report of institutional metrics for a given quarter.

    Example usage:
    --------------
    get_quarterly_inst_metrics(2023, 2)

    1. year: The year for which the report is to be generated (e.g., 2023).
    2. quarter: The quarter of the year (1 to 4) for which the report is to be generated (e.g., 3 for Q3 (July 1 - Sept 30)).
    """
    import csv

    from django.utils import timezone
    import io
    import pytz
    from tqdm import tqdm

    from osf.models import Institution, OSFUser, Preprint

    filename = "/tmp/institutional_metrics.csv"
    COL_HEADERS = [
        "institution.name",
        "total_users",
        "orcid_total",
        "quarterly_login",
        "quarterly_actions",
        "total_preprints",
        "public_top_projects",
        "private_top_projects",
        "public_projects",
        "private_projects",
        "public_registrations",
        "private_registrations",
        "embargoed_registrations",
        "public_storage",
        "private_storage",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    # compute start and end datetimes of the specified quarter
    quarter_months = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}
    start_month, end_month = quarter_months[quarter]
    start_dt = timezone.datetime(year, start_month, 1, tzinfo=pytz.utc)
    if end_month == 12:
        end_dt = timezone.datetime(year + 1, 1, 1, tzinfo=pytz.utc)
    else:
        end_dt = timezone.datetime(year, end_month + 1, 1, tzinfo=pytz.utc)

    insts = Institution.objects.all()

    pbar = tqdm(total=insts.count())

    for i in insts:
        users = (
            OSFUser.objects.filter(
                institutionaffiliation__institution__id=i.id, is_active=True
            )
            .exclude(spam_status=2)
            .distinct()
        )

        domain_metrics = {
            "institution.name": i.name,
            "total_users": users.count(),
            "orcid_total": 0,
            "quarterly_login": users.filter(
                date_last_login__gte=start_dt, date_last_login__lt=end_dt
            ).count(),
            "quarterly_actions": 0,
            "total_preprints": Preprint.objects.filter(
                _contributors__in=users, is_public=True, is_published=True
            )
            .exclude(spam_status=2)
            .distinct()
            .count(),
            "public_top_projects": i.nodes.filter(
                type="osf.node", is_public=True, deleted__isnull=True
            )
            .exclude(spam_status=2)
            .get_roots()
            .count(),
            "private_top_projects": i.nodes.filter(
                type="osf.node", is_public=False, deleted__isnull=True
            )
            .exclude(spam_status=2)
            .get_roots()
            .count(),
            "public_projects": i.nodes.filter(
                type="osf.node", is_public=True, deleted__isnull=True
            )
            .exclude(spam_status=2)
            .count(),
            "private_projects": i.nodes.filter(
                type="osf.node", is_public=False, deleted__isnull=True
            )
            .exclude(spam_status=2)
            .count(),
            "public_registrations": i.nodes.filter(
                type="osf.registration", is_public=True, deleted__isnull=True
            )
            .exclude(spam_status=2)
            .count(),
            "private_registrations": i.nodes.filter(
                type="osf.registration", is_public=False, deleted__isnull=True
            )
            .exclude(spam_status=2)
            .count(),
            "embargoed_registrations": i.nodes.filter(
                type="osf.registration",
                is_public=False,
                deleted__isnull=True,
                embargo__state="approved",
            )
            .exclude(spam_status=2)
            .count(),
            "public_storage": sum(
                [
                    sum(
                        [
                            s
                            for s in n.files.values_list("versions__size", flat=True)
                            if isinstance(s, int)
                        ]
                    )
                    for n in i.nodes.filter(
                        is_public=True, deleted__isnull=True
                    ).exclude(spam_status=2)
                ]
            ),
            "private_storage": sum(
                [
                    sum(
                        [
                            s
                            for s in n.files.values_list("versions__size", flat=True)
                            if isinstance(s, int)
                        ]
                    )
                    for n in i.nodes.filter(
                        is_public=False, deleted__isnull=True
                    ).exclude(spam_status=2)
                ]
            ),
        }

        for u in users:
            if "VERIFIED" in list(u.external_identity.get("ORCID", {}).values()):
                domain_metrics["orcid_total"] += 1
            if (
                u.logs.filter(created__gte=start_dt, created__lt=end_dt).exists()
                or u.preprint_logs.filter(
                    created__gte=start_dt, created__lt=end_dt
                ).exists()
            ):
                domain_metrics["quarterly_actions"] += 1

        writer.writerow(domain_metrics)
        pbar.update()

    pbar.close()

    with open(filename, "w") as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")


@timeit
def get_inst_preprints_by_provider():
    import csv

    import io
    from tqdm import tqdm

    from osf.models import Institution, OSFUser, PreprintProvider, Preprint

    filename = "/tmp/inst_preprintprovider_metrics.csv"
    COL_HEADERS = ["institution.name", "provider.name", "total_preprints"]
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    insts = Institution.objects.all()

    pbar = tqdm(total=insts.count())

    for i in insts:
        for ppp in PreprintProvider.objects.all():
            users = (
                OSFUser.objects.filter(
                    institutionaffiliation__institution__id=i.id, is_active=True
                )
                .exclude(spam_status=2)
                .distinct()
            )

            domain_metrics = {
                "institution.name": i.name,
                "provider.name": ppp.name,
                "total_preprints": Preprint.objects.filter(
                    _contributors__in=users,
                    provider=ppp,
                    is_public=True,
                    is_published=True,
                )
                .exclude(spam_status=2)
                .distinct()
                .count(),
            }
            if domain_metrics.get("total_preprints", 0):
                writer.writerow(domain_metrics)

        pbar.update(1)

    pbar.close()

    with open(filename, "w") as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")


@timeit
def get_regional_storage_metrics_for_insts(iids=None):
    from addons.osfstorage.models import Region
    from osf.models import Institution

    filename = "/tmp/regional_storage_metrics.csv"
    COL_HEADERS = [
        "institution.name",
        "region.name",
        "public_nodes_all",
        "private_nodes_all",
        "public_storage_all",
        "private_storage_all",
        "public_nodes",
        "private_nodes",
        "public_storage",
        "private_storage",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    if not iids:
        target_insts = list(Institution.objects.all())
    elif isinstance(iids, str):
        i = Institution.load(iids)
        if not i:
            print(f"Unable to find Inst {iids}")
            return
        target_insts = [i]
    elif isinstance(iids, list):
        target_insts = list(Institution.objects.filter(_id__in=iids))
    else:
        print(f"Unable to parse iids {iids}")
        return

    pbar = tqdm(total=len(target_insts))

    for i in target_insts:
        for r in Region.objects.all():
            ns = i.nodes.filter(addons_osfstorage_node_settings__region=r).exclude(
                spam_status=2
            )
            domain_metrics = {
                "institution.name": i.name,
                "region.name": r.name,
                "public_nodes_all": ns.filter(is_public=True).count(),
                "private_nodes_all": ns.filter(is_public=False).count(),
                "public_storage_all": sum(
                    [
                        sum(
                            [
                                s
                                for s in n.files.values_list(
                                    "versions__size", flat=True
                                )
                                if isinstance(s, int)
                            ]
                        )
                        for n in ns.filter(is_public=True)
                    ]
                ),
                "private_storage_all": sum(
                    [
                        sum(
                            [
                                s
                                for s in n.files.values_list(
                                    "versions__size", flat=True
                                )
                                if isinstance(s, int)
                            ]
                        )
                        for n in ns.filter(is_public=False)
                    ]
                ),
                # excluding deleted
                "public_nodes": ns.filter(is_public=True, deleted__isnull=True).count(),
                "private_nodes": ns.filter(
                    is_public=False, deleted__isnull=True
                ).count(),
                "public_storage": sum(
                    [
                        sum(
                            [
                                s
                                for s in n.files.values_list(
                                    "versions__size", flat=True
                                )
                                if isinstance(s, int)
                            ]
                        )
                        for n in ns.filter(is_public=True, deleted__isnull=True)
                    ]
                ),
                "private_storage": sum(
                    [
                        sum(
                            [
                                s
                                for s in n.files.values_list(
                                    "versions__size", flat=True
                                )
                                if isinstance(s, int)
                            ]
                        )
                        for n in ns.filter(is_public=False, deleted__isnull=True)
                    ]
                ),
            }
            # skip if public_nodes_all and private_nodes_all are 0, in case there are deleted nodes in a regions
            if domain_metrics.get("public_nodes_all", 0) or domain_metrics.get(
                "private_nodes_all", 0
            ):
                writer.writerow(domain_metrics)
        pbar.update(1)

    pbar.close()

    with open(filename, "w") as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")


# Main function to run quarterly metrics
def run_quarterly_metrics(year, quarter):
    """
    Run all quarterly metrics functions for a given year and quarter.

    Notes:
    ------
    1. This function does not include views data since it requires Elasticsearch access.  Pre-bake a copy of `inst_views.py` with the needed year and quarter and send to Engineering to execute.
    """
    logging.info(f"Starting quarterly metrics for {year} Q{quarter}")
    get_domain_metrics()
    get_quarterly_active_users(year, quarter)
    get_quarterly_inst_metrics(year, quarter)
    get_inst_preprints_by_provider()
    get_regional_storage_metrics_for_insts()
    logging.info(f"Completed quarterly metrics for {year} Q{quarter}")


if __name__ == "__main__":
    run_quarterly_metrics(2025, 4)
