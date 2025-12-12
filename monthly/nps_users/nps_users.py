# Optimized
# Needs to be merged with output of write_nps_users_insts() below: see merge_nps_users_insts() below

def write_nps_users_csv(n=None):
    import io
    import csv
    from collections import defaultdict
    from tqdm import tqdm
    from django.db.models import OuterRef, Subquery, F, Func

    from osf.models import OSFUser, Node, Registration, Preprint, NodeLog, PreprintLog

    
    filename = f'/tmp/nps_users.csv'
    fieldnames = ['u._id', 'u.username', 'u.date_confirmed', 'u.date_last_login', 'u.date_last_action', 'public_projects_created', 'private_projects_created', 'public_registrations_created', 'withdrawn_registrations_created', 'embargoed_registrations_created', 'published_preprints_created', 'withdrawn_preprints_created', 'public_projects_contributor', 'private_projects_contributor', 'public_registrations_contributor', 'withdrawn_registrations_contributor', 'embargoed_registrations_contributor', 'published_preprints_contributor', 'withdrawn_preprints_contributor']

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()

    # prefetch all logs
    print("Prefetching NodeLog entries...")
    log_entries = defaultdict(list)
    for log in NodeLog.objects.all().values('user_id', 'created'):
        log_entries[log['user_id']].append(log['created'])

    print("Prefetching PreprintLog entries...")
    preprint_log_entries = defaultdict(list)
    for plog in PreprintLog.objects.all().values('user_id', 'created'):
        preprint_log_entries[plog['user_id']].append(plog['created'])

    # subqueries for project/registration/preprint counts based on creators and contributors
    pubn_subq_created = Node.objects.filter(creator_id=OuterRef('pk'), is_public=True, deleted__isnull=True).annotate(count=Func(F('id'), function='Count')).values('count')
    privn_subq_created = Node.objects.filter(creator_id=OuterRef('pk'), is_public=False, deleted__isnull=True).annotate(count=Func(F('id'), function='Count')).values('count')
    pubr_subq_created = Registration.objects.filter(creator_id=OuterRef('pk'), is_public=True, deleted__isnull=True).exclude(retraction__state='approved').annotate(count=Func(F('id'), function='Count')).values('count')
    withr_subq_created = Registration.objects.filter(creator_id=OuterRef('pk'), is_public=True, deleted__isnull=True, retraction__state='approved').annotate(count=Func(F('id'), function='Count')).values('count')
    embr_subq_created = Registration.objects.filter(creator_id=OuterRef('pk'), is_public=False, deleted__isnull=True, embargo__state='approved').annotate(count=Func(F('id'), function='Count')).values('count')
    pubp_subq_created = Preprint.objects.filter(creator_id=OuterRef('pk'), is_public=True, is_published=True, deleted__isnull=True).exclude(machine_state='withdrawn').annotate(count=Func(F('id'), function='Count')).values('count')
    withp_subq_created = Preprint.objects.filter(creator_id=OuterRef('pk'), is_public=True, is_published=True, deleted__isnull=True, machine_state='withdrawn').annotate(count=Func(F('id'), function='Count')).values('count')
    pubn_subq_contributor = Node.objects.filter(_contributors=OuterRef('pk'), is_public=True, deleted__isnull=True).annotate(count=Func(F('id'), function='Count')).values('count')
    privn_subq_contributor = Node.objects.filter(_contributors=OuterRef('pk'), is_public=False, deleted__isnull=True).annotate(count=Func(F('id'), function='Count')).values('count')
    pubr_subq_contributor = Registration.objects.filter(_contributors=OuterRef('pk'), is_public=True, deleted__isnull=True).exclude(retraction__state='approved').annotate(count=Func(F('id'), function='Count')).values('count')
    withr_subq_contributor = Registration.objects.filter(_contributors=OuterRef('pk'), is_public=True, deleted__isnull=True, retraction__state='approved').annotate(count=Func(F('id'), function='Count')).values('count')
    embr_subq_contributor = Registration.objects.filter(_contributors=OuterRef('pk'), is_public=False, deleted__isnull=True, embargo__state='approved').annotate(count=Func(F('id'), function='Count')).values('count')
    pubp_subq_contributor = Preprint.objects.filter(_contributors=OuterRef('pk'), is_public=True, is_published=True, deleted__isnull=True).exclude(machine_state='withdrawn').annotate(count=Func(F('id'), function='Count')).values('count')
    withp_subq_contributor = Preprint.objects.filter(_contributors=OuterRef('pk'), is_public=True, is_published=True, deleted__isnull=True, machine_state='withdrawn').annotate(count=Func(F('id'), function='Count')).values('count')

    qs = OSFUser.objects.filter(is_active=True).exclude(spam_status__in=[1,2]).annotate(
        public_projects_created=Subquery(pubn_subq_created),
        private_projects_created=Subquery(privn_subq_created),
        public_registrations_created=Subquery(pubr_subq_created),
        withdrawn_registrations_created=Subquery(withr_subq_created),
        embargoed_registrations_created=Subquery(embr_subq_created),
        published_preprints_created=Subquery(pubp_subq_created),
        withdrawn_preprints_created=Subquery(withp_subq_created),
        public_projects_contributor=Subquery(pubn_subq_contributor),
        private_projects_contributor=Subquery(privn_subq_contributor),
        public_registrations_contributor=Subquery(pubr_subq_contributor),
        withdrawn_registrations_contributor=Subquery(withr_subq_contributor),
        embargoed_registrations_contributor=Subquery(embr_subq_contributor),
        published_preprints_contributor=Subquery(pubp_subq_contributor),
        withdrawn_preprints_contributor=Subquery(withp_subq_contributor)
    )
    if n:
        qs = qs[:n]

    pbar = tqdm(total=qs.count())
    for udict in qs.values(
        'guids___id', 'username', 'date_confirmed', 'date_last_login',
        'public_projects_created', 'private_projects_created',
        'public_registrations_created', 'withdrawn_registrations_created', 'embargoed_registrations_created',
        'published_preprints_created', 'withdrawn_preprints_created',
        'public_projects_contributor', 'private_projects_contributor',
        'public_registrations_contributor', 'withdrawn_registrations_contributor', 'embargoed_registrations_contributor',
        'published_preprints_contributor', 'withdrawn_preprints_contributor'
    ):
        uid = udict['guids___id']
        udict['u._id'] = udict.pop('guids___id')
        udict['u.username'] = udict.pop('username')
        udict['u.date_confirmed'] = udict.pop('date_confirmed').date().isoformat() if udict['date_confirmed'] else None
        if udict['date_last_login'] is not None:
            udict['u.date_last_login'] = udict.pop('date_last_login').date().isoformat()
        else:
            udict['u.date_last_login'] = udict.pop('date_last_login')

        # compute date of last action from pre-fetched logs
        user_obj = OSFUser.objects.get(guids___id=uid)
        last_dates = log_entries.get(user_obj.id, []) + preprint_log_entries.get(user_obj.id, [])
        udict['u.date_last_action'] = max(last_dates).date().isoformat() if last_dates else None

        writer.writerow(udict)
        pbar.update()
    pbar.close()

    with open(filename, 'w') as f:
        f.write(output.getvalue())

    print(f"Output written to {filename}")