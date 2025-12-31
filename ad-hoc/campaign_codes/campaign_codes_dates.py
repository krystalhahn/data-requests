def get_campaign_codes_and_dates():
    import io
    import csv
    from tqdm import tqdm
    from django.db.models import Case, When, Value, CharField
    import re
    filename = f'/tmp/campaign_codes_dates.csv'
    fieldnames = ['campaign', 'source_claimed', 'user_count','most_recent_user_created', 'abstractnode_count', 'most_recent_abstractnode_created', 
        'project_count', 'most_recent_project_created', 'registration_count', 'most_recent_registration_created', 
        'preprint_count', 'most_recent_preprint_created', 'draftregistration_count', 'most_recent_draftregistration_created', 
        'basefilenode_count', 'most_recent_basefilenode_created','outcome_count', 'most_recent_outcome_created']
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()

    campaigns = ['erp_challenge', 'osf_registered_reports', 'osf4m', 'agu_conference_2023', 'agu_conference']

    pbar = tqdm(total=len(campaigns))

    for campaign in campaigns:
        campaign_regex = rf'^(source|claimed):campaign\|{re.escape(campaign)}$'
        tags = Tag.all_tags.filter(system=True, name__regex=campaign_regex).annotate(
            source_claimed=Case(
                When(name__startswith='source', then=Value('source')),
                When(name__startswith='claimed', then=Value('claimed')),
                default=Value('other'),
                output_field=CharField()
            ),
            most_recent_user_created=Max('osfuser__date_confirmed'),
            most_recent_abstractnode_created=Max('abstractnode_tagged__created'),
            most_recent_project_created=Max('abstractnode_tagged__created', filter=Q(abstractnode_tagged__type='osf.node')),
            most_recent_registration_created=Max('abstractnode_tagged__created', filter=Q(abstractnode_tagged__type='osf.registration')),
            most_recent_preprint_created=Max('preprint_tagged__created'),
            most_recent_draftregistration_created=Max('draftregistration_tagged__created'),
            most_recent_basefilenode_created=Max('basefilenode_tagged__created'),
            most_recent_outcome_created=Max('outcome_tagged__created')
        )

        for tag in tags:
            writer.writerow({
                'campaign': campaign,
                'source_claimed': tag.source_claimed,
                'user_count': tag.osfuser_set.count(),
                'abstractnode_count': tag.abstractnode_tagged.count(),
                'project_count': tag.abstractnode_tagged.filter(type='osf.node').count(),
                'registration_count': tag.abstractnode_tagged.filter(type='osf.registration').count(),
                'preprint_count': tag.preprint_tagged.count(),
                'draftregistration_count': tag.draftregistration_tagged.count(),
                'basefilenode_count': tag.basefilenode_tagged.count(),
                'outcome_count': tag.outcome_tagged.count(),
                'most_recent_project_created': tag.most_recent_project_created or 'N/A',
                'most_recent_registration_created': tag.most_recent_registration_created or 'N/A',
                'most_recent_preprint_created': tag.most_recent_preprint_created or 'N/A',
                'most_recent_draftregistration_created': tag.most_recent_draftregistration_created or 'N/A',
                'most_recent_basefilenode_created': tag.most_recent_basefilenode_created or 'N/A',
                'most_recent_outcome_created': tag.most_recent_outcome_created or 'N/A'
            })
        pbar.update(1)
        
    pbar.close()

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())