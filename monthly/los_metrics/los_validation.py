def get_refined_artifacts(cutoff):
    import csv
    import io
    from django.utils import timezone
    import datetime
    from osf.utils.outcomes import ArtifactTypes
    from osf.models import Identifier, OutcomeArtifact
    from tqdm import tqdm
    from django.db.models import Q
    
    filename = '/tmp/refined_artifacts.csv'
    COL_HEADERS = ['reg_guid', 'author_guid', 'connected_outputs']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    cutoff_dt = timezone.make_aware(
        datetime.datetime.strptime(cutoff, "%Y-%m-%d"),
        timezone.get_fixed_timezone(-300)
    )

    target_regs = Registration.objects.all()

    pbar = tqdm(total=target_regs.count())

    for reg in target_regs.iterator(chunk_size=1000):
    
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
                Q(created__lte=cutoff_dt) &
                (Q(deleted__isnull=True) | Q(deleted__gt=cutoff_dt))
            )
            for artifact in connected_artifacts:
                artifact_label = ARTIFACT_TYPE_LABELS.get(artifact.artifact_type,  str(artifact.artifact_type))
                connected_resources.append(artifact_label)

        writer.writerow({
            'reg_guid': reg._id,
            'author_guid': reg.creator._id,
            'connected_outputs': connected_resources,
        })
        pbar.update()

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")