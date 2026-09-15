from django.core.management.base import BaseCommand
from workers.models import Country, Language


class Command(BaseCommand):
    help = 'Add all 54 African countries'

    def handle(self, *args, **options):
        countries = [
            ('DZ', 'Algeria', 'DZD', ['Arabic', 'French', 'Berber']),
            ('AO', 'Angola', 'AOA', ['Portuguese']),
            ('BJ', 'Benin', 'XOF', ['French', 'Fon', 'Yoruba']),
            ('BW', 'Botswana', 'BWP', ['English', 'Setswana']),
            ('BF', 'Burkina Faso', 'XOF', ['French', 'Mooré']),
            ('BI', 'Burundi', 'BIF', ['Kirundi', 'French', 'English']),
            ('CV', 'Cape Verde', 'CVE', ['Portuguese', 'Creole']),
            ('CM', 'Cameroon', 'XAF', ['French', 'English']),
            ('CF', 'Central African Republic', 'XAF', ['French', 'Sango']),
            ('TD', 'Chad', 'XAF', ['French', 'Arabic']),
            ('KM', 'Comoros', 'KMF', ['Comorian', 'Arabic', 'French']),
            ('CG', 'Congo', 'XAF', ['French', 'Lingala']),
            ('CD', 'Democratic Republic of the Congo', 'CDF', ['French', 'Lingala', 'Swahili']),
            ('CI', 'Ivory Coast', 'XOF', ['French']),
            ('DJ', 'Djibouti', 'DJF', ['French', 'Arabic', 'Somali']),
            ('EG', 'Egypt', 'EGP', ['Arabic', 'English']),
            ('GQ', 'Equatorial Guinea', 'XAF', ['Spanish', 'French', 'Portuguese']),
            ('ER', 'Eritrea', 'ERN', ['Tigrinya', 'Arabic', 'English']),
            ('SZ', 'Eswatini', 'SZL', ['English', 'SiSwati']),
            ('ET', 'Ethiopia', 'ETB', ['Amharic', 'Oromo', 'Tigrinya']),
            ('GA', 'Gabon', 'XAF', ['French']),
            ('GM', 'Gambia', 'GMD', ['English', 'Mandinka', 'Wolof']),
            ('GH', 'Ghana', 'GHS', ['English', 'Twi', 'Ewe']),
            ('GN', 'Guinea', 'GNF', ['French', 'Fula', 'Susu']),
            ('GW', 'Guinea-Bissau', 'GWP', ['Portuguese', 'Creole']),
            ('KE', 'Kenya', 'KES', ['English', 'Swahili']),
            ('LS', 'Lesotho', 'LSL', ['English', 'Sesotho']),
            ('LR', 'Liberia', 'LRD', ['English']),
            ('LY', 'Libya', 'LYD', ['Arabic']),
            ('MG', 'Madagascar', 'MGA', ['Malagasy', 'French']),
            ('MW', 'Malawi', 'MWK', ['English', 'Chichewa']),
            ('ML', 'Mali', 'XOF', ['French', 'Bambara']),
            ('MR', 'Mauritania', 'MRU', ['Arabic', 'French']),
            ('MU', 'Mauritius', 'MUR', ['English', 'French', 'Creole']),
            ('MA', 'Morocco', 'MAD', ['Arabic', 'French', 'Berber']),
            ('MZ', 'Mozambique', 'MZN', ['Portuguese']),
            ('NA', 'Namibia', 'NAD', ['English']),
            ('NE', 'Niger', 'XOF', ['French', 'Hausa']),
            ('NG', 'Nigeria', 'NGN', ['English', 'Hausa', 'Yoruba', 'Igbo']),
            ('RW', 'Rwanda', 'RWF', ['Kinyarwanda', 'English', 'French']),
            ('ST', 'São Tomé and Príncipe', 'STN', ['Portuguese']),
            ('SN', 'Senegal', 'XOF', ['French', 'Wolof', 'Pulaar']),
            ('SC', 'Seychelles', 'SCR', ['English', 'French', 'Creole']),
            ('SL', 'Sierra Leone', 'SLL', ['English']),
            ('SO', 'Somalia', 'SOS', ['Somali', 'Arabic']),
            ('ZA', 'South Africa', 'ZAR', ['English', 'Zulu', 'Xhosa', 'Afrikaans']),
            ('SS', 'South Sudan', 'SSP', ['English']),
            ('SD', 'Sudan', 'SDG', ['Arabic', 'English']),
            ('TZ', 'Tanzania', 'TZS', ['Swahili', 'English']),
            ('TG', 'Togo', 'XOF', ['French', 'Ewe']),
            ('TN', 'Tunisia', 'TND', ['Arabic', 'French']),
            ('UG', 'Uganda', 'UGX', ['English', 'Swahili']),
            ('ZM', 'Zambia', 'ZMW', ['English']),
            ('ZW', 'Zimbabwe', 'ZWL', ['English', 'Shona', 'Ndebele']),
        ]

        created_count = 0
        updated_count = 0

        for code, name, currency, langs in countries:
            country, created = Country.objects.update_or_create(
                code=code,
                defaults={
                    'name': name,
                    'currency': currency,
                    'mobile_money_services': [],
                    'is_active': True,
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

            # Link languages
            for lang_name in langs:
                lang, _ = Language.objects.get_or_create(
                    name=lang_name,
                    defaults={'code': lang_name[:10].lower().replace(' ', '_')}
                )
                country.languages.add(lang)

        self.stdout.write(self.style.SUCCESS(
            f'Successfully added {created_count} new countries, updated {updated_count} existing'
        ))
