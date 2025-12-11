# Original version
######## NPS Users V3 (2024) including requested date of last login
# u._id
# u.username
# u.date_confirmed
# u.date_last_login
# public_projects
# private_projects
# public_registrations
# withdrawn_registrations
# embargoed_registrations
# published_preprints
# withdrawn_preprints
#####################

import io
import csv
from tqdm import tqdm

from django.db.models.aggregates import Count
from django.db.models.expressions import F, Func, Subquery

from osf.models import OSFUser


def write_nps_users_csv(n=None):
    filename = f'/tmp/nps_users.csv'
    fieldnames = ['u._id', 'u.username', 'u.date_confirmed', 'u.date_last_login', 'public_projects', 'private_projects', 'public_registrations', 'withdrawn_registrations', 'embargoed_registrations', 'published_preprints', 'withdrawn_preprints']
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()
    pubn_subq = Node.objects.filter(creator_id=OuterRef('pk'), is_public=True, deleted__isnull=True).annotate(count=Func(F('id'), function='Count')).values('count')
    privn_subq = Node.objects.filter(creator_id=OuterRef('pk'), is_public=False, deleted__isnull=True).annotate(count=Func(F('id'), function='Count')).values('count')
    pubr_subq = Registration.objects.filter(creator_id=OuterRef('pk'), is_public=True, deleted__isnull=True).exclude(retraction__state='approved').annotate(count=Func(F('id'), function='Count')).values('count')
    withr_subq = Registration.objects.filter(creator_id=OuterRef('pk'), is_public=True, deleted__isnull=True, retraction__state='approved').annotate(count=Func(F('id'), function='Count')).values('count')
    embr_subq = Registration.objects.filter(creator_id=OuterRef('pk'), is_public=False, deleted__isnull=True, embargo__state='approved').annotate(count=Func(F('id'), function='Count')).values('count')
    pubp_subq = Preprint.objects.filter(creator_id=OuterRef('pk'), is_public=True, is_published=True, deleted__isnull=True).exclude(machine_state='withdrawn').annotate(count=Func(F('id'), function='Count')).values('count')
    withp_subq = Preprint.objects.filter(creator_id=OuterRef('pk'), is_public=True, is_published=True, deleted__isnull=True, machine_state='withdrawn').annotate(count=Func(F('id'), function='Count')).values('count')
    qs = OSFUser.objects.filter(is_active=True).exclude(spam_status__in=[1,2]).annotate(
        public_projects=Subquery(pubn_subq),
        private_projects=Subquery(privn_subq),
        public_registrations=Subquery(pubr_subq),
        withdrawn_registrations=Subquery(withr_subq),
        embargoed_registrations=Subquery(embr_subq),
        published_preprints=Subquery(pubp_subq),
        withdrawn_preprints=Subquery(withp_subq)
    )
    if n:
        qs = qs[:n]
    pbar = tqdm(total=qs.count())
    for udict in qs.values('guids___id', 'username', 'date_confirmed', 'date_last_login', 'public_projects', 'private_projects', 'public_registrations', 'withdrawn_registrations', 'embargoed_registrations', 'published_preprints', 'withdrawn_preprints'):
        try:
            udict['u.date_confirmed'] = udict.pop('date_confirmed').date().isoformat()
        except Exception:
            udict['u.date_confirmed'] = udict.pop('date_confirmed')
        if udict['date_last_login'] is not None:
            udict['u.date_last_login'] = udict.pop('date_last_login').date().isoformat()
        else:
            udict['u.date_last_login'] = udict.pop('date_last_login')
        udict['u._id'] = udict.pop('guids___id')
        udict['u.username'] = udict.pop('username')
        writer.writerow(udict)
        pbar.update()
    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())