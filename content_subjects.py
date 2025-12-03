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

import io
import csv
from tqdm import tqdm
from django.db.models.aggregates import Count
from django.db.models.expressions import F, Func, Subquery
from osf.models import OSFUser, Node, Registration, Preprint

# ALL objects
def get_content_subjects(n=None):
    filename = f'/tmp/content_subjects.csv'
    fieldnames = ['subject', 'public_projects', 'private_projects', 
                  'public_registrations', 'withdrawn_registrations', 'embargoed_registrations', 
                  'published_preprints', 'withdrawn_preprints']
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()
    
    # use top level of bepress taxonomy
    subject_names = ['Architecture', 'Arts and Humanities', 'Business', 'Education', 'Engineering', 'Law', 'Life Sciences', 'Medicine and Health Sciences', 'Physical Sciences and Mathematics', 'Social and Behavioral Sciences']

    pbar = tqdm(total=len(subject_names))

    for subject in subject_names:
        subject_objs = Subject.objects.filter(text=subject)

        writer.writerow({
            'subject': subject,
            'public_projects': Node.objects.filter(subjects__in=subject_objs, is_public=True, deleted__isnull=True).distinct().count(),
            'private_projects': Node.objects.filter(subjects__in=subject_objs, is_public=False, deleted__isnull=True).distinct().count(),
            'public_registrations': Registration.objects.filter(subjects__in=subject_objs, is_public=True, deleted__isnull=True).exclude(retraction__state='approved').distinct().count(),
            'withdrawn_registrations': Registration.objects.filter(subjects__in=subject_objs, is_public=True, deleted__isnull=True, retraction__state='approved').distinct().count(),
            'embargoed_registrations': Registration.objects.filter(subjects__in=subject_objs, is_public=False, deleted__isnull=True, embargo__state='approved').distinct().count(),
            'published_preprints': Preprint.objects.filter(subjects__in=subject_objs, is_public=True, is_published=True, deleted__isnull=True).exclude(machine_state='withdrawn').distinct().count(),
            'withdrawn_preprints': Preprint.objects.filter(subjects__in=subject_objs, is_public=True, is_published=True, deleted__isnull=True, machine_state='withdrawn').distinct().count(),
        })

        pbar.update(1)
    pbar.close()

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

# NONSPAM objects
def get_content_subjects_nonspam(n=None):
    filename = f'/tmp/content_subjects_nonspam.csv'
    fieldnames = ['subject', 'public_projects', 'private_projects', 
                  'public_registrations', 'withdrawn_registrations', 'embargoed_registrations', 
                  'published_preprints', 'withdrawn_preprints']
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()
    
    # use top level of bepress taxonomy
    subject_names = ['Architecture', 'Arts and Humanities', 'Business', 'Education', 'Engineering', 'Law', 'Life Sciences', 'Medicine and Health Sciences', 'Physical Sciences and Mathematics', 'Social and Behavioral Sciences']

    pbar = tqdm(total=len(subject_names))

    for subject in subject_names:
        subject_objs = Subject.objects.filter(text=subject)

        writer.writerow({
            'subject': subject,
            'public_projects': Node.objects.filter(subjects__in=subject_objs, is_public=True, deleted__isnull=True).exclude(spam_status__in=[1,2]).distinct().count(),
            'private_projects': Node.objects.filter(subjects__in=subject_objs, is_public=False, deleted__isnull=True).exclude(spam_status__in=[1,2]).distinct().count(),
            'public_registrations': Registration.objects.filter(subjects__in=subject_objs, is_public=True, deleted__isnull=True).exclude(retraction__state='approved').exclude(spam_status__in=[1,2]).distinct().count(),
            'withdrawn_registrations': Registration.objects.filter(subjects__in=subject_objs, is_public=True, deleted__isnull=True, retraction__state='approved').exclude(spam_status__in=[1,2]).distinct().count(),
            'embargoed_registrations': Registration.objects.filter(subjects__in=subject_objs, is_public=False, deleted__isnull=True, embargo__state='approved').exclude(spam_status__in=[1,2]).distinct().count(),
            'published_preprints': Preprint.objects.filter(subjects__in=subject_objs, is_public=True, is_published=True, deleted__isnull=True).exclude(machine_state='withdrawn').exclude(spam_status__in=[1,2]).distinct().count(),
            'withdrawn_preprints': Preprint.objects.filter(subjects__in=subject_objs, is_public=True, is_published=True, deleted__isnull=True, machine_state='withdrawn').exclude(spam_status__in=[1,2]).distinct().count(),
        })

        pbar.update(1)
    pbar.close()

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())