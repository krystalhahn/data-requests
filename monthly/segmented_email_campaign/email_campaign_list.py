def get_email_campaign_list(data_pull_date):
    import io
    import csv
    from osf.utils.outcomes import ArtifactTypes
    from django.db.models import Q
    from tqdm import tqdm
    from datetime import datetime
    import pytz
    from dateutil.relativedelta import relativedelta

    filename = '/tmp/segmented_email_campaign_list.csv'
    COL_HEADERS = ['user_guid', 'user_email']
    
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    # one year before data was pulled
    last_year_dt = datetime.fromisoformat(f"{data_pull_date}").replace(tzinfo=pytz.utc) - relativedelta(months=12)

    target_regs = Registration.objects.filter(is_public=True, created__lte=last_year_dt).exclude(moderation_state="withdrawn")

    # track users already written to avoid duplicates
    seen_users = set()

    pbar = tqdm(total = target_regs.count())

    for reg in target_regs.iterator(chunk_size=1000):

        # exclude registrations with connected outputs (data, code, materials, supplements)
        idents = reg.identifiers.all() if not 'file' in reg.type else reg.target.identifiers.all()
        partifacts = sum([list(i.artifact_metadata.filter(artifact_type=ArtifactTypes.PRIMARY.value)) for i in idents], [])
        outcomes = [pa.outcome for pa in partifacts]

        ARTIFACT_TYPE_LABELS = dict(ArtifactTypes.choices())
        
        has_non_paper_resource = False
        for o in outcomes:
            connected_artifacts = o.artifact_metadata.exclude(
                artifact_type=ArtifactTypes.PRIMARY.value
            ).filter(
                Q(finalized=True) &
                Q(deleted__isnull=True)
            )
            for artifact in connected_artifacts:
                artifact_label = ARTIFACT_TYPE_LABELS.get(artifact.artifact_type, str(artifact.artifact_type))
                if artifact_label != "PAPERS":
                    has_non_paper_resource = True
                    break
            if has_non_paper_resource:
                break

        if has_non_paper_resource:
            continue

        # filter contributors with admin + read + write permissions
        contributors = reg.contributors.distinct()

        for user in contributors:
            permissions = reg.get_permissions(user)

            if not {'admin', 'read', 'write'}.issubset(set(permissions)):
                continue

            if user._id in seen_users:
                continue

            seen_users.add(user._id)

            writer.writerow({
                'user_guid': user._id,
                'user_email': user.username,
            })

        pbar.update()
    
    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")