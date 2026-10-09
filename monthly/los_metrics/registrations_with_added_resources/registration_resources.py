def get_registration_resources(cutoff):
    import csv
    import io
    import datetime
    from osf.utils.outcomes import ArtifactTypes
    from osf.models import Identifier, OutcomeArtifact
    from tqdm import tqdm
    import json
    filename = '/tmp/registration_resources.csv'
    COL_HEADERS = ['reg_guid', 'connected_resources']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    cutoff_dt = datetime.datetime.fromisoformat(f"{cutoff}T00:00:00+00:00")

    target_regs = Registration.objects.filter(created__lt=cutoff_dt)

    pbar = tqdm(total=target_regs.count())

    for reg in target_regs.iterator(chunk_size=1000):
    
        idents = reg.identifiers.all() if not 'file' in reg.type else reg.target.identifiers.all()
        partifacts = sum([list(i.artifact_metadata.filter(artifact_type=ArtifactTypes.PRIMARY.value)) for i in idents], [])
        outcomes = [pa.outcome for pa in partifacts]

        resource_list = []
        ARTIFACT_TYPE_LABELS = dict(ArtifactTypes.choices())
        for o in outcomes:
            connected_artifacts = o.artifact_metadata.exclude(
                artifact_type=ArtifactTypes.PRIMARY.value
            ).filter(
                Q(finalized=True) &
                Q(created__lte=cutoff_dt) &
                (Q(deleted__isnull=True) | Q(deleted__gt=cutoff_dt))
            )
            for artifact in connected_artifacts:
                artifact_label = ARTIFACT_TYPE_LABELS.get(artifact.artifact_type,  str(artifact.artifact_type))

                resource_list.append({
                    'id': artifact.id,
                    'type': artifact_label,
                })

        writer.writerow({
            'reg_guid': reg._id,
            'connected_resources': json.dumps(resource_list, default=str)
        })
        pbar.update()

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")

# pulling title, DOI, and type for resources of selected registrations
def get_added_resources(guid_list_path):
    import io
    import csv
    from osf.utils.outcomes import ArtifactTypes
    from tqdm import tqdm

    filename = '/tmp/added_resource_regs.csv'
    COL_HEADERS = ['reg_guid', 'date_created', 'date_modified', 
                   'creator_guid', 'creator_name', 'contributor_guid', 'contributor_name', 
                   'resource_id', 'resource_title', 'resource_doi', 'resource_type']

    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    with open(guid_list_path, newline='') as readFile:
        total_regs = sum(1 for _ in csv.DictReader(readFile))

    with open(guid_list_path, newline='') as readFile:
        reader = csv.DictReader(readFile)

        for row in tqdm(reader, total=total_regs, desc="Processing registrations..."):
            reg_guid = row['reg_guid']

            reg = Registration.objects.filter(
                guids___id=reg_guid
            ).first()

            idents = reg.identifiers.all() if not 'file' in reg.type else reg.target.identifiers.all()
            partifacts = sum([list(i.artifact_metadata.filter(artifact_type=ArtifactTypes.PRIMARY.value)) for i in idents], [])
            outcomes = [pa.outcome for pa in partifacts]
    
            ARTIFACT_TYPE_LABELS = dict(ArtifactTypes.choices())
            for o in outcomes:
                connected_artifacts = o.artifact_metadata.exclude(
                    artifact_type=ArtifactTypes.PRIMARY.value
                ).filter(
                    Q(finalized=True) &
                    (Q(deleted__isnull=True))
                    # Q(created__lte=cutoff_dt) &
                    # (Q(deleted__isnull=True) | Q(deleted__gt=cutoff_dt))
                )
                for artifact in connected_artifacts:

                    artifact_label = ARTIFACT_TYPE_LABELS.get(artifact.artifact_type,  str(artifact.artifact_type))

                    writer.writerow({
                        'reg_guid': reg_guid,
                        'date_created': reg.created,
                        'date_modified': reg.modified,
                        'creator_guid': reg.creator._id,
                        'creator_name': reg.creator.fullname,
                        'contributor_guid': '; '.join(reg.contributors.values_list('guids___id', flat=True)),
                        'contributor_name': '; '.join(reg.contributors.values_list('fullname', flat=True)),
                        'resource_title': o.title,
                        'resource_doi': artifact.identifier.value, 
                        'resource_type': artifact_label
                    })

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")