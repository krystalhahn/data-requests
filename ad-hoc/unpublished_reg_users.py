def get_unpublished_reg_users():
    import csv
    import io
    from tqdm import tqdm
    import json

    filename = '/tmp/unpublished_reg_users.csv'
    COL_HEADERS = ['guid', 'first_name', 'last_name', 'email_address', 'discipline', 'institution', 'last_title', 'titles']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    target_users = OSFUser.objects.annotate(
        has_published_reg=Exists(
            Registration.objects.filter(
                registered_user=OuterRef("pk"),
                date_registered__isnull=False
            )
        ),
        has_draft_reg=Exists(
            DraftRegistration.objects.filter(
                initiator=OuterRef("pk")
            )
        ),
    ).filter(
        has_published_reg=False,
        has_draft_reg=True,
    )

    pbar = tqdm(total=target_users.count())

    # get the reverse accessor for institution affiliations.
    affiliation_field = next(
        f for f in OSFUser._meta.get_fields()
        if f.name == 'institutionaffiliation'
    )
    affiliation_accessor = affiliation_field.get_accessor_name()

    for user in target_users.iterator(chunk_size=1000):

        subjects = DraftRegistration.objects.filter(
                    initiator=user,
                ).values_list('subjects__text', flat=True).distinct()

        affiliations = getattr(user, affiliation_accessor).select_related(
            'institution'
        )
        institution_names = sorted({
            affiliation.institution.name
            for affiliation in affiliations
            if affiliation.institution
        })

        jobs = user.jobs or []

        def to_int(value):
            try:
                return int(value or 0)
            except (ValueError, TypeError):
                return 0

        latest_job = max(
            jobs,
            key=lambda job: (
                to_int(job.get("startYear")),
                to_int(job.get("startMonth")),
            ),
            default={},
        )

        writer.writerow({
            'guid': user._id,
            'first_name': user.given_name,
            'last_name': user.family_name,
            'email_address': user.username,
            'discipline': '; '.join(subject for subject in subjects if subject),
            'institution': '; '.join(institution_names),
            'last_title': latest_job.get('title'),  
            'titles': json.dumps([job.get("title") for job in user.jobs], indent=2), 
        })
        pbar.update()

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")