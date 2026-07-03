def get_limbo_registrations():
    import csv
    import io
    from tqdm import tqdm

    filename = '/tmp/limbo_registrations.csv'
    COL_HEADERS = ['reg_guid', 'is_public', 'is_deleted', 'spam_status', 'date_created', 'date_registered', 
                   'moderation_state', 'embargo_state', 'embargo_end_date', 'retraction_state']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    regs = Registration.objects.select_related('embargo', 'retraction').all()

    pbar = tqdm(total=regs.count())

    for reg in regs.iterator(chunk_size=1000):
        writer.writerow({
            'reg_guid': reg._id,
            'is_public': reg.is_public,
            'is_deleted': reg.deleted is not None,
            'spam_status': reg.spam_status,
            'date_created': reg.created,
            'date_registered': reg.registered_date,
            'moderation_state': reg.moderation_state,
            'embargo_state': reg.embargo.state if reg.embargo else None,
            'embargo_end_date': reg.embargo.end_date if reg.embargo else None,
            'retraction_state': reg.retraction.state if reg.retraction else None,
        })
        pbar.update()

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")