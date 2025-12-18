# example usage
get_quarterly_inst_metrics(2025, 3)  # Q3 of 2025 (July 1 - Sept 30)

def get_quarterly_inst_metrics(year, quarter):
    import csv
    import io
    from django.utils import timezone
    import pytz
    from tqdm import tqdm

    filename = f'/tmp/institutional_metrics.csv'
    COL_HEADERS = ['institution.name', 'total_users', 'orcid_total', 'quarterly_login', 'quarterly_actions', 'total_preprints', 'public_top_projects', 'private_top_projects', 'public_projects', 'private_projects', 'public_registrations', 'private_registrations', 'embargoed_registrations', 'public_storage', 'private_storage']
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
        users = OSFUser.objects.filter(
            institutionaffiliation__institution__id=i.id,
            is_active=True
        ).exclude(spam_status=2).distinct()

        domain_metrics = {
            'institution.name': i.name,
            'total_users': users.count(),
            'orcid_total': 0,
            'quarterly_login': users.filter(date_last_login__gte=start_dt, date_last_login__lt=end_dt).count(),
            'quarterly_actions': 0,
            'total_preprints': Preprint.objects.filter(_contributors__in=users, is_public=True, is_published=True).exclude(spam_status=2).distinct().count(),
            'public_top_projects': i.nodes.filter(type='osf.node', is_public=True, deleted__isnull=True).exclude(spam_status=2).get_roots().count(),
            'private_top_projects': i.nodes.filter(type='osf.node', is_public=False, deleted__isnull=True).exclude(spam_status=2).get_roots().count(),
            'public_projects': i.nodes.filter(type='osf.node', is_public=True, deleted__isnull=True).exclude(spam_status=2).count(),
            'private_projects': i.nodes.filter(type='osf.node', is_public=False, deleted__isnull=True).exclude(spam_status=2).count(),
            'public_registrations': i.nodes.filter(type='osf.registration', is_public=True, deleted__isnull=True).exclude(spam_status=2).count(),
            'private_registrations': i.nodes.filter(type='osf.registration', is_public=False, deleted__isnull=True).exclude(spam_status=2).count(),
            'embargoed_registrations': i.nodes.filter(type='osf.registration', is_public=False, deleted__isnull=True, embargo__state='approved').exclude(spam_status=2).count(),
            'public_storage': sum([sum([s for s in n.files.values_list('versions__size', flat=True) if isinstance(s, int)]) for n in i.nodes.filter(is_public=True, deleted__isnull=True).exclude(spam_status=2)]),
            'private_storage': sum([sum([s for s in n.files.values_list('versions__size', flat=True) if isinstance(s, int)]) for n in i.nodes.filter(is_public=False, deleted__isnull=True).exclude(spam_status=2)])
        }

        for u in users:
            if 'VERIFIED' in list(u.external_identity.get('ORCID', {}).values()):
                domain_metrics['orcid_total'] += 1
            if u.logs.filter(created__gte=start_dt, created__lt=end_dt).exists() or u.preprint_logs.filter(created__gte=start_dt, created__lt=end_dt).exists():
                domain_metrics['quarterly_actions'] += 1

        writer.writerow(domain_metrics)
        pbar.update()

    pbar.close()

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")