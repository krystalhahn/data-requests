def get_registration_resources(cutoff):
    import csv
    import io
    import datetime
    from osf.utils.outcomes import ArtifactTypes
    from osf.models import Identifier, OutcomeArtifact
    from tqdm import tqdm
    import json
    filename = '/tmp/registration_resources.csv'
    COL_HEADERS = ['reg_guid', 'connected_output_types', 'connected_output_ids']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    cutoff_dt = datetime.datetime.fromisoformat(f"{cutoff}T00:00:00+00:00")

    target_regs = Registration.objects.filter(created__lte=cutoff_dt)

    pbar = tqdm(total=target_regs.count())

    for reg in target_regs.iterator(chunk_size=1000):
    
        idents = reg.identifiers.all() if not 'file' in reg.type else reg.target.identifiers.all()
        partifacts = sum([list(i.artifact_metadata.filter(artifact_type=ArtifactTypes.PRIMARY.value)) for i in idents], [])
        outcomes = [pa.outcome for pa in partifacts]

        resource_types = []
        resource_ids = []
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
                resource_types.append(artifact_label)

                artifact_id = artifact.id
                resource_ids.append(artifact_id)

        writer.writerow({
            'reg_guid': reg._id,
            'connected_output_types': resource_types,
            'connected_output_ids': resource_ids,
        })
        pbar.update()

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())