# Get institutional affiliations when available
import io
import csv
from tqdm import tqdm

from django.db.models.aggregates import Count
from django.db.models.expressions import F, Func, Subquery
from django.db.models import Value

from osf.models import OSFUser, Institution


def write_nps_users_insts(n=None):
    filename = "/tmp/nps_users_insts.csv"
    fieldnames = ["u._id", "u.username", "institution_name"]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()

    insts = Institution.objects.all()

    pbar = tqdm(total=insts.count())

    for i in insts:
        qs = (
            OSFUser.objects.filter(
                institutionaffiliation__institution__id=i.id, is_active=True
            )
            .exclude(spam_status__in=[1, 2])
            .annotate(institution_name=Value(i.name))
        )

        if n:
            qs = qs[:n]

        for udict in qs.values("guids___id", "username", "institution_name"):
            udict["u._id"] = udict.pop("guids___id")
            udict["u.username"] = udict.pop("username")
            udict["institution_name"] = udict.pop("institution_name")

            writer.writerow(udict)

        pbar.update(1)
    pbar.close()

    with open(filename, "w") as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")
