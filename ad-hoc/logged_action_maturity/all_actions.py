# pulling `date_confirmed` instead of `created`, because not all `created` values are unique, it looks like there are buckets of `created` datetime values
def get_all_actions():
    import io
    import csv
    from tqdm import tqdm
    from datetime import datetime, timedelta
    from django.db.models import Count

    filename = f'/tmp/all_actions.csv'
    fieldnames = ['user_id', 'user_confirmed', 'action', 'action_created']
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()

    target_users = OSFUser.objects.filter(is_active=True).exclude(spam_status__in=[1,2])

    pbar = tqdm(total=target_users.count())

    for user in target_users:

        for log in user.logs.values_list('action', 'created'):
            action, action_created = log  # unpack the tuple
            writer.writerow({
                'user_id': user._id, 
                'user_confirmed': user.date_confirmed, 
                'action': action, 
                'action_created': action_created
            })

        pbar.update(1)
    pbar.close()

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())