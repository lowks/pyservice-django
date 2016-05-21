from django.db import models
from django.db.models import AutoField, PositiveIntegerField, IntegerField, PositiveSmallIntegerField, CharField, \
    TextField, DateField, DateTimeField, TimeField, DecimalField, BooleanField, EmailField
from django.db.models.fields.related import ForeignKey
from django.forms import FileField, ImageField



class ConfigField(object):
    def __init__(self, field, destiny, label, show, description=''):
        self.field = field
        self.destiny = destiny
        self.label = label
        self.show = show
        self.validators = []
        self.options = []
        self.description = description
        self.config()

    def config(self):

        self.name = self.field.__name__
        self.maxLength = self.field.max_length or 0,
        self.editable = self.field.editable,

        # Type of field
        if isinstance(self.field, (AutoField, PositiveIntegerField, IntegerField, PositiveSmallIntegerField)):
            self.type = 'integer'
        elif isinstance(self.field, CharField):
            self.type = 'string'
        elif isinstance(self.field, TextField):
            self.type = 'text'
        elif isinstance(self.field, DateField):
            self.type = 'date'
        elif isinstance(self.field, DateTimeField):
            self.type = 'datetime'
        elif isinstance(self.field, TimeField):
            self.type = 'time'
        elif isinstance(self.field, DecimalField):
            self.type = 'double'
        elif isinstance(self.field, BooleanField):
            self.type = 'boolean'
        elif isinstance(self.field, EmailField):
            self.type = 'email'
        elif isinstance(self.field, FileField):
            self.type = 'file'
        elif isinstance(self.field, ImageField):
            self.type = 'image'
        elif isinstance(self.field, ForeignKey):
            self.type = 'fk'

        if self.field.choices:
            self.type = 'combobox'
            for op in self.field.choices:
                self.options.append({'caption': op[1],
                                     'value': op[0]})
                if len(op[1]) > self.field.max_length:
                    self.maxLength = len(op[1])

        if self.field.null == False:
            validation = {
                'type': 'notnull',
                'message': 'Esse campo nao pode fica vazio'  # f.error_messages['null']
            }
            self.validators.append(validation)

        for v in self.field.validators:
            validation = None
            if v.code == 'min_length':
                validation = {
                    'type': 'min_length',
                    'value': v.limit_value,
                    'message': 'Digite no minimo {0} caracteres'.format(v.limit_value)
                }


            elif v.code == 'max_length':
                validation = {
                    'type': 'max_length',
                    'value': v.limit_value,
                    'message': 'Digite no maximo {0} caracteres'.format(v.limit_value)
                }


            elif v.code == 'max_value':
                validation = {
                    'type': 'max_value',
                    'value': v.limit_value,
                    'message': str(v.message)
                }

            elif v.code == 'min_value':
                validation = {
                    'type': 'min_value',
                    'value': v.limit_value,
                    'message': str(v.message)
                }

            if validation:
                self.validators.append(validation)

class ClassA(models.Model):
    name = models.CharField(max_length=10)
    description = models.CharField(max_length=40, null=False, blank=False)


def test_config():
    fields = [ConfigField(field=ClassA.name, destiny='cadastro', label='Name', show=True),
              ConfigField(field=ClassA.description, destiny='cadastro', label='Description', show=True)]

    assert fields[0].type == 'string'
