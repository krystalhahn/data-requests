# example argument
provider = PreprintProvider.objects.get(name = 'PsyArXiv')

def get_ppp_preprint_statuses_messages(provider, n=None):
    import csv
    import io
    from tqdm import tqdm

    filename = f'/tmp/{provider._id}_preprint_statuses_messages.csv'
    COL_HEADERS = ['preprint_guid_ver', 'preprint_guid', 'preprint_version', 'machine_state', 'date_created', 'date_published', 'moderation_messages', 'moderator_info', 'message_count']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    preprints = Preprint.objects.filter(provider=provider).distinct()

    if n:
        preprints = preprints[:n]

    pbar = tqdm(total=preprints.count())

    for p in preprints:

        preprint_guid = p._id.split('_')[0]
        preprint_version = p._id.split('_')[1]

        comment_actions = p.actions.filter(comment__isnull=False).exclude(comment='')
        comments_text = '\n---\n'.join([c.comment for c in comment_actions])
        commenter_info = '\n---\n'.join([f"{c.creator.fullname} ({c.creator._id})" for c in comment_actions])

        writer.writerow({
            'preprint_guid_ver': p._id,
            'preprint_guid': preprint_guid,
            'preprint_version': preprint_version,
            'machine_state': p.machine_state,
            'date_created': p.created.date().isoformat() if p.created else None,
            'date_published': p.date_published.date().isoformat() if p.date_published else None,
            'moderation_messages': comments_text,
            'moderator_info': commenter_info,
            'message_count': comment_actions.count()
        })
        pbar.update()

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")

# handles preprints in which the GUID is NA
# "Based on the timing... these are both rejected versions"
def get_ppp_preprint_statuses_messages(provider, n=None):
    import csv
    import io
    from tqdm import tqdm

    filename = f'/tmp/{provider._id}_preprint_statuses_messages.csv'
    COL_HEADERS = ['preprint_guid_ver', 'preprint_guid', 'preprint_version', 'machine_state', 'date_created', 'date_published', 'moderation_messages', 'moderator_info', 'message_count']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    preprints = Preprint.objects.filter(provider=provider).distinct()

    if n:
        preprints = preprints[:n]

    pbar = tqdm(total=preprints.count())

    for p in preprints:

        if p._id:
            preprint_guid_ver = p._id
            preprint_guid = p._id.split('_')[0]
            preprint_version = p._id.split('_')[1]
        else:
            preprint_guid_ver = None
            preprint_guid = None
            preprint_version = None

        comment_actions = p.actions.filter(comment__isnull=False).exclude(comment='')
        comments_text = '\n---\n'.join([c.comment for c in comment_actions])
        commenter_info = '\n---\n'.join([f"{c.creator.fullname} ({c.creator._id})" for c in comment_actions])

        writer.writerow({
            'preprint_guid_ver': preprint_guid_ver,
            'preprint_guid': preprint_guid,
            'preprint_version': preprint_version,
            'machine_state': p.machine_state,
            'date_created': p.created.date().isoformat() if p.created else None,
            'date_published': p.date_published.date().isoformat() if p.date_published else None,
            'moderation_messages': comments_text,
            'moderator_info': commenter_info,
            'message_count': comment_actions.count()
        })
        pbar.update()

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")