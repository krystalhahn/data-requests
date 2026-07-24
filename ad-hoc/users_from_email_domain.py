def get_users_from_email_domain(descriptor, domains):
    import io
    import csv
    from tqdm import tqdm

    filename = f'/tmp/{descriptor}_email_domain_users.csv'
    fieldnames = ['user_id', 'primary_email_address', 'all_emails']
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()

    if len(domains) == 1:
        emails = Email.objects.filter(address__contains=domains).select_related('user').distinct()
    else:
        email_query = Q()
        for domain in domains:
            email_query |= Q(address__icontains=domain)

        emails = Email.objects.filter(email_query).select_related('user').distinct()

    user_ids = emails.values_list('user_id', flat=True).distinct()
    users = OSFUser.objects.filter(id__in=user_ids)

    pbar = tqdm(total = users.count())

    for u in users:
        writer.writerow({
            'user_id': u._id,
            'primary_email_address': u.username,
            'all_emails': ', '.join(u.emails.values_list('address', flat=True))
        })
        pbar.update()

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"CSV file saved to {filename}")

def get_users_from_primary_email_domain(descriptor, domains):
    import io
    import csv
    from tqdm import tqdm

    filename = f'/tmp/{descriptor}_primary_email_domain_users.csv'
    fieldnames = ['user_id', 'primary_email_address', 'all_emails']
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()
    
    for domain in domains:
        users = OSFUser.objects.filter(username__contains=domain).distinct()

        pbar = tqdm(total = users.count())

        for u in users:
            writer.writerow({
                'user_id': u._id,
                'primary_email_address': u.username,
                'all_emails': ', '.join(u.emails.values_list('address', flat=True))
            })
            pbar.update()

        pbar.close()

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"CSV file saved to {filename}")