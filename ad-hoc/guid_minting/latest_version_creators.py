# get creators of the latest version of file for which the GUID was minted in the specified months
# includes total version count to see if there are strange spikes in version counts for files a creator uploaded
def get_latest_version_creators(content_type, year, month):
    import csv
    from collections import defaultdict
    from tqdm import tqdm
    from django.db.models import OuterRef, Subquery, Count
    from django.contrib.contenttypes.models import ContentType

    filename = "/tmp/latest_version_creators.csv"
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
        )

        # map: OsfStorageFile.id -> short GUID
        file_guid_map = {
            g.object_id: g._id
            for g in file_guids_qs.iterator(chunk_size=5000)
        }

        file_ids = list(file_guid_map.keys())
        print(f"Found {len(file_ids):,} file GUIDs.")

        if not file_ids:
            print("No files found — exiting.")
            return

        # subquery: latest FileVersion creator per file
        latest_version_qs = (
            FileVersion.objects
            .filter(basefilenode=OuterRef('id'))
            .order_by('-created')
        )

        # subquery: count versions per file
        version_count_qs = (
            FileVersion.objects
            .filter(basefilenode=OuterRef('id'))
            .order_by()
            .values('basefilenode')
            .annotate(vc=Count('id'))
            .values('vc')
        )

        creator_to_stats = defaultdict(lambda: {'file_guids': [], 'total_versions': 0})

        # chunk file IDs to keep IN clauses reasonable
        file_id_chunks = [
            file_ids[i:i + BATCH_SIZE]
            for i in range(0, len(file_ids), BATCH_SIZE)
        ]

        print(f"Processing {len(file_id_chunks)} chunks of files…")

        # resolve latest-version creators and version counts (DB-side)
        for chunk in tqdm(file_id_chunks):
            files_with_latest = (
                OsfStorageFile.objects
                .filter(id__in=chunk)
                .annotate(
                    latest_creator_id=Subquery(
                        latest_version_qs.values('creator_id')[:1]
                    ),
                    version_count=Subquery(version_count_qs[:1])
                )
                .values('id', 'latest_creator_id', 'version_count')
            )

            for row in files_with_latest.iterator(chunk_size=5000):
                creator_id = row['latest_creator_id']
                if not creator_id:
                    continue

                creator_to_stats[creator_id]['file_guids'].append(file_guid_map[row['id']])
                creator_to_stats[creator_id]['total_versions'] += row['version_count'] or 0

        print(f"Resolved latest-version creators for {len(creator_to_stats):,} users.")

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
                'file_guids': ",".join(stats['file_guids']),
            })

    print(f"Output written to {filename}")
