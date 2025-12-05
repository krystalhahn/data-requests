def generate_cedar_metadata_csv():
    import csv
    import io
    from tqdm import tqdm
    from osf.utils.outcomes import ArtifactTypes

    filename = '/tmp/cedar_metadata.csv'
    COL_HEADERS = ['community_schema', 'type', 'resourceType', 'deleted', 'guid', 'title', 'created', 'subjects', 'institutions', 'hasConnectedResource', 'visible_contributors']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    # fetch all CedarMetadataRecord objects
    qs = CedarMetadataRecord.objects.all()

    pbar = tqdm(total=qs.count())

    for cmr in qs:
        # retrieve the GUID associated with the CedarMetadataRecord
        guid = cmr.guid

        # retrieve the associated GuidMetadataRecord through the metadata_record field
        gmr = getattr(guid, 'metadata_record', None)

        # retrieve the referent associated with the GUID
        ref = guid.referent

        # skip records based on privacy or publication status
        if hasattr(ref, 'is_public') and not ref.is_public:
            continue
        if ref.type == 'osf.preprint' and not ref.is_published:
            continue
        if 'file' in ref.type and not ref.target.is_public:
            continue

        # retrieve identifiers and artifacts
        idents = ref.identifiers.all() if 'file' not in ref.type else ref.target.identifiers.all()
        partifacts = sum([list(i.artifact_metadata.filter(artifact_type=ArtifactTypes.PRIMARY.value)) for i in idents], [])
        outcomes = [pa.outcome for pa in partifacts]

        # check for connected resources
        has_artifacts = any(
            o.artifact_metadata.exclude(artifact_type=ArtifactTypes.PRIMARY.value)
            .filter(finalized=True, deleted__isnull=True).exists() for o in outcomes
        )

        writer.writerow({
            'community_schema': cmr.template.schema_name, 
            'type': ref.type,
            'resourceType': getattr(gmr, 'resource_type_general', None),
            'deleted': ref.is_deleted,
            'guid': guid._id,
            'title': getattr(ref, 'title', None) or getattr(ref, 'name', None),
            'created': ref.created,
            'subjects': list(ref.subjects.values_list('text', flat=True)) if hasattr(ref, 'subjects') else [],
            'institutions': list(ref.affiliated_institutions.values_list('name', flat=True)) if hasattr(ref, 'affiliated_institutions') else [],
            'hasConnectedResource': has_artifacts,
            'visible_contributors': list(ref.contributor_set.filter(visible=True).values_list('user__guids___id', flat=True)) if hasattr(ref, 'contributor_set') else [],
        })

        pbar.update(1)
    pbar.close()

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")