# number of public registrations on the OSF
# number of registrations with (at least 1) outputs in the related resources (data, code, materials) sections
# number of registrations with at least 1 outcome linked in the related resource paper section
# number of registrations with both an output and outcome linked (LOS)

def get_all_registry_reg():
    import csv
    import io
    from django.utils import timezone
    from osf.utils.outcomes import ArtifactTypes
    from osf.models import Identifier, OutcomeArtifact
    from tqdm import tqdm
    filename = '/tmp/all_registry_reg.csv'
    COL_HEADERS = ['reg_guid', 'author_guid', 'registry', 'template', 'date_registered', 'connected_outputs']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

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
            ).filter(finalized=True, deleted__isnull=True)
        
            for artifact in connected_artifacts:
                artifact_label = ARTIFACT_TYPE_LABELS.get(artifact.artifact_type, str(artifact.artifact_type))
                connected_resources.append(artifact_label)

        writer.writerow({
            'reg_guid': reg._id,
            'author_guid': reg.creator._id,
            'registry': reg.provider._id,
            'template': reg.registered_schema.all()[0].name,
            'date_registered': reg.registered_date.date().isoformat(),
            'connected_outputs': connected_resources
        })
        pbar.update()

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")