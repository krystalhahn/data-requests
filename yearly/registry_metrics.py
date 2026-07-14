def get_monthly_metrics():
    import csv
    import io
    filename = '/tmp/monthly_COR_metrics.csv'
    COL_HEADERS = ['month', 'schema', 'accepted', 'embargoed', 'rejected', 'withdrawn', 'updated']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()
    jan = timezone.datetime(2024,1,1,tzinfo=pytz.utc)
    feb = timezone.datetime(2024,2,1,tzinfo=pytz.utc)
    mar = timezone.datetime(2024,3,1,tzinfo=pytz.utc)
    apr = timezone.datetime(2024,4,1,tzinfo=pytz.utc)
    may = timezone.datetime(2024,5,1,tzinfo=pytz.utc)
    jun = timezone.datetime(2024,6,1,tzinfo=pytz.utc)
    jul = timezone.datetime(2024,7,1,tzinfo=pytz.utc)
    dates = [jan, feb, mar, apr, may, jun, jul]
    while len(dates) > 1:
        start = dates.pop(0)
        end = dates[0]
        month = '-'.join(start.isoformat().split('-')[:2])
        target_regs = Registration.objects.filter(provider__reviews_workflow='pre-moderation', created__gte=start, created__lt=end)
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
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

def get_monthly_metrics_by_provider(targets=None):
    import csv
    import io
    filename = '/tmp/monthly_COR_provider_metrics.csv'
    COL_HEADERS = ['month', 'provider', 'schema', 'total', 'accepted', 'embargoed', 'rejected', 'withdrawn', 'updated']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()
    jan = timezone.datetime(2024,1,1,tzinfo=pytz.utc)
    feb = timezone.datetime(2024,2,1,tzinfo=pytz.utc)
    mar = timezone.datetime(2024,3,1,tzinfo=pytz.utc)
    apr = timezone.datetime(2024,4,1,tzinfo=pytz.utc)
    may = timezone.datetime(2024,5,1,tzinfo=pytz.utc)
    jun = timezone.datetime(2024,6,1,tzinfo=pytz.utc)
    jul = timezone.datetime(2024,7,1,tzinfo=pytz.utc)
    dates = [jan, feb, mar, apr, may, jun, jul]
    while len(dates) > 1:
        start = dates.pop(0)
        end = dates[0]
        month = '-'.join(start.isoformat().split('-')[:2])
        target_providers = targets or RegistrationProvider.objects.exclude(_id='osf')
        for provider in target_providers:
            target_regs = Registration.objects.filter(provider=provider, created__gte=start, created__lt=end)
            valid_schemas = set(list(provider.schemas.values_list('name', flat=True)))
            for sn in valid_schemas:
                writer.writerow({
                    'month': month,
                    'provider': provider._id,
                    'schema': sn,
                    'total': target_regs.filter(registered_schema__name=sn).count(),
                    'accepted': target_regs.filter(registered_schema__name=sn, moderation_state='accepted').count(),
                    'embargoed': target_regs.filter(registered_schema__name=sn, moderation_state='embargo').count(),
                    'rejected': target_regs.filter(registered_schema__name=sn, moderation_state='rejected').count(),
                    'withdrawn': target_regs.filter(registered_schema__name=sn, moderation_state='withdrawn').count(),
                    'updated': target_regs.filter(registered_schema__name=sn).annotate(src=Count('schema_responses')).filter(src__gte=2).count()
    
                })
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())


