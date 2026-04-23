def get_user_reg_pairs(data_pull_date):
    import io
    import csv
    from osf.utils.outcomes import ArtifactTypes
    from django.db.models import Q
    from tqdm import tqdm
    from datetime import datetime
    import pytz
    from dateutil.relativedelta import relativedelta

    filename = '/tmp/segmented_email_campaign_user_reg_pairs.csv'
    COL_HEADERS = ['user_guid', 'user_email', 'user_permissions', 'reg_guid', 'date_created', 'date_registered', 'moderation_state', 'connected_resources']
    
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    # one year before data was pulled
    last_year_dt = datetime.fromisoformat(f"{data_pull_date}").replace(tzinfo=pytz.utc) - relativedelta(months=12)

    target_regs = Registration.objects.filter(is_public=True, created__lte=last_year_dt).exclude(moderation_state="withdrawn")

    pbar = tqdm(total = target_regs.count())

    for reg in target_regs.iterator(chunk_size=1000):
        contributors = reg.contributors.distinct()

        idents = reg.identifiers.all() if not 'file' in reg.type else reg.target.identifiers.all()
        partifacts = sum([list(i.artifact_metadata.filter(artifact_type=ArtifactTypes.PRIMARY.value)) for i in idents], [])
        outcomes = [pa.outcome for pa in partifacts]

        connected_resources = []
        ARTIFACT_TYPE_LABELS = dict(ArtifactTypes.choices())
        for o in outcomes:
            connected_artifacts = o.artifact_metadata.exclude(
                artifact_type=ArtifactTypes.PRIMARY.value
            ).filter(
                Q(finalized=True) &
                Q(deleted__isnull=True)
            )
            for artifact in connected_artifacts:
                artifact_label = ARTIFACT_TYPE_LABELS.get(artifact.artifact_type,  str(artifact.artifact_type))
                connected_resources.append(artifact_label)

        for user in contributors: 
            writer.writerow({
            'user_guid': user._id,
            'user_email': user.username,
            'user_permissions': reg.get_permissions(user),
            'reg_guid': reg._id,
            'date_created': reg.created,
            'date_registered': reg.registered_date,
            'moderation_state': reg.moderation_state,
            'connected_resources': connected_resources
        })
            
        pbar.update()

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")