# example usage
get_quarterly_active_users(2025, 3) # Q3 of 2025 (July 1 - Sept 30)

def get_quarterly_active_users(year, quarter):
    from osf.metrics import CountedAuthUsage
    import csv
    import io
    import pytz
    from tqdm import tqdm 

    filename = '/tmp/inst_active_users.csv'
    COL_HEADERS = ['institution', 'user', 'guid', 'email', 'public_projects', 'public_registrations', 'quarterly_actions', 'date_last_log', 'department', 'created', 'date_last_login']
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
        users = OSFUser.objects.filter(
            institutionaffiliation__institution__id=i.id,
            is_active=True
        ).exclude(spam_status=2).distinct()
        
        for u in users:
            last_log = getattr(u.logs.order_by('-created').first(), 'created', None)
            if last_log:
                last_log = str(last_log.date())
            inst_metrics = {
                'institution': i.name,
                'user': u.fullname,
                'guid': u._id,
                'email': u.username,
                'public_projects': u.nodes.filter(type='osf.node', is_public=True, deleted__isnull=True, affiliated_institutions__id=i.id, created__gte=start_dt, created__lt=end_dt).exclude(spam_status=2).count(),
                'public_registrations': u.nodes.filter(type='osf.registration', is_public=True, deleted__isnull=True, affiliated_institutions__id=i.id, created__gte=start_dt, created__lt=end_dt).exclude(spam_status=2).count(),
                'quarterly_actions': 0,
                'date_last_log': last_log,
                'department': i.institutionaffiliation_set.filter(user=u).first().sso_department,
                'created': u.created,
                'date_last_login': u.date_last_login
            }
            if u.logs.filter(created__gte=start_dt, created__lt=end_dt).exists() or u.preprint_logs.filter(created__gte=start_dt, created__lt=end_dt).exists():
                inst_metrics['quarterly_actions'] += 1
            writer.writerow(inst_metrics)

        pbar.update()

    pbar.close()

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")