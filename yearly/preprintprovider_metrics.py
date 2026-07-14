def write_ppp_csvs(start_month, end_month, prov=None):
    import io
    import csv
    import pytz
    from django.utils import timezone
    import pytz
    from dateutil.relativedelta import relativedelta
    from tqdm import tqdm
    from math import ceil

    if prov:
        filename = f'/tmp/{prov._id}_metrics.csv'
    else:
        filename = f'/tmp/preprintprovider_metrics.csv'
    fieldnames = ['month', 'provider._id', 'submitted', 'withdrawn']
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()

    start_y, start_m = map(int, start_month.split("-"))
    start = timezone.datetime(start_y, start_m, 1, tzinfo=pytz.utc)
    end_y, end_m = map(int, end_month.split("-"))
    end = timezone.datetime(end_y, end_m, 1, tzinfo=pytz.utc)

    current = start
    
    if not prov:
        qs = PreprintProvider.objects.all()
    else:
        qs = PreprintProvider.objects.filter(id=prov.id)

    num_months = (end.year - start.year) * 12 + (end.month - start.month)
    pbar = tqdm(total=num_months * qs.count())

    while current < end:
        next_month = current + relativedelta(months=1)

        month = current.strftime("%b").lower()

        for ppp in qs:
            if ppp.reviews_workflow == 'post-moderation':
                sub_q = ppp.preprints.filter(machine_state__in=['accepted', 'pending'])
            else:
                sub_q = ppp.preprints.filter(machine_state='accepted')
            
            writer.writerow({
                    'month': month,
                    'provider._id': ppp._id,
                    'submitted': sub_q.filter(created__gte=current, created__lt=next_month).count(),
                    'withdrawn': ppp.preprints.filter(date_withdrawn__gte=current, date_withdrawn__lt=next_month, machine_state='withdrawn').count()
                })
            pbar.update()

        current = next_month

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"CSV file saved to {filename}")