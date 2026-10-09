# Total, not only for the quarter
def get_domain_metrics(ds=None):
    import csv
    import os
    from django.utils import timezone
    from tqdm import tqdm

    filename = '/tmp/all_domain_metrics.csv'
    COL_HEADERS = ['domain', 'total_users', 'orcid_total', 'annual_login', 'annual_actions', 'total_nodes', 'public_nodes', 'total_regs', 'public_regs', 'total_preprints', 'published_preprints']

    if not ds:
        unames = Email.objects.filter(user__is_active=True).exclude(user__spam_status=2).values_list('address', flat=True)
        ds = set([u.split('@')[1] for u in unames if '@' in u])

    # sort domains for predictable processing order
    ds = sorted(set(ds))

    # load domains already completed so the script can resume
    completed = set()
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        with open(filename, 'r', newline='') as read_file:
            reader = csv.DictReader(read_file)
            completed = {
                row['domain'] for row in reader
                if row.get('domain')
            }

    remaining = [d for d in ds if d not in completed]

    print(f"Total domains: {len(ds)}")
    print(f"Already completed: {len(completed)}")
    print(f"Remaining: {len(remaining)}")

    target_date = timezone.now() - timezone.timedelta(days=365)

    # append to existing file or create a new file with headers
    write_header = (
        not os.path.exists(filename)
        or os.path.getsize(filename) == 0
    )

    with open(filename, 'a', newline='') as write_file:
        writer = csv.DictWriter(write_file, fieldnames=COL_HEADERS)

        if write_header:
            writer.writeheader()
            write_file.flush()

        for d in tqdm(remaining, desc='Processing domains...'):
            users = OSFUser.objects.filter(
                        is_active=True,
                        id__in=Email.objects.filter(address__endswith=f'@{d}').values_list('user_id', flat=True).distinct()
                    ).exclude(spam_status=2)

            ns = Node.objects.filter(_contributors__in=users, deleted__isnull=True, is_deleted=False).exclude(spam_status__in=[1,2]).distinct()
            rs = Registration.objects.filter(_contributors__in=users, deleted__isnull=True, is_deleted=False).exclude(spam_status__in=[1,2]).distinct()
            ps = Preprint.objects.filter(_contributors__in=users, deleted__isnull=True).exclude(machine_state='initial').exclude(spam_status__in=[1,2]).distinct()

            domain_metrics = {
                'domain': d,
                'total_users': users.count(),
                'orcid_total': 0,
                'annual_login': users.filter(date_last_login__gte=target_date).count(),
                'annual_actions': 0,
                'total_nodes': ns.count(),
                'public_nodes': ns.filter(is_public=True).count(),
                'total_regs': rs.count(),
                'public_regs': rs.filter(is_public=True).exclude(moderation_state='withdrawn').count(),
                'total_preprints': ps.count(),
                'published_preprints': ps.filter(is_public=True, is_published=True).exclude(machine_state='withdrawn').count()
                    }

            for u in users:
                if 'VERIFIED' in list(u.external_identity.get('ORCID', {}).values()):
                    domain_metrics['orcid_total'] += 1
                if u.logs.filter(created__gte=target_date).exists() or u.preprint_logs.filter(created__gte=target_date).exists():
                    domain_metrics['annual_actions'] += 1

            # save each completed domain immediately
            writer.writerow(domain_metrics)
            write_file.flush()

    print(f"Output written to {filename}")
    print(f"Domains completed this run: {len(remaining)}")
    print(f"Domains completed overall: {len(completed) + len(remaining)}")