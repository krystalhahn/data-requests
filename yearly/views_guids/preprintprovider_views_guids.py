ppps = ['acctrt', 'biohackrxiv', 'bodoarxiv', 'coppreprints', 'edarxiv', 'ecsarxiv', 'focusarchive', 
        'lawarchive', 'mediarxiv', 'metaarxiv', 'newaddictionsx', 'paleorxiv', 'psyarxiv', 'socarxiv']

def get_preprintprovider_guids(ppps):
    import io
    import csv
    import pytz
    from django.utils import timezone
    import pytz
    from dateutil.relativedelta import relativedelta
    from tqdm import tqdm

    filename = '/tmp/preprintprovider_guids.csv'
    COL_HEADERS = ['preprint_provider', 'guid']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    target_ppps = PreprintProvider.objects.filter(_id__in=ppps)

    pbar = tqdm(total = target_ppps.count())

    for ppp in target_ppps:

        for preprint in ppp.preprints.all():

            writer.writerow({
                'preprint_provider': ppp._id,
                'guid': preprint._id
            })

        pbar.update()

    pbar.close()

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")