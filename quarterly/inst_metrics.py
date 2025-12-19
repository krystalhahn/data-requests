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

# further optimized version with active_users and quarterly_actions
# original counts quarterly_actions as number of users with one action in specified period --> active_users
# count all logged actions in specified period for each user --> quarterly_actions
def get_quarterly_inst_metrics(year, quarter):
    import csv
    import io
    from django.db.models import Q, Count
    from django.utils import timezone
    import pytz
    from collections import defaultdict, Counter
    from tqdm import tqdm

    filename = f'/tmp/institutional_metrics.csv'
    COL_HEADERS = [
        'institution.name', 'total_users', 'active_users', 'orcid_total',
        'quarterly_login', 'quarterly_actions', 'total_preprints',
        'public_top_projects', 'private_top_projects', 'public_projects', 'private_projects',
        'public_registrations', 'private_registrations', 'embargoed_registrations',
        'public_storage', 'private_storage'
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    # compute start and end datetimes of the specified quarter
    quarter_months = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}
    start_month, end_month = quarter_months[quarter]
    start_dt = timezone.datetime(year, start_month, 1, tzinfo=pytz.utc)
    end_dt = timezone.datetime(year + 1, 1, 1, tzinfo=pytz.utc) if end_month == 12 else timezone.datetime(year, end_month + 1, 1, tzinfo=pytz.utc)

    # fetch all institutions
    insts = list(Institution.objects.all())
    inst_ids = [i.id for i in insts]
    print(f"Fetched {len(insts)} institutions")

    # fetch all active users in these institutions
    users = OSFUser.objects.filter(
        institutionaffiliation__institution__id__in=inst_ids,
        is_active=True
    ).exclude(spam_status=2).distinct().prefetch_related('logs', 'preprint_logs')
    print(f"Fetched {users.count()} active users in all institutions")

    # map users to institutions
    user_inst_map = defaultdict(list)
    for u in users:
        for aff in u.institutionaffiliation_set.filter(institution_id__in=inst_ids):
            user_inst_map[aff.institution_id].append(u)
    print("Completed mapping users to institutions")

    # bulk compute ORCID verified per user
    orcid_verified_map = {u.id: ('VERIFIED' in u.external_identity.get('ORCID', {}).values()) for u in users}
    print("Completed computing ORCID verification for users")

    # bulk compute quarterly logins per user
    quarterly_login_map = {u.id: u.date_last_login is not None and start_dt <= u.date_last_login < end_dt for u in users}
    print("Completed computing quarterly logins for users")

    # bulk compute actions per user
    node_actions = Counter(NodeLog.objects.filter(
        user__in=users, created__gte=start_dt, created__lt=end_dt
    ).values_list('user_id', flat=True))
    preprint_actions = Counter(PreprintLog.objects.filter(
        user__in=users, created__gte=start_dt, created__lt=end_dt
    ).values_list('user_id', flat=True))
    user_actions_map = {u.id: node_actions.get(u.id, 0) + preprint_actions.get(u.id, 0) for u in users}
    print("Completed computing quarterly actions for users")

    # iterate institutions
    pbar = tqdm(total=len(insts))
    for inst in insts:
        inst_users = user_inst_map.get(inst.id, [])
        inst_user_ids = [u.id for u in inst_users]

        domain_metrics = {
            'institution.name': inst.name,
            'total_users': len(inst_users),
            'orcid_total': sum(orcid_verified_map[u.id] for u in inst_users),
            'quarterly_login': sum(quarterly_login_map[u.id] for u in inst_users),
            'quarterly_actions': sum(user_actions_map[u.id] for u in inst_users),
            'active_users': sum(1 for u in inst_users if user_actions_map[u.id] > 0),
            'total_preprints': Preprint.objects.filter(_contributors__in=inst_users, is_public=True, is_published=True).exclude(spam_status=2).distinct().count(),
            'public_top_projects': inst.nodes.filter(type='osf.node', is_public=True, deleted__isnull=True).exclude(spam_status=2).get_roots().count(),
            'private_top_projects': inst.nodes.filter(type='osf.node', is_public=False, deleted__isnull=True).exclude(spam_status=2).get_roots().count(),
            'public_projects': inst.nodes.filter(type='osf.node', is_public=True, deleted__isnull=True).exclude(spam_status=2).count(),
            'private_projects': inst.nodes.filter(type='osf.node', is_public=False, deleted__isnull=True).exclude(spam_status=2).count(),
            'public_registrations': inst.nodes.filter(type='osf.registration', is_public=True, deleted__isnull=True).exclude(spam_status=2).count(),
            'private_registrations': inst.nodes.filter(type='osf.registration', is_public=False, deleted__isnull=True).exclude(spam_status=2).count(),
            'embargoed_registrations': inst.nodes.filter(type='osf.registration', is_public=False, deleted__isnull=True, embargo__state='approved').exclude(spam_status=2).count(),
            'public_storage': sum([sum([s for s in n.files.values_list('versions__size', flat=True) if isinstance(s, int)]) for n in inst.nodes.filter(is_public=True, deleted__isnull=True).exclude(spam_status=2)]),
            'private_storage': sum([sum([s for s in n.files.values_list('versions__size', flat=True) if isinstance(s, int)]) for n in inst.nodes.filter(is_public=False, deleted__isnull=True).exclude(spam_status=2)])
        }

        writer.writerow(domain_metrics)
        pbar.update()

    pbar.close()

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")
