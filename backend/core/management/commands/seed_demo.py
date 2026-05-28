from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand

from core.models import ActivityCategory, EmissionFactor, Plant, Scope, Tenant


class Command(BaseCommand):
    help = "Seed a demo tenant, plants, and a small emission factor catalog."

    def add_arguments(self, parser):
        parser.add_argument('--tenant-slug', default='demo')
        parser.add_argument('--tenant-name', default='Demo Tenant')

    def handle(self, *args, **options):
        slug: str = options['tenant_slug']
        name: str = options['tenant_name']

        tenant, _ = Tenant.objects.get_or_create(slug=slug, defaults={'name': name})
        if tenant.name != name:
            tenant.name = name
            tenant.save(update_fields=['name'])

        plants = [
            ('1000', 'Werk 1000 (Berlin)', 'DE', 'Europe/Berlin'),
            ('2000', 'Werk 2000 (Frankfurt)', 'DE', 'Europe/Berlin'),
        ]

        for code, plant_name, country, tz in plants:
            Plant.objects.get_or_create(
                tenant=tenant,
                code=code,
                defaults={'name': plant_name, 'country': country, 'timezone': tz},
            )

        # Demo emission factors: coherent but not authoritative.
        factors = [
            # Fuel combustion (Scope 1)
            (Scope.SCOPE_1, ActivityCategory.FUEL, 'diesel', 'liter', Decimal('2.680000')),
            (Scope.SCOPE_1, ActivityCategory.FUEL, 'petrol', 'liter', Decimal('2.310000')),
            (Scope.SCOPE_1, ActivityCategory.FUEL, 'heating_oil', 'liter', Decimal('2.680000')),

            # Purchased electricity (Scope 2)
            (Scope.SCOPE_2, ActivityCategory.ELECTRICITY, 'grid_electricity', 'kWh', Decimal('0.233000')),

            # Procurement (Scope 3) — mass-based subset
            (Scope.SCOPE_3, ActivityCategory.PROCUREMENT, 'paper', 'kg', Decimal('1.200000')),
            (Scope.SCOPE_3, ActivityCategory.PROCUREMENT, 'steel', 'kg', Decimal('1.900000')),
            (Scope.SCOPE_3, ActivityCategory.PROCUREMENT, 'plastic', 'kg', Decimal('2.500000')),
            (Scope.SCOPE_3, ActivityCategory.PROCUREMENT, 'chemicals', 'kg', Decimal('3.000000')),

            # Business travel (Scope 3)
            (Scope.SCOPE_3, ActivityCategory.TRAVEL, 'flight_economy', 'km', Decimal('0.120000')),
            (Scope.SCOPE_3, ActivityCategory.TRAVEL, 'flight_premium_economy', 'km', Decimal('0.150000')),
            (Scope.SCOPE_3, ActivityCategory.TRAVEL, 'flight_business', 'km', Decimal('0.240000')),
            (Scope.SCOPE_3, ActivityCategory.TRAVEL, 'flight_first', 'km', Decimal('0.300000')),
            (Scope.SCOPE_3, ActivityCategory.TRAVEL, 'hotel', 'night', Decimal('15.000000')),
            (Scope.SCOPE_3, ActivityCategory.TRAVEL, 'taxi', 'km', Decimal('0.200000')),
            (Scope.SCOPE_3, ActivityCategory.TRAVEL, 'rail', 'km', Decimal('0.041000')),
        ]

        created = 0
        for scope, category, subcategory, unit, value in factors:
            obj, was_created = EmissionFactor.objects.get_or_create(
                tenant=None,
                scope=scope,
                category=category,
                subcategory=subcategory,
                unit=unit,
                defaults={
                    'co2e_kg_per_unit': value,
                    'region': 'GLOBAL',
                    'source': 'Demo factors (prototype)',
                    'is_active': True,
                },
            )
            if not was_created and obj.co2e_kg_per_unit != value:
                obj.co2e_kg_per_unit = value
                obj.save(update_fields=['co2e_kg_per_unit'])
            created += int(was_created)

        self.stdout.write(self.style.SUCCESS(f"Seeded tenant '{tenant.slug}', plants, and {created} emission factors."))
