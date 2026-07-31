def get_embargoed_registrations(start_month, end_month=None):
    import csv
    import io
    import datetime
    from tqdm import tqdm
    import json
    from django.utils import timezone
    import pytz
    from dateutil.relativedelta import relativedelta

    filename = '/tmp/embargoed_registrations.csv'
    COL_HEADERS = ['reg_guid', 'is_public', 'embargo_state', 
                   'creator_guid', 'is_creators_first_reg', 'creator_total_reg_count', 
                   'creator_embargo_state_reg_count', 'creator_approved_embargo_reg_count', 'creator_completed_embargo_reg_count', 
                   'date_embargo_initiated', 'date_embargo_ended',
                   'date_created', 'date_registered',
                   'root_guid', 'date_root_created',
                   'registered_from_guid', 'date_registered_from_created',
                   'contributor_count', 'subject']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    start_y, start_m = map(int, start_month.split("-"))
    start = timezone.datetime(start_y, start_m, 1, tzinfo=pytz.utc)

    # currently embargoed registrations: is_public=False, deleted__isnull=True, embargo__state='approved'
    target_regs = Registration.objects.filter(created__gte=start, is_public=True, embargo__state__isnull=False)

    if end_month:
        end_y, end_m = map(int, end_month.split("-"))
        end = timezone.datetime(end_y, end_m, 1, tzinfo=pytz.utc)

        target_regs = Registration.objects.filter(created__gte=start, created__lt=end, is_public=True, embargo__state__isnull=False)

    for reg in tqdm(target_regs, total = target_regs.count()):
        creator_regs = reg.creator.nodes_created.filter(type='osf.registration')

        writer.writerow({
            'reg_guid': reg._id,
            'is_public': reg.is_public,
            'embargo_state': reg.embargo.state if reg.embargo else None,
            'creator_guid': reg.creator._id,
            'is_creators_first_reg': True if reg == reg.creator.nodes_created.filter(type='osf.registration').order_by('created').first() else False,
            'creator_total_reg_count': creator_regs.count(),
            # count regs that have any embargo state (approved, completed, rejected, pending_moderation, moderator_rejected, unapproved)
            'creator_embargo_state_reg_count': creator_regs.filter(embargo__state__isnull=False).count(),
            'creator_approved_embargo_reg_count': creator_regs.filter(embargo__state='approved').count(),
            'creator_completed_embargo_reg_count': creator_regs.filter(embargo__state='completed').count(),
            'date_embargo_initiated': reg.embargo.initiation_date,
            'date_embargo_ended': reg.embargo.end_date,
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