####################
# subject
# public_projects
# private_projects
# public_registrations
# withdrawn_registrations
# embargoed_registrations
# published_preprints
# withdrawn_preprints
#####################

# flexible function to handle both metrics with and without spam
# run twice for all objects and non-spam objects
## get_content_subjects() --> content_subjects.csv
## get_content_subjects(include_spam=False) --> content_subjects_nonspam.csv

import io
import csv
from tqdm import tqdm
from django.db.models import Q
from osf.models import OSFUser, Node, Registration, Preprint, Subject


def get_content_subjects(include_spam=True, n=None):
    filename = f"/tmp/content_subjects{'_nonspam' if not include_spam else ''}.csv"
    fieldnames = [
        "subject",
        "public_projects",
        "private_projects",
        "public_registrations",
        "withdrawn_registrations",
        "embargoed_registrations",
        "published_preprints",
        "withdrawn_preprints",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()

    # top level of bepress taxonomy
    subject_names = [
        "Architecture",
        "Arts and Humanities",
        "Business",
        "Education",
        "Engineering",
        "Law",
        "Life Sciences",
        "Medicine and Health Sciences",
        "Physical Sciences and Mathematics",
        "Social and Behavioral Sciences",
    ]

    pbar = tqdm(total=len(subject_names))

    # spam filter
    spam_filter = Q() if include_spam else ~Q(spam_status__in=[1, 2])

    for subject in subject_names:
        subject_objs = Subject.objects.filter(text=subject)

        writer.writerow(
            {
                "subject": subject,
                "public_projects": Node.objects.filter(
                    subjects__in=subject_objs, is_public=True, deleted__isnull=True
                )
                .filter(spam_filter)
                .distinct()
                .count(),
                "private_projects": Node.objects.filter(
                    subjects__in=subject_objs, is_public=False, deleted__isnull=True
                )
                .filter(spam_filter)
                .distinct()
                .count(),
                "public_registrations": Registration.objects.filter(
                    subjects__in=subject_objs, is_public=True, deleted__isnull=True
                )
                .exclude(retraction__state="approved")
                .filter(spam_filter)
                .distinct()
                .count(),
                "withdrawn_registrations": Registration.objects.filter(
                    subjects__in=subject_objs,
                    is_public=True,
                    deleted__isnull=True,
                    retraction__state="approved",
                )
                .filter(spam_filter)
                .distinct()
                .count(),
                "embargoed_registrations": Registration.objects.filter(
                    subjects__in=subject_objs,
                    is_public=False,
                    deleted__isnull=True,
                    embargo__state="approved",
                )
                .filter(spam_filter)
                .distinct()
                .count(),
                "published_preprints": Preprint.objects.filter(
                    subjects__in=subject_objs,
                    is_public=True,
                    is_published=True,
                    deleted__isnull=True,
                )
                .exclude(machine_state="withdrawn")
                .filter(spam_filter)
                .distinct()
                .count(),
                "withdrawn_preprints": Preprint.objects.filter(
                    subjects__in=subject_objs,
                    is_public=True,
                    is_published=True,
                    deleted__isnull=True,
                    machine_state="withdrawn",
                )
                .filter(spam_filter)
                .distinct()
                .count(),
            }
        )

        pbar.update(1)
    pbar.close()

    with open(filename, "w") as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")
