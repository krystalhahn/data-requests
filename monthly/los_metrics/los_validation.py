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

# incorporating refined artifacts (artifacts that were created and not deleted by cutoff date)
def get_all_reg_w_refined_artifacts(cutoff):
    import csv
    import io
    from django.utils import timezone
    from osf.utils.outcomes import ArtifactTypes
    from osf.models import Identifier, OutcomeArtifact
    from tqdm import tqdm
    import json
    filename = '/tmp/all_reg_w_refined_artifacts.csv'
    COL_HEADERS = ['reg_guid', 'author_guid', 'is_public', 'is_deleted', 'date_created', 'date_registered', 'moderation_state', 'retraction_state', 'spam_status', 
                   'registry', 'template', 'connected_outputs', 'institution', 'subject', 'subject_parent', 'funder', 'funder_identifier', 'funder_identifier_type']
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

        gmr = GuidMetadataRecord.objects.filter(guid___id=reg._id).first()
        funding_info = gmr.funding_info if gmr else []
        funders = [f['funder_name'] for f in funding_info] or None
        funder_identifiers = [f['funder_identifier'] for f in funding_info] or None
        funder_identifier_types = [f['funder_identifier_type'] for f in funding_info] or None

        writer.writerow({
            'reg_guid': reg._id,
            'is_public': reg.is_public,
            'is_deleted': reg.deleted is not None,
            'date_created': reg.created,
            'date_registered': reg.registered_date.date().isoformat(),
            'moderation_state': reg.moderation_state,
            'retraction_state': reg.retraction.state if reg.retraction else None,
            'spam_status': reg.spam_status,
            'author_guid': reg.creator._id,
            'registry': reg.provider._id,
            'template': reg.registered_schema.all()[0].name,
            'connected_outputs': connected_resources,
            'institution': json.dumps(list(reg.affiliated_institutions.values_list('name', flat=True)) if hasattr(reg, 'affiliated_institutions') else []),
            'subject': json.dumps(list(reg.subjects.filter(parent_id__isnull=False).values_list('text', flat=True)) if hasattr(reg, 'subjects') else []),
            'subject_parent': json.dumps(list(reg.subjects.filter(parent_id__isnull=True).values_list('text', flat=True)) if hasattr(reg, 'subjects') else []),
            'funder': json.dumps(funders) if funders else None,
            'funder_identifier': json.dumps(funder_identifiers) if funder_identifiers else None,
            'funder_identifier_type': json.dumps(funder_identifier_types) if funder_identifier_types else None,
        })
        pbar.update()

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")