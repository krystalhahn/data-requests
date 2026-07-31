def get_public_registrations(start_month, end_month=None):
    import csv
    import io
    import datetime
    from tqdm import tqdm
    import json
    from django.utils import timezone
    import pytz
    from dateutil.relativedelta import relativedelta

    filename = '/tmp/public_registrations.csv'
    COL_HEADERS = ['reg_guid', 'is_public', 'is_deleted', 'embargo_state', 'reg_creator',
                   'date_created', 'date_registered',
                   'root_guid', 'date_root_created',
                   'registered_from_guid', 'date_registered_from_created',
                   'contributor_count', 'subject']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    start_y, start_m = map(int, start_month.split("-"))
    start = timezone.datetime(start_y, start_m, 1, tzinfo=pytz.utc)

    target_regs = Registration.objects.filter(created__gte=start, is_public=True)

    if end_month:
        end_y, end_m = map(int, end_month.split("-"))
        end = timezone.datetime(end_y, end_m, 1, tzinfo=pytz.utc)

        target_regs = Registration.objects.filter(created__gte=start, created__lt=end, is_public=True)

    for reg in tqdm(target_regs, total = target_regs.count()):
        writer.writerow({
            'reg_guid': reg._id,
            'is_public': reg.is_public,
            'is_deleted': True if reg.deleted else None,
            'embargo_state': reg.embargo.state if reg.embargo else None,
            'reg_creator': reg.creator._id,
            'date_created': reg.created,
            'date_registered': reg.registered_date,
            'root_guid': reg.root._id if reg.root else None,
            'date_root_created': reg.root.created if reg.root else None,
            'registered_from_guid': reg.registered_from._id if reg.registered_from else None,
            'date_registered_from_created': reg.registered_from.created if reg.registered_from else None,
            'contributor_count': reg.contributors.count(),
            'subject': json.dumps(list(reg.subjects.values_list('text', flat=True)) if hasattr(reg, 'subjects') else [])
        })

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")