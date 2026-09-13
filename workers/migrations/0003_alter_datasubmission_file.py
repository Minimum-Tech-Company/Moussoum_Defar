# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workers', '0002_annotationtask_annotationresult_notification_payment_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datasubmission',
            name='file',
            field=models.FileField(blank=True, null=True, upload_to='submissions/%Y/%m/%d/'),
        ),
    ]
