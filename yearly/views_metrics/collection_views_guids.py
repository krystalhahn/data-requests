collections = ['embsi', 'fusf', 'ibdgc', 'iafns', 'uremethods']

def get_collection_guids(collections):
    import io
    import csv
    from tqdm import tqdm

    filename = '/tmp/collection_guids.csv'
    col_headers = ['collection', 'guid', 'title']

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=col_headers)
    writer.writeheader()

    target_collections = Collection.objects.filter(
        provider__in=CollectionProvider.objects.filter(
            _id__in=collections
        )
    )

    rows = []

    for collection in target_collections:
        guid_ids = set(
            collection.guids.values_list('_id', flat=True)
        )
        guid_ids.update(
            collection.guid_links.values_list('_id', flat=True)
        )

        for guid in Guid.objects.filter(_id__in=guid_ids):
            referent = guid.referent

            rows.append({
                'collection': collection.provider._id,
                'guid': guid._id,
                'title': referent.title if referent else None
            })

    for row in tqdm(rows):
        writer.writerow(row)

    with open(filename, 'w') as write_file:
        write_file.write(output.getvalue())

    print(f"Output written to {filename}")