def get_target_creators():
    import io
    import csv
    from tqdm import tqdm

    from django.db.models.aggregates import Count
    from django.db.models.expressions import F, Func, Subquery
    from django.db.models import Value

    filename = '/tmp/target_creators.csv'
    fieldnames = ['creator_user_id', 'creator_guid', 'file_count', 'file_guids']
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    # collect file IDs & map to GUIDs for Aug–Sep 2025
    print("Collecting File GUIDs for Aug–Sep 2025…")

    file_guids_qs = Guid.objects.filter(
        content_type__model="basefilenode",
        created__year=2025,
        created__month__in=[8, 9],
    )

    file_ids = list(file_guids_qs.values_list("object_id", flat=True))
    print(f"Found {len(file_ids):,} file GUIDs.")

    # map file_id -> GUID
    file_guid_map = {g.object_id: g._id for g in file_guids_qs}

    # stream OsfStorageFile rows in batches
    print("Fetching OsfStorageFile rows in batches…")
    queryset = OsfStorageFile.objects.filter(id__in=file_ids).values(
        "id", "target_content_type_id", "target_object_id"
    )

    by_ct = defaultdict(list)
    for row in tqdm(queryset.iterator(chunk_size=5000), total=len(file_ids)):
        by_ct[row["target_content_type_id"]].append(row["target_object_id"])

    # resolve model classes for each content type
    print("Resolving content types…")
    ct_models = {ct.id: ct.model_class() for ct in ContentType.objects.filter(id__in=by_ct.keys())}

    # map creator_id → list of file IDs
    creator_to_files = defaultdict(list)

    # bulk resolve creators per target model
    print("Resolving target creators in bulk…")

    for ct_id, object_ids in by_ct.items():
        model = ct_models[ct_id]
        print(f"  - Processing {len(object_ids):,} objects from {model.__name__}")

        qs = model.objects.filter(id__in=object_ids).values("id", "creator_id")
        for row in tqdm(qs.iterator(chunk_size=5000), total=len(object_ids)):
            creator_id = row["creator_id"]
            if creator_id:
                creator_to_files[creator_id].append(row["id"])

    # fetch creator GUIDs in bulk
    print("Fetching creator GUIDs…")
    creator_qs = OSFUser.objects.filter(id__in=creator_to_files.keys()).values("id", "guids___id")
    creator_guid_map = {row["id"]: row["guids___id"] for row in creator_qs}

    # sort by file_count DESC
    print("Sorting creators by file_count…")
    sorted_creators = sorted(
        creator_to_files.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )

    print("Writing CSV rows…")
    for creator_id, file_ids in tqdm(sorted_creators):
        guid_list = [file_guid_map[file_id] for file_id in file_ids if file_id in file_guid_map]
        if not guid_list:
            continue  # skip creators with no files with GUIDs
        writer.writerow({
            "creator_user_id": creator_id,
            "creator_guid": creator_guid_map.get(creator_id),
            "file_count": len(guid_list),
            "file_guids": ",".join(guid_list),
        })

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")