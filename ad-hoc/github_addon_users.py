import io
import csv
from tqdm import tqdm

from django.db.models import Prefetch
from osf.models import OSFUser
from addons.github.models import UserSettings

def get_github_addon_users(n=None):
    filename = '/tmp/github_addon_users.csv'
    fieldnames = ['u._id', 'u.username', 'u.date_confirmed', 'u.date_last_login', 'github_addon', 'addon_created', 'addon_modified']
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()

    # prefetch related GitHub addon settings
    qs = OSFUser.objects.filter(is_active=True).exclude(spam_status__in=[1, 2]).prefetch_related(
        Prefetch('addons_github_user_settings', queryset=UserSettings.objects.only('created', 'modified', 'is_deleted'))
    )
    if n:
        qs = qs[:n]

    pbar = tqdm(total=qs.count())
    for user in qs:
        # get related GitHub addon settings if available
        github_settings = getattr(user, 'addons_github_user_settings', None)
        writer.writerow({
            'u._id': user._id,
            'u.username': user.username,
            'u.date_confirmed': user.date_confirmed.date().isoformat() if user.date_confirmed else None,
            'u.date_last_login': user.date_last_login.date().isoformat() if user.date_last_login else None,
            'github_addon': True if github_settings and not github_settings.is_deleted else False,
            'addon_created': github_settings.created.isoformat() if github_settings else None,
            'addon_modified': github_settings.modified.isoformat() if github_settings else None,
        })
        pbar.update()

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())