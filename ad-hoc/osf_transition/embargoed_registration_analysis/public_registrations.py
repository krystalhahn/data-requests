def get_public_registrations(start_month, end_month=None):
    import csv
    import json
    import pytz
    from django.db.models import Count, Prefetch
    from django.utils import timezone
    from tqdm import tqdm

    filename = "/tmp/public_registrations.csv"
    COL_HEADERS = ['reg_guid', 'is_public', 'is_deleted', 'embargo_state', 'reg_creator',
                   'date_created', 'date_registered',
                   'root_guid', 'date_root_created',
                   'registered_from_guid', 'date_registered_from_created',
                   'contributor_count', 'subject']

    start_year, start_month_num = map(int, start_month.split("-"))
    start = timezone.datetime(start_year, start_month_num, 1, tzinfo=pytz.UTC)

    queryset = (Registration.objects.filter(created__gte=start,is_public=True,)
        .select_related("creator", "embargo", "root", "registered_from")
        .prefetch_related(Prefetch("subjects"))
        .annotate(contributor_count=Count("_contributors", distinct=True) )
    )

    if end_month:
        end_year, end_month_num = map(int, end_month.split("-"))
        end = timezone.datetime(end_year, end_month_num, 1, tzinfo=pytz.UTC)
        queryset = queryset.filter(created__lt=end)

    total = queryset.count()

    with open(filename, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=COL_HEADERS)
        writer.writeheader()

        for reg in tqdm(queryset.iterator(chunk_size=1000), total=total):
            writer.writerow({
                "reg_guid": reg._id,
                "is_public": reg.is_public,
                "is_deleted": bool(reg.deleted) or None,
                "embargo_state": reg.embargo.state if reg.embargo else None,
                "reg_creator": reg.creator._id,
                "date_created": reg.created,
                "date_registered": reg.registered_date,
                "root_guid": reg.root._id if reg.root else None,
                "date_root_created": reg.root.created if reg.root else None,
                "registered_from_guid": (
                    reg.registered_from._id
                    if reg.registered_from
                    else None
                ),
                "date_registered_from_created": (
                    reg.registered_from.created
                    if reg.registered_from
                    else None
                ),
                "contributor_count": reg.contributor_count,
                "subject": json.dumps(
                    [subject.text for subject in reg.subjects.all()]
                ),
            })

    print(f"Output written to {filename}")
