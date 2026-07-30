def get_weekly_active_users(backup_cutoff):
    import io
    import csv
    from tqdm import tqdm
    import datetime
    import pytz
    from django.utils import timezone
    import time

    filename = f'/tmp/weekly_active_users.csv'
    fieldnames = ['login_count', 'action_count_from_user', 'action_count_from_log']
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()

    end_y, end_m, end_d = map(int, backup_cutoff.split("-"))
    end = timezone.datetime(end_y, end_m, end_d, tzinfo=pytz.utc)
    start = end - datetime.timedelta(days=7)

    print("Counting logins...")
    t0 = time.time()
    login_count = OSFUser.objects.filter(date_last_login__gte=start, date_last_login__lt=end).count()
    print(f"Login count: {login_count} (took {time.time() - t0:.2f}s)")

    print("Counting users with actions from NodeLog...")
    t0 = time.time()
    # don't count when there is no user (system)
    action_count_from_log = NodeLog.objects.filter(created__gte=start, created__lt=end, user__isnull=False).values('user').distinct().count()
    print(f"Action count from NodeLog: {action_count_from_log} (took {time.time() - t0:.2f}s)")

    print("Counting users with actions from OSFUser...")
    t0 = time.time()
    action_count_from_user = OSFUser.objects.filter(logs__created__gte=start, logs__created__lt=end).distinct().count()
    print(f"Action count from OSFUser: {action_count_from_user} (took {time.time() - t0:.2f}s)")

    writer.writerow({
        'login_count': login_count,
        'action_count_from_user': action_count_from_user,
        'action_count_from_log': action_count_from_log
    })

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")