# example usage
get_monthly_registration_metrics("2025-07", "2026-07")

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

        month = current.strftime("%Y-%m")

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

    print(f"Output written to {filename}")

# example usage
# community-operated registries (COR) metrics: DAM, RWE, YOUth (+ OSF)
get_monthly_registry_metrics("2025-07", "2026-07", ("dam","rwe","youthstudy","osf"))

def get_monthly_registry_metrics(start_month, end_month, targets=None):
    import csv
    import io
    from django.db.models import Count, Q, Exists, OuterRef
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

    if targets:
        target_providers = RegistrationProvider.objects.filter(_id__in=targets)
    else:
        target_providers = RegistrationProvider.objects.all()

    providers = list(target_providers)
    num_months = (end.year - start.year) * 12 + (end.month - start.month)
    pbar = tqdm(total=num_months * len(providers))

    current = start

    while current < end:
        next_month = current + relativedelta(months=1)

        month = current.strftime("%Y-%m")

        for provider in providers:
            valid_schemas = set(
                provider.schemas.values_list('name', flat=True)
            )

            metrics = Registration.objects.filter(
                provider=provider,
                created__gte=current,
                created__lt=next_month,
                registered_schema__name__in=valid_schemas
            ).values(
                'registered_schema__name'
            ).annotate(
                total=Count('id'),
                accepted=Count('id', filter=Q(moderation_state='accepted')),
                embargoed=Count('id', filter=Q(moderation_state='embargo')),
                embargo_approved=Count('id', filter=Q(embargo__state='approved')),
                approved=Count('id', filter=Q(registration_approval__state='approved')),
                rejected=Count('id', filter=Q(moderation_state='rejected')),
                withdrawn=Count('id',filter=Q(moderation_state='withdrawn'))
            )
            metrics_by_schema = {
                row['registered_schema__name']: row
                for row in metrics
            }
            updated = Registration.objects.filter(
                provider=provider,
                created__gte=current,
                created__lt=next_month,
                registered_schema__name__in=valid_schemas
            ).filter(
                Exists(
                    Registration.objects.filter(
                        pk=OuterRef('pk')
                    ).annotate(
                        response_count=Count('schema_responses')
                    ).filter(
                        response_count__gte=2
                    )
                )
            ).values(
                'registered_schema__name'
            ).annotate(
                updated=Count('id')
            )

            updated_by_schema = {
                row['registered_schema__name']: row['updated']
                for row in updated
            }

            for sn in valid_schemas:
                row = metrics_by_schema.get(sn, {})
                writer.writerow({
                    'month': month,
                    'provider': provider._id,
                    'schema': sn,
                    'total': row.get('total', 0),
                    'accepted': row.get('accepted', 0),
                    'embargoed': row.get('embargoed', 0),
                    'embargo_approved': row.get('embargo_approved', 0),
                    'approved': row.get('approved', 0),
                    'rejected': row.get('rejected', 0),
                    'withdrawn': row.get('withdrawn', 0),
                    'updated': updated_by_schema.get(sn, 0)
                })

            pbar.update()

        current = next_month

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")