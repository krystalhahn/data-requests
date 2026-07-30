# dynamic version of function that checks for new keys in spam_data
def get_private_spam_node_sample(sample_size=100):
    import io
    import csv
    import random
    from tqdm import tqdm

    filename = f'/tmp/private_spam_node_sample.csv'
    fieldnames = [
        'guid', 'title', 'contributors', 'description', 'date_created',
        'spam_data_author', 'spam_data_author_email', 'spam_data_content',
        'spam_data_domains',
        'spam_data_headers_Referer', 'spam_data_headers_Remote-Addr', 'spam_data_headers_User-Agent',
        'spam_data_who_flagged',
        'spam_data_oopspam_data_Score',
        'spam_data_oopspam_data_Details_isIPBlocked',
        'spam_data_oopspam_data_Details_isContentSpam',
        'spam_data_oopspam_data_Details_numberOfSpamWords',
        'spam_data_oopspam_data_Details_spamWords',
        'spam_data_oopspam_data_Details_countryMatch',
        'spam_data_oopspam_data_Details_isContentTooShort',
        'spam_data_oopspam_data_Details_isEmailBlocked',
        'spam_data_oopspam_data_Details_langMatch',
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()

    nodes_qs = Node.objects.filter(is_public=False, spam_status=2)
    all_ids = list(nodes_qs.values_list('id', flat=True))
    sample_ids = random.sample(all_ids, min(sample_size, len(all_ids)))
    nodes = Node.objects.filter(id__in=sample_ids)

    for n in tqdm(nodes, total=len(nodes)):
        row = {
            'guid': n._id,
            'title': n.title,
            'contributors': '; '.join(n.contributors.values_list('fullname', flat=True)),
            'description': n.description,
            'date_created': n.created,
        }

        spam_data = n.spam_data or {}
        for k, v in spam_data.items():
            if isinstance(v, dict):
                for nested_k, nested_v in v.items():
                    if isinstance(nested_v, dict):
                        # one more level down (e.g. oopspam_data -> Details -> spamWords)
                        for deep_k, deep_v in nested_v.items():
                            key = f"spam_data_{k}_{nested_k}_{deep_k}"
                            if isinstance(deep_v, list):
                                row[key] = '; '.join(str(item) for item in deep_v)
                            else:
                                row[key] = deep_v
                    elif isinstance(nested_v, list):
                        row[f"spam_data_{k}_{nested_k}"] = '; '.join(str(item) for item in nested_v)
                    else:
                        row[f"spam_data_{k}_{nested_k}"] = nested_v
            elif isinstance(v, list):
                row[f"spam_data_{k}"] = '; '.join(str(item) for item in v)
            else:
                row[f"spam_data_{k}"] = v

        writer.writerow(row)

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")

# set fields explicitly
def get_private_spam_node_sample(sample_size=100):
    import io
    import csv
    import random
    from tqdm import tqdm

    filename = f'/tmp/private_spam_node_sample.csv'
    fieldnames = [
        'guid', 'title', 'contributors', 'description', 'date_created',
        'spam_data_author', 'spam_data_author_email', 'spam_data_content',
        'spam_data_domains',
        'spam_data_headers_Referer', 'spam_data_headers_Remote-Addr', 'spam_data_headers_User-Agent',
        'spam_data_who_flagged',
        'spam_data_oopspam_data_Score',
        'spam_data_oopspam_data_Details_isIPBlocked',
        'spam_data_oopspam_data_Details_isContentSpam',
        'spam_data_oopspam_data_Details_numberOfSpamWords',
        'spam_data_oopspam_data_Details_spamWords',
        'spam_data_oopspam_data_Details_countryMatch',
        'spam_data_oopspam_data_Details_isContentTooShort',
        'spam_data_oopspam_data_Details_isEmailBlocked',
        'spam_data_oopspam_data_Details_langMatch',
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()

    nodes_qs = Node.objects.filter(is_public=False, spam_status=2)
    all_ids = list(nodes_qs.values_list('id', flat=True))
    sample_ids = random.sample(all_ids, min(sample_size, len(all_ids)))
    nodes = Node.objects.filter(id__in=sample_ids)

    for n in tqdm(nodes, total=len(nodes)):
        spam_data = n.spam_data or {}
        headers = spam_data.get('headers', {}) or {}
        oopspam_data = spam_data.get('oopspam_data', {}) or {}
        details = oopspam_data.get('Details', {}) or {}

        row = {
            'guid': n._id,
            'title': n.title,
            'contributors': ', '.join(f"'{name}'" for name in n.contributors.values_list('fullname', flat=True)),
            'description': n.description,
            'date_created': n.created,
            'spam_data_author': spam_data.get('author'),
            'spam_data_author_email': spam_data.get('author_email'),
            'spam_data_content': spam_data.get('content'),
            'spam_data_domains': '; '.join(spam_data.get('domains', [])) if spam_data.get('domains') else None,
            'spam_data_headers_Referer': headers.get('Referer'),
            'spam_data_headers_Remote-Addr': headers.get('Remote-Addr'),
            'spam_data_headers_User-Agent': headers.get('User-Agent'),
            'spam_data_who_flagged': spam_data.get('who_flagged'),
            'spam_data_oopspam_data_Score': oopspam_data.get('Score'),
            'spam_data_oopspam_data_Details_isIPBlocked': details.get('isIPBlocked'),
            'spam_data_oopspam_data_Details_isContentSpam': details.get('isContentSpam'),
            'spam_data_oopspam_data_Details_numberOfSpamWords': details.get('numberOfSpamWords'),
            'spam_data_oopspam_data_Details_spamWords': '; '.join(details.get('spamWords', [])) if details.get('spamWords') else None,
            'spam_data_oopspam_data_Details_countryMatch': details.get('countryMatch'),
            'spam_data_oopspam_data_Details_isContentTooShort': details.get('isContentTooShort'),
            'spam_data_oopspam_data_Details_isEmailBlocked': details.get('isEmailBlocked'),
            'spam_data_oopspam_data_Details_langMatch': details.get('langMatch'),
        }

        writer.writerow(row)

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")