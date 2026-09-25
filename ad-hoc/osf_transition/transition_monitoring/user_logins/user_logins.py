def get_total_users_since_transition(backup_cutoff):
    import datetime
    import pytz
    from django.utils import timezone
    import time
    from django.db.models import Count, Q

    end_y, end_m, end_d = map(int, backup_cutoff.split("-"))
    end = timezone.datetime(end_y, end_m, end_d, tzinfo=pytz.utc)
    start = timezone.datetime(2026, 8, 9, tzinfo=pytz.utc)

    print("Counting users that have logged in since...")
    t0 = time.time()
    total_logged_in_users = OSFUser.objects.filter(
        date_last_login__gte=start, 
        date_last_login__lt=end
    ).annotate(
        total_project_count=Count(
            "nodes",
            filter=Q(nodes__type="osf.node"),
            distinct=True
        ),
        private_project_count=Count(
            "nodes",
            filter=Q(
                nodes__type="osf.node",
                nodes__is_public=False
            ),
            distinct=True
        )
    )

    total_login_count = total_logged_in_users.count()
    print(f"Total login count: {total_login_count} (took {time.time() - t0:.2f}s)")

    t0 = time.time()
    total_users = OSFUser.objects.filter(
        created__lt=end
    ).count()
    total_filtered_users = OSFUser.objects.filter(
        created__lt=end, 
        deleted__isnull=True, 
        is_active=True
        ).exclude(
            spam_status__in=[1,2]
            ).count()
    print(f"% of total user base: {total_login_count / total_users * 100:.2f}% (took {time.time() - t0:.2f}s)")

    print("Segmenting user logins by project count...")
    t0 = time.time()
    users_any_projects = total_logged_in_users.filter(total_project_count__gt=0).count()
    users_any_private_projects = total_logged_in_users.filter(private_project_count__gt=0).count()
    print(f"Users with >0 projects: {users_any_projects}")
    print(f"Users with >0 private projects: {users_any_private_projects}")

    users_more_than_5_projects = total_logged_in_users.filter(total_project_count__gt=5).count()
    users_more_than_5_private_projects = total_logged_in_users.filter(private_project_count__gt=5).count()
    print(f"Users with >5 projects: {users_more_than_5_projects}")
    print(f"Users with >5 private projects: {users_more_than_5_private_projects} (took {time.time() - t0:.2f}s)")