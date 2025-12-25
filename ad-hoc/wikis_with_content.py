def check_wiki_content(n=None):
    filename = '/tmp/wiki_content_counts.csv'
    COL_HEADERS = ['public_projects_wikis', 'private_projects_wikis',
                   'public_projects_wikis_1', 'private_projects_wikis_1', 
                   'public_projects_wikis_2_5', 'private_projects_wikis_2_5',
                   'public_projects_wikis_6_plus', 'private_projects_wikis_6_plus']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    # count WikiVersions for each WikiPage of a Node
    wiki_version_count = WikiVersion.objects.filter(
        wiki_page__node=OuterRef('pk'), 
        content__isnull=False  
    ).values('wiki_page__node').annotate(count=Count('id'))

    # subqueries for each wiki version count range
    # total public/private projects with content in wiki
    public_wiki_count = Node.objects.annotate(
        wiki_count=Subquery(wiki_version_count.filter(count__gt=0).values('count'))
    ).filter(is_public=True, wiki_count__gt=0).count()

    private_wiki_count = Node.objects.annotate(
        wiki_count=Subquery(wiki_version_count.filter(count__gt=0).values('count'))
    ).filter(is_public=False, wiki_count__gt=0).count()

    # public/private projects with 1 wiki version
    public_wiki_count_1 = Node.objects.annotate(
        wiki_count=Subquery(wiki_version_count.filter(count=1).values('count'))
    ).filter(is_public=True, wiki_count=1).count()

    private_wiki_count_1 = Node.objects.annotate(
        wiki_count=Subquery(wiki_version_count.filter(count=1).values('count'))
    ).filter(is_public=False, wiki_count=1).count()

    # public/private projects with 2-5 wiki versions
    public_wiki_count_2_5 = Node.objects.annotate(
        wiki_count=Subquery(wiki_version_count.filter(count__gte=2, count__lte=5).values('count'))
    ).filter(is_public=True, wiki_count__gte=2, wiki_count__lte=5).count()

    private_wiki_count_2_5 = Node.objects.annotate(
        wiki_count=Subquery(wiki_version_count.filter(count__gte=2, count__lte=5).values('count'))
    ).filter(is_public=False, wiki_count__gte=2, wiki_count__lte=5).count()

    # public/private projects with 6 or more wiki versions
    public_wiki_count_6_plus = Node.objects.annotate(
        wiki_count=Subquery(wiki_version_count.filter(count__gte=6).values('count'))
    ).filter(is_public=True, wiki_count__gte=6).count()

    private_wiki_count_6_plus = Node.objects.annotate(
        wiki_count=Subquery(wiki_version_count.filter(count__gte=6).values('count'))
    ).filter(is_public=False, wiki_count__gte=6).count()

    writer.writerow({
        'public_projects_wikis': public_wiki_count,
        'private_projects_wikis': private_wiki_count,
        'public_projects_wikis_1': public_wiki_count_1, 
        'private_projects_wikis_1': private_wiki_count_1,
        'public_projects_wikis_2_5': public_wiki_count_2_5,
        'private_projects_wikis_2_5': private_wiki_count_2_5,
        'public_projects_wikis_6_plus': public_wiki_count_6_plus,
        'private_projects_wikis_6_plus': private_wiki_count_6_plus
    })

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())