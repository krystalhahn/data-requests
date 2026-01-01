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