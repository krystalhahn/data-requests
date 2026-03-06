# when there are associated GuidMetadataRecord objects
def get_metadata_objects(n=None):
    import csv
    import io
    from osf.utils.outcomes import ArtifactTypes
    from tqdm import tqdm

    filename = f'/tmp/objects_with_metadata.csv'
    COL_HEADERS = ['type', 'resourceType', 'guid', 'title', 'created', 
                   'subjects', 'region', 'institutions', 'funders', 
                   'has_connected_resource', 'connected_resources', 'has_all_resources', 
                   'visible_contributors']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    qs = GuidMetadataRecord.objects.all()[:n]

    pbar = tqdm(total=qs.count())

    for gmr in qs:
        
        # get referent object
        ref = gmr.guid.referent
        # skip private and unpublished objects
        if hasattr(ref, 'is_public') and not ref.is_public:
            continue
        if ref.type == 'osf.preprint' and not ref.is_published:
            continue
        if 'file' in ref.type and not ref.target.is_public:
            continue
        # extract identifiers and associated primary artifacts and associated outcomes
        idents = ref.identifiers.all() if not 'file' in ref.type else ref.target.identifiers.all()
        partifacts = sum([list(i.artifact_metadata.filter(artifact_type=ArtifactTypes.PRIMARY.value)) for i in idents], [])
        outcomes = [pa.outcome for pa in partifacts]
        # check for finalized, non-primary, non-deleted artifacts
        has_artifacts = any([o.artifact_metadata.exclude(artifact_type=ArtifactTypes.PRIMARY.value).filter(finalized=True, deleted__isnull=True).exists() for o in outcomes])
        # extract affiliated funders if available
        funder_names = [fi.get('funder_name') for fi in gmr.funding_info if isinstance(fi, dict) and fi.get('funder_name')] if gmr.funding_info else []

        # get artifact type dictionary
        ARTIFACT_TYPE_LABELS = dict(ArtifactTypes.choices())
        # designate required artifact types (to count towards 5 connected resources)
        required_types = {'DATA', 'ANALYTIC_CODE', 'MATERIALS', 'PAPERS', 'SUPPLEMENTS'}
        # initialize empty list of connected resources
        connected_resources = []
        # initalize `has_all_resources` value
        all_types_present = False
        # create empty set to collect unique artifact labels among connected artifacts
        artifact_labels = set()
        # iterate over each outcome associated with the metadata record
        for o in outcomes:
            connected_artifacts = o.artifact_metadata.exclude(
                artifact_type=ArtifactTypes.PRIMARY.value
            ).filter(finalized=True, deleted__isnull=True)
            
            
            for artifact in connected_artifacts:
                # add artifact label to `connected_resources` list
                artifact_label = ARTIFACT_TYPE_LABELS.get(artifact.artifact_type, str(artifact.artifact_type))
                connected_resources.append(artifact_label)
                artifact_labels.add(artifact_label)

            # check if all 5 required artifact types are present
            all_types_present = required_types.issubset(artifact_labels)

        writer.writerow({
            'type': ref.type,
            'resourceType': gmr.resource_type_general,
            'guid': gmr.guid._id,
            'title': getattr(ref, 'title', None) or getattr(ref, 'name', None),
            'created': ref.created,
            # get list of subjects/disciplines
            'subjects': list(ref.subjects.values_list('text', flat=True)) if hasattr(ref, 'subjects') else [],
            # get list of gstorageic regions
            'region': ref.addons_osfstorage_node_settings.region.name if hasattr(ref, 'addons_osfstorage_node_settings') else None,
            # get list of affiliated institutions
            'institutions': list(ref.affiliated_institutions.values_list('name', flat=True)) if hasattr(ref, 'affiliated_institutions') else [],
            'funders': funder_names,
            'has_connected_resource': has_artifacts,
            'connected_resources': connected_resources,
            'has_all_resources': all_types_present,
            'visible_contributors': list(ref.contributor_set.filter(visible=True).values_list('user__guids___id', flat=True)) if hasattr(ref, 'contributor_set') else [],
        })

        pbar.update()
    
    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")


# if no associated GuidMetadataRecord object, just get connected resources
# batched version because runtime was too long
def get_connected_reg(n=None):
    import csv
    from osf.utils.outcomes import ArtifactTypes
    from osf.models import Identifier, OutcomeArtifact
    from tqdm import tqdm
    from django.db.models import Prefetch

    filename = '/tmp/connected_reg.csv'
    COL_HEADERS = ['type', 'guid', 'title', 'created', 
                   'subjects', 'region', 'institutions', 
                   'has_connected_resource', 'connected_resources', 'has_all_resources']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    ARTIFACT_TYPE_LABELS = dict(ArtifactTypes.choices())
    REQUIRED_TYPES = {'DATA', 'ANALYTIC_CODE', 'MATERIALS', 'PAPERS', 'SUPPLEMENTS'}

    # prefetch subjects, institutions, artifacts
    qs = (
        Registration.objects.filter(is_public=True)
        .select_related('addons_osfstorage_node_settings__region')
        .prefetch_related('subjects','affiliated_institutions', Prefetch('identifiers', queryset=Identifier.objects.prefetch_related(Prefetch('artifact_metadata', queryset=OutcomeArtifact.objects.select_related('outcome')))))
    )

    if n:
        qs = qs[:n]

    total = qs.count()

    for reg in tqdm(qs.iterator(chunk_size=1000), total=total):
        partifacts = sum([
            list(i.artifact_metadata.filter(artifact_type=ArtifactTypes.PRIMARY.value))
            for i in reg.identifiers.all()
        ], [])
        outcomes = [pa.outcome for pa in partifacts if pa.outcome]
        connected_resources = []
        artifact_labels = set()

        for o in outcomes:
            connected_artifacts = [
                a for a in o.artifact_metadata.all()
                if a.artifact_type != ArtifactTypes.PRIMARY.value and a.finalized and a.deleted is None
            ]
            for artifact in connected_artifacts:
                label = ARTIFACT_TYPE_LABELS.get(artifact.artifact_type, str(artifact.artifact_type))
                connected_resources.append(label)
                artifact_labels.add(label)

        has_artifacts = bool(connected_resources)
        all_types_present = REQUIRED_TYPES.issubset(artifact_labels)

        writer.writerow({
            'type': reg.type,
            'guid': reg._id,
            'title': reg.title,
            'created': reg.created,
            'subjects': list(reg.subjects.values_list('text', flat=True)) if hasattr(reg, 'subjects') else [],
            'region': reg.addons_osfstorage_node_settings.region.name
                        if hasattr(reg, 'addons_osfstorage_node_settings') and reg.addons_osfstorage_node_settings.region else None,
            'institutions': list(reg.affiliated_institutions.values_list('name', flat=True)) if hasattr(reg, 'affiliated_institutions') else [],
            'has_connected_resource': has_artifacts,
            'connected_resources': connected_resources,
            'has_all_resources': all_types_present,
        })
        
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")