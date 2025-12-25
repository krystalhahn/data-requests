import io
import csv
from tqdm import tqdm

from django.db.models.aggregates import Count
from django.db.models.expressions import F, Func, Subquery

from osf.models import OSFUser

def check_contributors(n=None):
    from osf.metrics import CountedAuthUsage
    import csv
    import io
    filename = '/tmp/contributor_object_counts.csv'
    COL_HEADERS = ['public_projects_contributor', 'private_projects_contributor',
                   'preprints_contributor', 'registrations_contributor',
                   'public_projects_contributor_1', 'private_projects_contributor_1',
                   'preprints_contributor_1', 'registrations_contributor_1',
                   'public_projects_contributors_2_3', 'private_projects_contributor_2_3',
                   'preprints_contributors_2_3', 'registrations_contributor_2_3',
                   'public_projects_contributor_4_plus', 'private_projects_contributor_4_plus',
                   'preprints_contributor_4_plus', 'registrations_contributor_4_plus']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    # count Contributors for each Node/Registration
    contributor_count = Contributor.objects.filter(
        node=OuterRef('pk')).values('node').annotate(count=Count('id'))

     # count Contributors for each Preprint
    preprint_contributor_count = PreprintContributor.objects.filter(
        preprint=OuterRef('pk')).values('preprint').annotate(count=Count('id'))
    
    # total public/private projects with contributors
    pub_proj_count = Node.objects.annotate(
        contributor_count=Subquery(contributor_count.filter(count__gt=0).values('count'))
    ).filter(is_public=True, contributor_count__gt=0).count()

    priv_proj_count = Node.objects.annotate(
        contributor_count=Subquery(contributor_count.filter(count__gt=0).values('count'))
    ).filter(is_public=False, contributor_count__gt=0).count()
    
		# total preprints with contributors
    prepr_count = Preprint.objects.annotate(
        contributor_count=Subquery(preprint_contributor_count.filter(count__gt=0).values('count'))
    ).filter(contributor_count__gt=0).count()

    # total registrations with contributors
    reg_count = Registration.objects.annotate(
        contributor_count=Subquery(contributor_count.filter(count__gt=0).values('count'))
    ).filter(contributor_count__gt=0).count()

    # subqueries for each contributor count rang
    pub_proj_count_1 = Node.objects.annotate(
        contributor_count=Subquery(contributor_count.filter(count=1).values('count'))
    ).filter(is_public=True, contributor_count=1).count()

    priv_proj_count_1 = Node.objects.annotate(
        contributor_count=Subquery(contributor_count.filter(count=1).values('count'))
    ).filter(is_public=False, contributor_count=1).count()

    prepr_count_1 = Preprint.objects.annotate(
        contributor_count=Subquery(preprint_contributor_count.filter(count=1).values('count'))
    ).filter(contributor_count=1).count()

    reg_count_1 = Registration.objects.annotate(
        contributor_count=Subquery(contributor_count.filter(count=1).values('count'))
    ).filter(contributor_count=1).count()

    pub_proj_count_2_3 = Node.objects.annotate(
        contributor_count=Subquery(contributor_count.filter(count__gte=2, count__lte=3).values('count'))
    ).filter(is_public=True, contributor_count__gte=2, contributor_count__lte=3).count()

    priv_proj_count_2_3 = Node.objects.annotate(
        contributor_count=Subquery(contributor_count.filter(count__gte=2, count__lte=3).values('count'))
    ).filter(is_public=False, contributor_count__gte=2, contributor_count__lte=3).count()

    prepr_count_2_3 = Preprint.objects.annotate(
        contributor_count=Subquery(preprint_contributor_count.filter(count__gte=2, count__lte=3).values('count'))
    ).filter(contributor_count__gte=2, contributor_count__lte=3).count()

    reg_count_2_3 = Registration.objects.annotate(
        contributor_count=Subquery(contributor_count.filter(count__gte=2, count__lte=3).values('count'))
    ).filter(contributor_count__gte=2, contributor_count__lte=3).count()

    pub_proj_count_4_plus = Node.objects.annotate(
        contributor_count=Subquery(contributor_count.filter(count__gte=4).values('count'))
    ).filter(is_public=True, contributor_count__gte=4).count()

    priv_proj_count_4_plus = Node.objects.annotate(
        contributor_count=Subquery(contributor_count.filter(count__gte=4).values('count'))
    ).filter(is_public=False, contributor_count__gte=4).count()

    prepr_count_4_plus = Preprint.objects.annotate(
        contributor_count=Subquery(preprint_contributor_count.filter(count__gte=4).values('count'))
    ).filter(contributor_count__gte=4).count()

    reg_count_4_plus = Registration.objects.annotate(
        contributor_count=Subquery(contributor_count.filter(count__gte=4).values('count'))
    ).filter(contributor_count__gte=4).count()
 
    writer.writerow({
        'public_projects_contributor': pub_proj_count, 
        'private_projects_contributor': priv_proj_count,
        'preprints_contributor': prepr_count, 
        'registrations_contributor': reg_count,
        'public_projects_contributor_1': pub_proj_count_1, 
        'private_projects_contributor_1': priv_proj_count_1,
        'preprints_contributor_1': prepr_count_1, 
        'registrations_contributor_1': reg_count_1,
        'public_projects_contributors_2_3': pub_proj_count_2_3, 
        'private_projects_contributor_2_3': priv_proj_count_2_3,
        'preprints_contributors_2_3': prepr_count_2_3, 
        'registrations_contributor_2_3': reg_count_2_3,
        'public_projects_contributor_4_plus': pub_proj_count_4_plus, 
        'private_projects_contributor_4_plus': priv_proj_count_4_plus,
        'preprints_contributor_4_plus': prepr_count_4_plus, 
        'registrations_contributor_4_plus': reg_count_4_plus
    })

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())