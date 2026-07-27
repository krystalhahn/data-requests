# example usage
get_users_from_email_domain('uol', ['@london.ac.uk', '@student.london.ac.uk', '@londonexternal.ac.uk'])

def get_users_from_email_domain(descriptor, domains):
    import io
    import csv
    from tqdm import tqdm
    from django.db.models import Q

    filename = f'/tmp/{descriptor}_email_domain_users.csv'
    fieldnames = ['user_id', 'primary_email_address', 'all_emails']
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()

    query = Q()
    for domain in domains:
        query |= Q(emails__address__icontains=domain) | Q(username__icontains=domain)

    users = OSFUser.objects.filter(query).distinct().prefetch_related('emails')

    for u in tqdm(users, total=users.count()):
        writer.writerow({
            'user_id': u._id,
            'primary_email_address': u.username,
            'all_emails': ', '.join(u.emails.values_list('address', flat=True))
        })

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"CSV file saved to {filename}")