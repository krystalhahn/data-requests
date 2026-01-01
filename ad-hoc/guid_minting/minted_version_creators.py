# get creator of file version at the time of GUID creation in specified months
def get_version_creators_at_guid_creation(content_type, year, month):
    import csv
    from collections import defaultdict
    from tqdm import tqdm
    from django.db.models import OuterRef, Subquery, Count, F
    from django.contrib.contenttypes.models import ContentType

    filename = '/tmp/creators_at_guid_version.csv'
    fieldnames = ['creator_user_id', 'creator_guid', 'file_count', 'total_versions', 'file_guids']

    BATCH_SIZE = 50_000

    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        # collect file GUIDs minted in the specified month(s)
        print("Collecting file GUIDs for specified month(s)…")

        file_guids_qs = Guid.objects.filter(
            content_type__model=content_type,
            created__year=year,
            created__month__in=month,
        ).order_by('created')

        # map: OsfStorageFile.id -> list of GUID objects
        file_guid_map = defaultdict(list)
        for g in file_guids_qs.iterator(chunk_size=5000):
            file_guid_map[g.object_id].append(g)

        file_ids = list(file_guid_map.keys())
        print(f"Found {len(file_ids):,} file GUIDs.")

        if not file_ids:
            print("No files found — exiting.")
            return

        creator_to_stats = defaultdict(lambda: {'file_guids': [], 'total_versions': 0})

        # process files in chunks
        file_id_chunks = [
            file_ids[i:i + BATCH_SIZE]
            for i in range(0, len(file_ids), BATCH_SIZE)
        ]

        print(f"Processing {len(file_id_chunks)} chunks of files…")

        for chunk in tqdm(file_id_chunks):
            # fetch all versions for the chunk of files
            files_qs = OsfStorageFile.objects.filter(id__in=chunk).prefetch_related('versions__creator')

            for file in files_qs.iterator(chunk_size=1000):
                versions = list(file.versions.order_by('created'))
                if not versions:
                    continue

                for guid_obj in file_guid_map[file.id]:
                    # find the version created last **before or at** the GUID creation
                    version_at_guid_time = None
                    for v in reversed(versions):
                        if v.created <= guid_obj.created:
                            version_at_guid_time = v
                            break

                    if not version_at_guid_time or not version_at_guid_time.creator:
                        continue

                    creator_id = version_at_guid_time.creator.id
                    creator_to_stats[creator_id]['file_guids'].append(guid_obj._id)
                    creator_to_stats[creator_id]['total_versions'] += len(versions)

        print(f"Resolved creators for {len(creator_to_stats):,} users.")

        # resolve creator GUIDs
        print("Fetching creator GUIDs…")
        creator_ids = list(creator_to_stats.keys())

        creator_guid_map = {
            u['id']: u['guids___id']
            for u in OSFUser.objects.filter(id__in=creator_ids).values('id', 'guids___id')
        }

        print("Writing CSV rows…")
        for creator_id, stats in tqdm(creator_to_stats.items()):
            writer.writerow({
                'creator_user_id': creator_id,
                'creator_guid': creator_guid_map.get(creator_id),
                'file_count': len(stats['file_guids']),
                'total_versions': stats['total_versions'],
                'file_guids': ','.join(stats['file_guids']),
            })

    print(f"Output written to {filename}")
