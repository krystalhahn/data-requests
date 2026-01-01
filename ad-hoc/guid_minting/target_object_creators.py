def get_target_creators(content_type, year, month):
    import csv
    from collections import defaultdict
    from tqdm import tqdm
    from django.contrib.contenttypes.models import ContentType

    filename = '/tmp/target_creators.csv'
    fieldnames = ['creator_user_id', 'creator_guid', 'file_count', 'file_guids']

    # open CSV for streaming write
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        print("Collecting file GUIDs for specified month(s)")
        file_guids_qs = Guid.objects.filter(
            content_type__model=content_type,
            created__year=year,
            created__month__in=month,
        )

        # map file_id -> GUID, streamed
        file_guid_map = {g.object_id: g._id for g in file_guids_qs.iterator(chunk_size=5000)}
        file_ids = list(file_guid_map.keys())
        print(f"Found {len(file_ids):,} file GUIDs.")

        # stream OsfStorageFile rows
        print("Fetching OsfStorageFile rows…")
        file_to_target = {}
        for f_row in OsfStorageFile.objects.filter(id__in=file_ids).values(
            'id', 'target_content_type_id', 'target_object_id'
        ).iterator(chunk_size=5000):
            file_to_target[f_row['id']] = (f_row['target_content_type_id'], f_row['target_object_id'])

        # group target IDs by content type
        ct_to_targets = defaultdict(set)
        for ct_id, target_id in file_to_target.values():
            ct_to_targets[ct_id].add(target_id)

        # resolve creators per content type in batches
        creator_to_file_guids = defaultdict(list)
        for ct_id, target_ids in ct_to_targets.items():
            model = ContentType.objects.get(id=ct_id).model_class()
            print(f"Processing {len(target_ids):,} targets for content type {model.__name__}…")
            for target in model.objects.filter(id__in=target_ids).values('id', 'creator_id').iterator(chunk_size=5000):
                target_id = target['id']
                creator_id = target['creator_id']
                if creator_id:
                    # find all files pointing to this target
                    for file_id, (f_ct_id, f_target_id) in file_to_target.items():
                        if f_ct_id == ct_id and f_target_id == target_id:
                            creator_to_file_guids[creator_id].append(file_guid_map[file_id])

        # fetch creator GUIDs in batches
        print("Fetching creator GUIDs…")
        creator_ids = list(creator_to_file_guids.keys())
        creator_guid_map = {}
        for user in OSFUser.objects.filter(id__in=creator_ids).values('id', 'guids___id').iterator(chunk_size=5000):
            creator_guid_map[user['id']] = user['guids___id']

        print("Writing CSV rows…")
        for creator_id, guid_list in tqdm(creator_to_file_guids.items()):
            writer.writerow({
                'creator_user_id': creator_id,
                'creator_guid': creator_guid_map.get(creator_id),
                'file_count': len(guid_list),
                'file_guids': ','.join(guid_list),
            })

    print(f"Output written to {filename}")
