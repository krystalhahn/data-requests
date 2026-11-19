def get_new_confirmed_users(start):
    import io
    import csv
    from tqdm import tqdm
    from django.db.models import OuterRef, Subquery, F, Func, Max
    from osf.models import OSFUser, Node, Registration, Preprint, NodeLog, PreprintLog

    filename = f'/tmp/new_confirmed_users.csv'
    fieldnames = ['u._id', 'u.username', 'u.date_confirmed', 'u.date_last_login', 'u.date_last_action',
                  'u.academiaInstitution', 'u.academiaProfileID', 'u.baiduScholar', 'u.github', 'u.impactStory', 'u.linkedIn', 'u.profileWebsites', 'u.researchGate', 'u.researcherId', 'u.scholar', 'u.ssrn', 'u.twitter', 
                  'public_projects_created', 'private_projects_created', 
                  'public_registrations_created', 'withdrawn_registrations_created', 'embargoed_registrations_created', 
                  'published_preprints_created', 'withdrawn_preprints_created', 
                  'public_projects_contributor', 'private_projects_contributor', 
                  'public_registrations_contributor', 'withdrawn_registrations_contributor', 'embargoed_registrations_contributor', 
                  'published_preprints_contributor', 'withdrawn_preprints_contributor']

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()

    start_y, start_m, start_d = map(int, start.split("-"))
    start = timezone.datetime(start_y, start_m, start_d, tzinfo=pytz.utc)

    # subqueries for most recent user actions
    node_last_subq = (
        NodeLog.objects
        .filter(user_id=OuterRef('pk'))
        .order_by('-created')
        .values('created')[:1]
    )

    preprint_last_subq = (
        PreprintLog.objects
        .filter(user_id=OuterRef('pk'))
        .order_by('-created')
        .values('created')[:1]
    )

    # subqueries for project/registration/preprint counts based on creators and contributors
    def count_subq(qs):
        return qs.annotate(count=Func(F('id'), function='Count')).values('count')

    pubn_subq_created = count_subq(Node.objects.filter(creator_id=OuterRef('pk'), is_public=True, deleted__isnull=True))
    privn_subq_created = count_subq(Node.objects.filter(creator_id=OuterRef('pk'), is_public=False, deleted__isnull=True))
    pubr_subq_created = count_subq(Registration.objects.filter(creator_id=OuterRef('pk'), is_public=True, deleted__isnull=True).exclude(retraction__state='approved'))
    withr_subq_created = count_subq(Registration.objects.filter(creator_id=OuterRef('pk'), is_public=True, deleted__isnull=True, retraction__state='approved'))
    embr_subq_created = count_subq(Registration.objects.filter(creator_id=OuterRef('pk'), is_public=False, deleted__isnull=True, embargo__state='approved'))
    pubp_subq_created = count_subq(Preprint.objects.filter(creator_id=OuterRef('pk'), is_public=True, is_published=True, deleted__isnull=True).exclude(machine_state='withdrawn'))
    withp_subq_created = count_subq(Preprint.objects.filter(creator_id=OuterRef('pk'), is_public=True, is_published=True, deleted__isnull=True, machine_state='withdrawn'))
    pubn_subq_contributor = count_subq(Node.objects.filter(_contributors=OuterRef('pk'), is_public=True, deleted__isnull=True))
    privn_subq_contributor = count_subq(Node.objects.filter(_contributors=OuterRef('pk'), is_public=False, deleted__isnull=True))
    pubr_subq_contributor = count_subq(Registration.objects.filter(_contributors=OuterRef('pk'), is_public=True, deleted__isnull=True).exclude(retraction__state='approved'))
    withr_subq_contributor = count_subq(Registration.objects.filter(_contributors=OuterRef('pk'), is_public=True, deleted__isnull=True, retraction__state='approved'))
    embr_subq_contributor = count_subq(Registration.objects.filter(_contributors=OuterRef('pk'), is_public=False, deleted__isnull=True, embargo__state='approved'))
    pubp_subq_contributor = count_subq(Preprint.objects.filter(_contributors=OuterRef('pk'), is_public=True, is_published=True, deleted__isnull=True).exclude(machine_state='withdrawn'))
    withp_subq_contributor = count_subq(Preprint.objects.filter(_contributors=OuterRef('pk'), is_public=True, is_published=True, deleted__isnull=True, machine_state='withdrawn'))

    # main queryset
    qs = OSFUser.objects.filter(date_confirmed__gte=start).annotate(
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
        withdrawn_preprints_contributor=Subquery(withp_subq_contributor),
        node_last_action=Subquery(node_last_subq),
        preprint_last_action=Subquery(preprint_last_subq)
    )

    total = qs.count()
    pbar = tqdm(total=total)

    # streaming write (no per-row DB hits)
    for u in qs.values(
        'id', 'guids___id', 'username', 'date_confirmed', 'date_last_login',
        'node_last_action', 'preprint_last_action',
        'public_projects_created', 'private_projects_created',
        'public_registrations_created', 'withdrawn_registrations_created', 'embargoed_registrations_created',
        'published_preprints_created', 'withdrawn_preprints_created',
        'public_projects_contributor', 'private_projects_contributor',
        'public_registrations_contributor', 'withdrawn_registrations_contributor', 'embargoed_registrations_contributor',
        'published_preprints_contributor', 'withdrawn_preprints_contributor',
        'social'
    ).iterator(chunk_size=1000):

        last_action = max(
            filter(None, [
                u['node_last_action'],
                u['preprint_last_action']
            ]),
            default=None
        )

        social = u.get('social') or {}

        row = {
            'u._id': u['guids___id'],
            'u.username': u['username'],
            'u.date_confirmed': u['date_confirmed'].date().isoformat() if u['date_confirmed'] else None,
            'u.date_last_login': u['date_last_login'].date().isoformat() if u['date_last_login'] else None,
            'u.date_last_action': last_action.date().isoformat() if last_action else None,
            'u.academiaInstitution': social.get('academiaInstitution', ''),
            'u.academiaProfileID': social.get('academiaProfileID', ''),
            'u.baiduScholar': social.get('baiduScholar', ''),
            'u.github': social.get('github', []),
            'u.impactStory': social.get('impactStory', ''),
            'u.linkedIn': social.get('linkedIn', []),
            'u.profileWebsites': social.get('profileWebsites', []),
            'u.researchGate': social.get('researchGate', ''),
            'u.researcherId': social.get('researcherId', ''),
            'u.scholar': social.get('scholar', ''),
            'u.ssrn': social.get('ssrn', ''),
            'u.twitter': social.get('twitter', []),
            **{k: u.get(k) for k in fieldnames if k in u},
        }

        writer.writerow(row)
        pbar.update()

    pbar.close()

    with open(filename, 'w') as f:
        f.write(output.getvalue())

    print(f"Output written to {filename}")