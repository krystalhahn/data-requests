# Total, not only for the quarter
def get_inst_preprints_by_provider():
    import csv
    import io
    from tqdm import tqdm

    filename = f'/tmp/inst_preprintprovider_metrics.csv'
    COL_HEADERS = ['institution.name', 'provider.name', 'total_preprints']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    insts = Institution.objects.all()

    pbar = tqdm(total=insts.count())

    for i in insts:
        for ppp in PreprintProvider.objects.all():

            users = OSFUser.objects.filter(
                institutionaffiliation__institution__id=i.id,
                is_active=True
            ).exclude(spam_status=2).distinct()

            domain_metrics = {
                'institution.name': i.name,
                'provider.name': ppp.name,
                'total_preprints': Preprint.objects.filter(_contributors__in=users, provider=ppp, is_public=True, is_published=True).exclude(spam_status=2).distinct().count()
            }
            if domain_metrics.get('total_preprints', 0):
                writer.writerow(domain_metrics)

        pbar.update(1)

    pbar.close()

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")