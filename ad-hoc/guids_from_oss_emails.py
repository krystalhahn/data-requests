# example usage
get_guids_from_oss_emails("/path/to/guid_list.csv")

def get_guids_from_oss_emails(guid_list_path):
    import csv
    import io
    from tqdm import tqdm

    oss_emails = []
    with open(guid_list_path, newline='') as mapfile:
        mapreader = csv.reader(mapfile, delimiter=',', quotechar='"')
        next(mapreader)
        for row in mapreader:
            if row:
                oss_emails.append(row[0].strip().lower())

    filename = '/tmp/guids_from_oss_emails.csv'
    COL_HEADERS = ['email', 'u._id', 'u.username', 'u.fullname', 'u.given_name', 'u.middle_names', 'u.family_name']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    pbar = tqdm(total=len(oss_emails))

    for oss_email in oss_emails:
        try:
            email = Email.objects.get(address=oss_email)

            user = email.user

            writer.writerow({
                'email': oss_email,
                'u._id': user._id,
                'u.username': user.username,
                'u.fullname': user.fullname,
                'u.given_name': user.given_name,
                'u.middle_names': user.middle_names,
                'u.family_name': user.family_name
            })
        except Email.DoesNotExist:
            writer.writerow({
                'email': oss_email,
                'u._id': None,
                'u.username': None,
                'u.fullname': None,
                'u.given_name': None,
                'u.middle_names': None,
                'u.family_name': None
            })
        pbar.update()

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")