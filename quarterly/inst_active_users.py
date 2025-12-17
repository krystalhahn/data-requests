def get_quarterly_active_users():
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

    targets = Institution.objects.all()

    pbar = tqdm(total=targets.count())

    jul = timezone.datetime(2025,7,1,tzinfo=pytz.utc)
    oct = timezone.datetime(2025,10,1,tzinfo=pytz.utc)

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
                'public_projects': u.nodes.filter(type='osf.node', is_public=True, deleted__isnull=True, affiliated_institutions__id=i.id, created__gte=jul, created__lt=oct).exclude(spam_status=2).count(),
                'public_registrations': u.nodes.filter(type='osf.registration', is_public=True, deleted__isnull=True, affiliated_institutions__id=i.id, created__gte=jul, created__lt=oct).exclude(spam_status=2).count(),
                'quarterly_actions': 0,
                'date_last_log': last_log,
                'department': i.institutionaffiliation_set.filter(user=u).first().sso_department,
                'created': u.created,
                'date_last_login': u.date_last_login
            }
            if u.logs.filter(created__gte=jul, created__lt=oct).exists() or u.preprint_logs.filter(created__gte=jul, created__lt=oct).exists():
                inst_metrics['quarterly_actions'] += 1
            writer.writerow(inst_metrics)

        pbar.update()

    pbar.close()

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")