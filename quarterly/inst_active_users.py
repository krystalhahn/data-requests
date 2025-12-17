def get_annual_top_active_users():
    from osf.metrics import CountedAuthUsage
    import csv
    import io
    filename = '/tmp/inst_active_users.csv'
    COL_HEADERS = ['institution', 'user', 'guid', 'public_projects', 'public_registrations', 'date_last_log', 'department', 'created', 'date_last_login']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()
    targets = Institution.objects.all()
    for i in targets:
        users = OSFUser.objects.filter(
            institutionaffiliation__institution__id=i.id,
            is_active=True
        ).exclude(spam_status=2).distinct()
        for u in users:
            last_log = getattr(u.logs.order_by('-created').first(), 'created', None)
            if last_log:
                last_log = str(last_log.date())
            metric = {
                'institution': i.name,
                'user': u.fullname,
                'guid': u._id,
                'public_projects': u.nodes.filter(type='osf.node', is_public=True, deleted__isnull=True, affiliated_institutions__id=i.id).exclude(spam_status=2).count(),
                'public_registrations': u.nodes.filter(type='osf.registration', is_public=True, deleted__isnull=True, affiliated_institutions__id=i.id).exclude(spam_status=2).count(),
                'date_last_log': last_log,
                'department': i.institutionaffiliation_set.filter(user=u).first().sso_department,
                'created': u.created,
                'date_last_login': u.date_last_login
            }
            writer.writerow(metric)
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())