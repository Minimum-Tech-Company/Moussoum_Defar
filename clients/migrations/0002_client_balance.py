# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='balance',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10),
        ),
    ]
