# get available names and ORCIDs from NPS users
# pass arguments to pull inactive and spam users too
def write_nps_users_names_orcids(active_only=True, nonspam_only=True):
    import csv
    import io
    from django.db.models import Q
    from tqdm import tqdm

    filename = f'/tmp/nps_users_names_orcids.csv'
    fieldnames = ['u._id', 'u.username', 'u.fullname', 'u.given_name', 'u.middle_names', 'u.family_name', 'u.orcid', 'u.date_confirmed', 'u.is_active', 'u.is_spam', 'u.deleted']
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()

    filters = Q()
    if active_only:
        filters &= Q(is_active=True)
    if nonspam_only:
        filters &= ~Q(spam_status__in=[1,2])

    qs = OSFUser.objects.filter(filters)

    pbar = tqdm(total=qs.count())

    for udict in qs.values('guids___id', 'username', 'fullname', 'given_name', 'middle_names', 'family_name', 'external_identity', 'date_confirmed', 'is_active', 'spam_status', 'deleted'):
        # safely handle date_confirmed
        if 'date_confirmed' in udict and udict['date_confirmed'] is not None:
            try:
                udict['u.date_confirmed'] = udict.pop('date_confirmed').date().isoformat()
            except AttributeError:
                # if it’s not a datetime, just cast to string
                udict['u.date_confirmed'] = str(udict.pop('date_confirmed'))
        else:
            # remove it from dict entirely if it exists
            udict.pop('date_confirmed', None)
            udict['u.date_confirmed'] = None

        deleted_val = udict.pop('deleted', None)

        if deleted_val is not None:
            try:
                udict['u.deleted'] = deleted_val.date().isoformat()
            except AttributeError:
                udict['u.deleted'] = str(deleted_val)
        else:
            udict['u.deleted'] = None

        udict['u._id'] = udict.pop('guids___id')
        udict['u.username'] = udict.pop('username')
        udict['u.fullname'] = udict.pop('fullname')
        udict['u.given_name'] = udict.pop('given_name')
        udict['u.middle_names'] = udict.pop('middle_names')
        udict['u.family_name'] = udict.pop('family_name')
        udict['u.is_active'] = udict.pop('is_active')
        udict['u.is_spam'] = udict.pop('spam_status', None) in (1, 2)

        ext_id = udict.pop('external_identity', {})
        if 'ORCID' in ext_id and ext_id['ORCID']:
            udict['u.orcid'] = list(ext_id['ORCID'].keys())[0]  # take the first ORCID
        else:
            udict['u.orcid'] = None
        
        writer.writerow(udict)
        pbar.update()

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")