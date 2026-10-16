def get_institution_guids():
    import csv
    from tqdm import tqdm

    filename = '/tmp/institution_guids.csv'
    COL_HEADERS = ['institution', 'guid', 'type', 'date_created']

    institutions = Institution.objects.all()

    with open(filename, 'w') as writeFile:
        writer = csv.DictWriter(writeFile, fieldnames=COL_HEADERS)
        writer.writeheader()

        for institution in tqdm(
            institutions,
            desc='Processing institutions'
        ):
            node_rows = (
                institution.nodes
                .values_list('guids___id', 'type', 'created')
                .exclude(guids___id__isnull=True)
                .distinct()
            )

            for guid, node_type, date_created in node_rows:
                writer.writerow({
                    'institution': institution._id,
                    'guid': guid,
                    'type': node_type,
                    'date_created': date_created
                })

            preprint_guids = (
                institution.preprints
                .values_list('guids___id', 'created')
                .exclude(guids___id__isnull=True)
                .distinct()
            )

            for guid, date_created in preprint_guids:
                writer.writerow({
                    'institution': institution._id,
                    'guid': guid,
                    'type': 'osf.preprint',
                    'date_created': date_created
                })

    print(f'Output written to {filename}')