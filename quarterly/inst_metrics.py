# Added top-level projects
def get_quarterly_inst_metrics():
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
    insts = Institution.objects.all()
    jul = timezone.datetime(2025,7,1,tzinfo=pytz.utc)
    oct = timezone.datetime(2025,10,1,tzinfo=pytz.utc)
    for i in insts:
        users = OSFUser.objects.filter(
            institutionaffiliation__institution__id=i.id,
            is_active=True
        ).exclude(spam_status=2).distinct()
        domain_metrics = {
            'institution.name': i.name,
            'total_users': users.count(),
            'orcid_total': 0,
            'quarterly_login': users.filter(date_last_login__gte=jul, date_last_login__lt=oct).count(),
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
            if u.logs.filter(created__gte=jul, created__lt=oct).exists() or u.preprint_logs.filter(created__gte=jul, created__lt=oct).exists():
                domain_metrics['quarterly_actions'] += 1
        writer.writerow(domain_metrics)
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())