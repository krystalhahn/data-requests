def get_new_confirmed_users(start):
    import io
    import csv
    from tqdm import tqdm
    from django.db.models import OuterRef, Subquery, F, Func
    from osf.models import OSFUser, Node, Registration, Preprint, NodeLog, PreprintLog

    filename = '/tmp/new_confirmed_users.csv'

    account_fields = [
        'fullname', 'given_name', 'middle_names', 'family_name',
        'orcid', 'is_active', 'is_spam', 'deleted'
    ]

    social_fields = [
        'academiaInstitution', 'academiaProfileID', 'baiduScholar',
        'github', 'impactStory', 'linkedIn', 'profileWebsites',
        'researchGate', 'researcherId', 'scholar', 'ssrn', 'twitter'
    ]

    activity_fields = [
        'public_projects_created', 'private_projects_created',
        'public_registrations_created', 'withdrawn_registrations_created', 'embargoed_registrations_created',
        'published_preprints_created', 'withdrawn_preprints_created',
        'public_projects_contributor', 'private_projects_contributor',
        'public_registrations_contributor', 'withdrawn_registrations_contributor', 'embargoed_registrations_contributor',
        'published_preprints_contributor', 'withdrawn_preprints_contributor'
    ]

    fieldnames = (
        ['u._id', 'u.username', 'u.date_confirmed', 'u.date_last_login',
         'u.date_last_action']
        + [f'u.{field}' for field in social_fields]
        + account_fields
        + [f'u.{field}' for field in account_fields]
    )

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()

    start_y, start_m, start_d = map(int, start.split('-'))
    start = timezone.datetime(start_y, start_m, start_d, tzinfo=pytz.utc)

    def format_date(value):
        return value.date().isoformat() if value else None

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

    def count_subq(qs):
        return qs.annotate(
            count=Func(F('id'), function='Count')
        ).values('count')

    count_subqueries = {
        'pubn_subq_created': count_subq(Node.objects.filter(creator_id=OuterRef('pk'), is_public=True, deleted__isnull=True)), 
        'privn_subq_created': count_subq(Node.objects.filter(creator_id=OuterRef('pk'), is_public=False, deleted__isnull=True)),
        'pubr_subq_created': count_subq(Registration.objects.filter(creator_id=OuterRef('pk'), is_public=True, deleted__isnull=True).exclude(retraction__state='approved')),
        'withr_subq_created': count_subq(Registration.objects.filter(creator_id=OuterRef('pk'), is_public=True, deleted__isnull=True, retraction__state='approved')), 
        'embr_subq_created': count_subq(Registration.objects.filter(creator_id=OuterRef('pk'), is_public=False, deleted__isnull=True, embargo__state='approved')), 
        'pubp_subq_created': count_subq(Preprint.objects.filter(creator_id=OuterRef('pk'), is_public=True, is_published=True, deleted__isnull=True).exclude(machine_state='withdrawn')), 
        'withp_subq_created': count_subq(Preprint.objects.filter(creator_id=OuterRef('pk'), is_public=True, is_published=True, deleted__isnull=True, machine_state='withdrawn')), 
        'pubn_subq_contributor': count_subq(Node.objects.filter(_contributors=OuterRef('pk'), is_public=True, deleted__isnull=True)), 
        'privn_subq_contributor': count_subq(Node.objects.filter(_contributors=OuterRef('pk'), is_public=False, deleted__isnull=True)), 
        'pubr_subq_contributor': count_subq(Registration.objects.filter(_contributors=OuterRef('pk'), is_public=True, deleted__isnull=True).exclude(retraction__state='approved')), 
        'withr_subq_contributor': count_subq(Registration.objects.filter(_contributors=OuterRef('pk'), is_public=True, deleted__isnull=True, retraction__state='approved')), 
        'embr_subq_contributor': count_subq(Registration.objects.filter(_contributors=OuterRef('pk'), is_public=False, deleted__isnull=True, embargo__state='approved')), 
        'pubp_subq_contributor': count_subq(Preprint.objects.filter(_contributors=OuterRef('pk'), is_public=True, is_published=True, deleted__isnull=True).exclude(machine_state='withdrawn')),
        'withp_subq_contributor': count_subq(Preprint.objects.filter(_contributors=OuterRef('pk'), is_public=True, is_published=True, deleted__isnull=True, machine_state='withdrawn'))
    }

    annotations = {
        field: Subquery(subquery)
        for field, subquery in count_subqueries.items()
    }

    qs = OSFUser.objects.filter(
        date_confirmed__gte=start
    ).annotate(
        **annotations,
        node_last_action=Subquery(node_last_subq),
        preprint_last_action=Subquery(preprint_last_subq)
    )

    total = qs.count()
    pbar = tqdm(total=total)

    values_fields = [
        'id', 'guids___id', 'username', 'date_confirmed', 'date_last_login', 'node_last_action', 'preprint_last_action',
        'social', 'fullname', 'given_name', 'middle_names', 'family_name', 'external_identity',
        'is_active', 'spam_status', 'deleted'
    ] + activity_fields

    for u in qs.values(*values_fields).iterator(chunk_size=1000):

        last_action = max(
            filter(None, [
                u['node_last_action'],
                u['preprint_last_action']
            ]),
            default=None
        )

        # social profiles
        social = u.get('social') or {}

        # ORCID
        ext_id = u.get('external_identity') or {}
        orcid_data = ext_id.get('ORCID') or {}
        orcid = next(iter(orcid_data), None)

        # account information
        row = {
            'u._id': u['guids___id'],
            'u.username': u['username'],
            'u.date_confirmed': format_date(u['date_confirmed']),
            'u.date_last_login': format_date(u['date_last_login']),
            'u.date_last_action': format_date(last_action),

            # social profiles
            **{
                f'u.{field}': social.get(
                    field,
                    [] if field in ('github', 'linkedIn', 'profileWebsites', 'twitter') else ''
                )
                for field in social_fields
            },

            # activity counts
            **{
                field: u.get(field)
                for field in count_fields
            },

            # account information
            'u.fullname': u['fullname'],
            'u.given_name': u['given_name'],
            'u.middle_names': u['middle_names'],
            'u.family_name': u['family_name'],
            'u.orcid': orcid,
            'u.is_active': u['is_active'],
            'u.is_spam': u['spam_status'] in (1, 2),
            'u.deleted': format_date(u['deleted'])
        }

        writer.writerow(row)
        pbar.update()

    pbar.close()

    with open(filename, 'w') as f:
        f.write(output.getvalue())

    print(f"Output written to {filename}")

# Get institutional affiliations when available
import io
import csv
from tqdm import tqdm

from django.db.models.aggregates import Count
from django.db.models.expressions import F, Func, Subquery
from django.db.models import Value

from osf.models import OSFUser, Institution

def write_nps_users_insts(n=None):
    filename = f'/tmp/nps_users_insts.csv'
    fieldnames = ['u._id', 'u.username','institution_name']
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()

    insts = Institution.objects.all()

    pbar = tqdm(total=insts.count())

    for i in insts:
        qs = OSFUser.objects.filter(
            institutionaffiliation__institution__id=i.id,
            is_active=True
        ).exclude(spam_status__in=[1,2]).annotate(
            institution_name=Value(i.name)
        )
        
        if n:
            qs = qs[:n]

        for udict in qs.values('guids___id', 'username', 'institution_name'):
            udict['u._id'] = udict.pop('guids___id')
            udict['u.username'] = udict.pop('username')
            udict['institution_name'] = udict.pop('institution_name')

            writer.writerow(udict)
        
        pbar.update(1)
    pbar.close()

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")