def fetch_project_doi_privacy(ds, name='institutional'):
    from osf.metrics import CountedAuthUsage
    import csv
    import io
    filename = f'/tmp/{name}_project_doi_privacy.csv'
    COL_HEADERS = [ 'user_domain', 'user_subdomain', 'user_guid', 'object_guid', 'object_type', 'object_title', 'object_is_public', 'object_created', 'object_doi_created', 'object_doi', 'article_doi']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    n_iqs = Identifier.objects.filter(content_type=30, object_id=OuterRef('pk'), category='doi', value__isnull=False)
    p_iqs = Identifier.objects.filter(content_type=47, object_id=OuterRef('pk'), category='doi', value__isnull=False)
    
    for d in ds:

        target_users = OSFUser.objects.filter(
            is_active=True, emails__address__endswith=d
        ).exclude(spam_status__in=[1,2]).values_list('id', flat=True)
        
        # retrieve nodes, registrations, and preprints for domain users
        domain_nodes = Node.objects.annotate(
                has_doi=Exists(n_iqs),
                doi_value=Subquery(n_iqs.values('value')[:1]),
                doi_created=Subquery(n_iqs.values('created')[:1])
            ).filter(_contributors__in=target_users, deleted__isnull=True, is_deleted=False).distinct()
        domain_regs = Registration.objects.annotate(
                has_doi=Exists(n_iqs),
                doi_value=Subquery(n_iqs.values('value')[:1]),
                doi_created=Subquery(n_iqs.values('created')[:1])
            ).filter(_contributors__in=target_users, deleted__isnull=True, is_deleted=False).distinct()
        domain_preprints = Preprint.objects.annotate(
                has_doi=Exists(p_iqs),
                doi_value=Subquery(p_iqs.values('value')[:1]),
                doi_created=Subquery(p_iqs.values('created')[:1])
            ).filter(_contributors__in=target_users, deleted__isnull=True).distinct()

        for n in domain_nodes:
            writer.writerow({
                'user_domain': d,
                'object_guid': n._id,
                'object_type': n.type,
                'object_title': n.title,
                'object_is_public': n.is_public,
                'object_created': n.created,
                'object_doi_created': n.doi_created,
                'object_doi': n.doi_value,
                'article_doi': n.article_doi
            })
        for r in domain_regs:
            writer.writerow({
                'user_domain': d,
                'object_guid': r._id,
                'object_type': r.type,
                'object_title': r.title,
                'object_is_public': r.is_public,
                'object_created': r.created,
                'object_doi_created': r.doi_created,
                'object_doi':r.doi_value,
                'article_doi': r.article_doi
            })
        for p in domain_preprints:
            writer.writerow({
                'user_domain': d,
                'object_guid': p._id,
                'object_type': 'osf.preprint',
                'object_title': p.title,
                'object_is_public': p.is_public,
                'object_created': p.created,
                'object_doi_created': p.doi_created,
                'object_doi': p.doi_value,
                'article_doi': p.article_doi
            })
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())