# Added date of last login, date of last action, and separate counts for objects in which user is creator or contributor
# Needs to be merged with output of write_nps_users_insts() below: see merge_nps_users_insts() below

import io
import csv
from tqdm import tqdm

from django.db.models.aggregates import Count
from django.db.models.expressions import F, Func, Subquery

from osf.models import OSFUser, Node, Registration, Preprint

def write_nps_users_csv(n=None):
    filename = f'/tmp/nps_users.csv'
    fieldnames = ['u._id', 'u.username', 'u.date_confirmed', 'u.date_last_login', 'u.date_last_action', 'public_projects_created', 'private_projects_created', 'public_registrations_created', 'withdrawn_registrations_created', 'embargoed_registrations_created', 'published_preprints_created', 'withdrawn_preprints_created', 'public_projects_contributor', 'private_projects_contributor', 'public_registrations_contributor', 'withdrawn_registrations_contributor', 'embargoed_registrations_contributor', 'published_preprints_contributor', 'withdrawn_preprints_contributor']
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()
    
    # subqueries for project and registration counts
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
    
    # main user query with annotations
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
    
    for udict in qs.values('guids___id', 'username', 'date_confirmed', 'date_last_login', 'public_projects_created', 'private_projects_created', 'public_registrations_created', 'withdrawn_registrations_created', 'embargoed_registrations_created', 'published_preprints_created', 'withdrawn_preprints_created', 'public_projects_contributor', 'private_projects_contributor', 'public_registrations_contributor', 'withdrawn_registrations_contributor', 'embargoed_registrations_contributor', 'published_preprints_contributor', 'withdrawn_preprints_contributor'):
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
        
        # calculate the date of last action (-created for descending order)
        user_id = udict['u._id']
        last_log_action = OSFUser.objects.get(guids___id=user_id).logs.order_by('-created').first()
        last_preprint_action = OSFUser.objects.get(guids___id=user_id).preprint_logs.order_by('-created').first()
        
        # determine the latest action date between last log and preprint_log
        last_action = None
        if last_log_action and last_preprint_action:
            last_action = max(last_log_action.created, last_preprint_action.created)
        elif last_log_action:
            last_action = last_log_action.created
        elif last_preprint_action:
            last_action = last_preprint_action.created

        udict['u.date_last_action'] = last_action.date().isoformat() if last_action else None

        writer.writerow(udict)
        pbar.update()
    
    pbar.close()
    
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())
        
    print(f"Output written to {filename}")