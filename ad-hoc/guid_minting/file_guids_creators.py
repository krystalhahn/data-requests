# at the GUID level
def inspect_file_guids(content_type, year, month):
    import csv
    import io
    from tqdm import tqdm
    
    filename = "/tmp/file_guids.csv"
    fieldnames = ['guid', 'file_guid', 'name', 'created', 'deleted', 'target_guid', 'target_creator']
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    file_guids_qs = Guid.objects.filter(
            content_type__model=content_type,
            created__year=year,
            created__month__in=month,
        ).select_related()
    
    pbar = tqdm(total = file_guids_qs.count())

    for guid in file_guids_qs.iterator(chunk_size=5000):
        file = guid.referent

        writer.writerow({
            "guid": guid._id,
            "file_guid": file._id,
            "name": file.name if file.name else None,
            "created": file.created,
            "deleted": file.deleted,
            "target_guid": file.target._id,
            "target_creator": file.target.creator._id
        })

        pbar.update()
    
    pbar.close()

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")

# at the file level
def inspect_file_guids_creators(content_type_model, year, month):
    import csv
    from collections import defaultdict
    from tqdm import tqdm
    from django.contrib.contenttypes.models import ContentType

    filename = '/tmp/file_guids_creators.csv'
    fieldnames = ['guid', 'file_guid', 'name', 'created', 'deleted', 'target_guid', 'target_creator', 'latest_version_creator', 'minted_version_creator']

    ct = ContentType.objects.get(model=content_type_model)

    # fetch file GUIDs
    file_guids_qs = Guid.objects.filter(
        content_type=ct,
        created__year=year,
        created__month__in=month,
    )

    file_guid_map = {g.object_id: g for g in file_guids_qs.iterator(chunk_size=5000)}
    file_ids = list(file_guid_map.keys())

    if not file_ids:
        print("No files found — exiting.")
        return

    print(f"Processing {len(file_ids):,} files…")

    # fetch file → target mappings
    file_rows = OsfStorageFile.objects.filter(id__in=file_ids).values(
        'id',
        'name',
        'created',
        'deleted',
        'target_content_type_id',
        'target_object_id',
    )

    file_to_target = {
        row['id']: row
        for row in file_rows.iterator(chunk_size=5000)
    }

    # group target IDs by content type
    ct_to_target_ids = defaultdict(set)
    for row in file_to_target.values():
        if row['target_content_type_id'] and row['target_object_id']:
            ct_to_target_ids[row['target_content_type_id']].add(
                row['target_object_id']
            )

    # resolve target GUID + creator GUID in bulk
    target_info_map = {}

    for ct_id, target_ids in ct_to_target_ids.items():
        model = ContentType.objects.get(id=ct_id).model_class()
        print(f"Resolving {len(target_ids):,} targets for {model.__name__}")

        qs = (
            model.objects
            .filter(id__in=target_ids)
            .select_related('creator')
            .prefetch_related('guids', 'creator__guids')
        )

        for obj in qs:
            target_guid = obj.guids.first()._id if obj.guids.exists() else None
            target_creator = (
                obj.creator.guids.first()._id
                if obj.creator and obj.creator.guids.exists()
                else None
            )

            target_info_map[(ct_id, obj.id)] = {
                'target_guid': target_guid,
                'target_creator': target_creator,
            }

    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for file_id, row in tqdm(
            file_to_target.items(),
            total=len(file_to_target),
        ):
            guid = file_guid_map[file_id]

            versions = list(
                FileVersion.objects
                .filter(basefilenode__id=file_id)
                .select_related('creator')
                .prefetch_related('creator__guids')
                .order_by('created')
            )

            latest_version = versions[-1] if versions else None
            latest_version_creator = (
                latest_version.creator.guids.first()._id
                if (
                    latest_version
                    and latest_version.creator
                    and latest_version.creator.guids.exists()
                )
                else None
            )

            minted_versions = [v for v in versions if v.created <= guid.created]
            minted_version = minted_versions[-1] if minted_versions else None
            minted_version_creator = (
                minted_version.creator.guids.first()._id
                if (
                    minted_version
                    and minted_version.creator
                    and minted_version.creator.guids.exists()
                )
                else None
            )

            ct_id = row['target_content_type_id']
            target_id = row['target_object_id']
            target_info = target_info_map.get((ct_id, target_id), {})

            writer.writerow({
                'guid': guid._id,
                'file_guid': row['id'],
                'name': row['name'],
                'created': row['created'],
                'deleted': row['deleted'],
                'target_guid': target_info.get('target_guid'),
                'target_creator': target_info.get('target_creator'),
                'latest_version_creator': latest_version_creator,
                'minted_version_creator': minted_version_creator,
            })

    print(f"Output written to {filename}")
