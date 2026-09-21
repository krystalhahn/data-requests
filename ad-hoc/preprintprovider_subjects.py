def get_preprintprovider_subjects(provider):
    import csv
    import io
    from tqdm import tqdm
    import json
    filename = f'/tmp/{provider}_preprint_subjects.csv'
    COL_HEADERS = ['preprint_guid', 'preprint_provider', 'subjects']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    target_ps = Preprint.objects.filter(provider___id=provider)

    pbar = tqdm(total=target_ps.count())

    for p in target_ps:

        writer.writerow({
            'preprint_guid': p._id,
            'preprint_provider': p.provider._id,
            'subjects': json.dumps(list(p.subjects.values_list('text', flat=True)) if hasattr(p, 'subjects') else []),
        })
        pbar.update()

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")