import io
import csv
import pytz
from django.utils import timezone
from tqdm import tqdm

from osf.models import PreprintProvider
from osf.models import Preprint

def write_ppp_csvs(prov=None, end_year=None):
    this_year = end_year or timezone.now().year
    last_year = this_year - 1
    jul = timezone.datetime(last_year, 7, 1, tzinfo=pytz.utc)
    aug = timezone.datetime(last_year, 8, 1, tzinfo=pytz.utc)
    sep = timezone.datetime(last_year, 9, 1, tzinfo=pytz.utc)
    oct = timezone.datetime(last_year, 10, 1, tzinfo=pytz.utc)
    nov = timezone.datetime(last_year, 11, 1, tzinfo=pytz.utc)
    dec = timezone.datetime(last_year, 12, 1, tzinfo=pytz.utc)
    jan = timezone.datetime(this_year, 1, 1, tzinfo=pytz.utc)
    feb = timezone.datetime(this_year, 2, 1, tzinfo=pytz.utc)
    mar = timezone.datetime(this_year, 3, 1, tzinfo=pytz.utc)
    apr = timezone.datetime(this_year, 4, 1, tzinfo=pytz.utc)
    may = timezone.datetime(this_year, 5, 1, tzinfo=pytz.utc)
    jun = timezone.datetime(this_year, 6, 1, tzinfo=pytz.utc)
    jul21 = timezone.datetime(this_year, 7, 1, tzinfo=pytz.utc)
    months = [jul, aug, sep, oct, nov, dec, jan, feb, mar, apr, may, jun, jul21]
    if prov:
        filename = f'/tmp/{prov._id}_metrics.csv'
    else:
        filename = f'/tmp/preprintprovider_metrics.csv'
    fieldnames = ['month', 'provider._id', 'submitted', 'withdrawn']
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()
    if not prov:
        qs = PreprintProvider.objects.all()
    else:
        qs = PreprintProvider.objects.filter(id=prov.id)
    pbar = tqdm(total=qs.count()*12)
    for ppp in qs:
        if ppp.reviews_workflow == 'post-moderation':
            sub_q = ppp.preprints.filter(machine_state__in=['accepted', 'pending'])
        else:
            sub_q = ppp.preprints.filter(machine_state='accepted')
        for i, mo in enumerate(months):
            if i == len(months)-1:
                break
            end = months[i+1]
            writer.writerow({
                'month': f'{mo.month}-{mo.year}',
                'provider._id': ppp._id,
                'submitted': sub_q.filter(created__gte=mo, created__lt=end).count(),
                'withdrawn': ppp.preprints.filter(date_withdrawn__gte=mo, date_withdrawn__lt=end, machine_state='withdrawn').count()
            })
            pbar.update()
    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())