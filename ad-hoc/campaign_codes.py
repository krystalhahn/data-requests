# get counts of users and objects each campaign code is associated with
def get_campaign_codes():
    import io
    import csv
    from tqdm import tqdm
    from django.db.models import Case, When, Value, CharField
    import re

    filename = f'/tmp/campaign_codes.csv'
    fieldnames = ['campaign','source_claimed', 'user_count', 'abstractnode_count', 'project_count', 'registration_count', 'preprint_count', 'draftregistration_count', 'basefilenode_count', 'outcome_count']
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()
		
	# the 'agu_conference' tag seems to have been deprecated? No results for this
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
            )
        )

        for tag in tags:
            writer.writerow({
                'campaign': campaign,
                'source_claimed': tag.source_claimed, 
                'user_count': tag.osfuser_set.count(), 
                # abstractnode can either be projects and registrations, so 'abstractnode_count' is the total of 'project_count' and 'registration_count'
                'abstractnode_count': tag.abstractnode_tagged.count(), 
                'project_count': tag.abstractnode_tagged.filter(type='osf.node').count(),
                'registration_count': tag.abstractnode_tagged.filter(type='osf.registration').count(),
                'preprint_count': tag.preprint_tagged.count(),
                'draftregistration_count': tag.draftregistration_tagged.count(),
                # no basefilenodes with campaign code
                'basefilenode_count': tag.basefilenode_tagged.count(),
                'outcome_count': tag.outcome_tagged.count()
            })
        pbar.update(1)
        
    pbar.close()

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())