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
    from django.db.models import Q

    filename = '/tmp/preprintprovider_guids.csv'
    COL_HEADERS = ['preprint_provider', 'guid']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    target_ppps = PreprintProvider.objects.filter(_id__in=ppps)

    guid_filter = Q()

    ct = ContentType.objects.get_for_model(Preprint)

    object_ids = Preprint.objects.filter(
        provider__in=target_ppps
    ).values("pk")

    guid_filter |= Q(
        content_type=ct,
        object_id__in=object_ids
    )

    ppp_guids = Guid.objects.filter(guid_filter)

    pbar = tqdm(total = ppp_guids.count())

    for guid in ppp_guids:
        writer.writerow({
            'preprintprovider': guid.referent.provider._id,
            'guid': guid._id
        })
        pbar.update()

    pbar.close()
    
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())