import factory

from django.conf import settings

from geotrek.core.factories import PathFactory, StakeFactory, TopologyFactory
from geotrek.common.factories import OrganismFactory
from geotrek.infrastructure.factories import InfrastructureFactory
from geotrek.signage.factories import SignageFactory
from . import models


class InterventionStatusFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.InterventionStatus

    status = factory.Sequence(lambda n: "Status %s" % n)


class InterventionDisorderFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.InterventionDisorder

    disorder = factory.Sequence(lambda n: "Disorder %s" % n)


class InterventionTypeFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.InterventionType

    type = factory.Sequence(lambda n: "Type %s" % n)


class InterventionJobFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.InterventionJob

    job = factory.Sequence(lambda n: "Job %s" % n)
    cost = 500.0


class ManDayFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.ManDay

    nb_days = 1
    job = factory.SubFactory(InterventionJobFactory)


class InterventionFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Intervention

    name = factory.Sequence(lambda n: "Intervention %s" % n)
    status = factory.SubFactory(InterventionStatusFactory)
    stake = factory.SubFactory(StakeFactory)
    type = factory.SubFactory(InterventionTypeFactory)
    if not settings.TREKKING_TOPOLOGY_ENABLED:
        topology = factory.SubFactory(TopologyFactory)

    @factory.post_generation
    def create_intervention(obj, create, extracted, **kwargs):
        if obj.pk:
            obj.disorders.add(InterventionDisorderFactory.create())
            ManDayFactory.create(intervention=obj)


class InfrastructureInterventionFactory(InterventionFactory):
    @factory.post_generation
    def create_infrastructure_intervention(obj, create, extracted, **kwargs):
        infra = InfrastructureFactory.create()
        obj.set_topology(infra)
        if create:
            obj.save()


class InfrastructurePointInterventionFactory(InterventionFactory):
    @factory.post_generation
    def create_infrastructure_point_intervention(obj, create, extracted, **kwargs):
        if settings.TREKKING_TOPOLOGY_ENABLED:
            infra = InfrastructureFactory.create(path=PathFactory.create(), path__start=0.5, path__end=0.5)
        else:
            infra = InfrastructureFactory.create(geom='SRID=2154;POINT (700040 6600040)')
        obj.set_topology(infra)
        if create:
            obj.save()


class SignageInterventionFactory(InterventionFactory):
    @factory.post_generation
    def create_signage_intervention(obj, create, extracted, **kwargs):
        infra = SignageFactory.create()
        obj.set_topology(infra)
        if create:
            obj.save()


class ContractorFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Contractor

    contractor = factory.Sequence(lambda n: "Contractor %s" % n)


class ProjectTypeFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.ProjectType

    type = factory.Sequence(lambda n: "Type %s" % n)


class ProjectDomainFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.ProjectDomain

    domain = factory.Sequence(lambda n: "Domain %s" % n)


class ProjectFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Project

    name = factory.Sequence(lambda n: "Project %s" % n)
    begin_year = 2010

    @factory.post_generation
    def create_project(obj, create, extracted, **kwargs):
        if create:
            obj.contractors.add(ContractorFactory.create())
            FundingFactory.create(project=obj, amount=1000)


class FundingFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Funding

    project = factory.SubFactory(ProjectFactory)
    organism = factory.SubFactory(OrganismFactory)
