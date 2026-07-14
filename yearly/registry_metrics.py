def get_monthly_registration_metrics(start_month, end_month):
    import csv
    import io
    from django.utils import timezone
    import pytz
    from dateutil.relativedelta import relativedelta
    from tqdm import tqdm

    filename = '/tmp/monthly_registration_metrics.csv'
    COL_HEADERS = ['month', 'schema', 'accepted', 'embargoed', 'rejected', 'withdrawn', 'updated']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    start_y, start_m = map(int, start_month.split("-"))
    start = timezone.datetime(start_y, start_m, 1, tzinfo=pytz.utc)
    end_y, end_m = map(int, end_month.split("-"))
    end = timezone.datetime(end_y, end_m, 1, tzinfo=pytz.utc)

    current = start

    num_months = (end.year - start.year) * 12 + (end.month - start.month)
    pbar = tqdm(total=num_months)
    
    while current < end:
        next_month = current + relativedelta(months=1)

        month = current.strftime("%b").lower()

        target_regs = Registration.objects.filter(provider__reviews_workflow='pre-moderation', created__gte=current, created__lt=next_month)
        valid_schemas = set(list(target_regs.values_list('registered_schema__name', flat=True)))

        for sn in valid_schemas:
            writer.writerow({
                'month': month,
                'schema': sn,
                'accepted': target_regs.filter(registered_schema__name=sn, moderation_state='accepted').count(),
                'embargoed': target_regs.filter(registered_schema__name=sn, moderation_state='embargo').count(),
                'rejected': target_regs.filter(registered_schema__name=sn, moderation_state='rejected').count(),
                'withdrawn': target_regs.filter(registered_schema__name=sn, moderation_state='withdrawn').count(),
                'updated': target_regs.filter(registered_schema__name=sn).annotate(src=Count('schema_responses')).filter(src__gte=2).count()

            })
        
        pbar.update()
        current = next_month
            
    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"CSV file saved to {filename}")

def get_monthly_registry_metrics(start_month, end_month, targets=None):
    import csv
    import io
    from django.utils import timezone
    import pytz
    from dateutil.relativedelta import relativedelta
    from tqdm import tqdm

    filename = '/tmp/monthly_registry_metrics.csv'
    COL_HEADERS = ['month', 'provider', 'schema', 'total', 'accepted', 'embargoed', 'embargo_approved', 'approved', 'rejected', 'withdrawn', 'updated']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    start_y, start_m = map(int, start_month.split("-"))
    start = timezone.datetime(start_y, start_m, 1, tzinfo=pytz.utc)
    end_y, end_m = map(int, end_month.split("-"))
    end = timezone.datetime(end_y, end_m, 1, tzinfo=pytz.utc)

    current = start

    if targets:
        target_providers = RegistrationProvider.objects.filter(_id__in=targets)
    else: 
        target_providers = RegistrationProvider.objects.all()

    num_months = (end.year - start.year) * 12 + (end.month - start.month)
    pbar = tqdm(total=num_months * target_providers.count())
    
    while current < end:
        next_month = current + relativedelta(months=1)

        month = current.strftime("%b").lower()

        for provider in target_providers:
            target_regs = Registration.objects.filter(provider=provider, created__gte=current, created__lt=next_month)
            valid_schemas = set(list(provider.schemas.values_list('name', flat=True)))

            for sn in valid_schemas:
                writer.writerow({
                    'month': month,
                    'provider': provider._id,
                    'schema': sn,
                    'total': target_regs.filter(registered_schema__name=sn).count(),
                    'accepted': target_regs.filter(registered_schema__name=sn, moderation_state='accepted').count(),
                    'embargoed': target_regs.filter(registered_schema__name=sn, moderation_state='embargo').count(),
                    'embargo_approved': target_regs.filter(registered_schema__name=sn, embargo__state='approved').count(),
                    'approved': target_regs.filter(registered_schema__name=sn, registration_approval__state='approved').count(),
                    'rejected': target_regs.filter(registered_schema__name=sn, moderation_state='rejected').count(),
                    'withdrawn': target_regs.filter(registered_schema__name=sn, moderation_state='withdrawn').count(),
                    'updated': target_regs.filter(registered_schema__name=sn).annotate(src=Count('schema_responses')).filter(src__gte=2).count()
                })

            pbar.update()

        current = next_month

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"CSV file saved to {filename}")

