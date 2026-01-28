import time
from functools import wraps


def timeit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        elapsed = end - start
        print(f"Function '{func.__name__}' executed in {elapsed / 60:.2f} mins")
        return result

    return wrapper


# Total, not only for the quarter
@timeit
def get_domain_metrics(ds=None):
    import csv
    import io
    from django.utils import timezone
    from tqdm import tqdm

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
